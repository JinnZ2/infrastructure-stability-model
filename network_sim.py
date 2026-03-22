"""
Infrastructure Stability Model — Agent-Based Network Simulation

Models what the mean-field ODE cannot: heterogeneous node quality and network
topology effects on activation cascades and re-suppression damage.

Key insight this captures:
  High-R_i nodes are trust network hubs. They activate first (most networked,
  most visible to peer referral) but also suppress first under wrong-order
  activation (strongest pattern recognition for institutional theater).
  Burning hub nodes doesn't just lower average p_engage — it fragments the
  propagation network and removes the highest-value cascade seeds.

Usage:
  python3 network_sim.py              # run and save plots
  python3 network_sim.py --show       # also display interactive

Authors: Kavik, Claude (Anthropic)
License: CC0 1.0 Universal
"""

import sys
from dataclasses import dataclass, field
from typing import List

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


# ---------------------------------------------------------------------------
# Network construction
# ---------------------------------------------------------------------------

def build_trust_network(n_nodes, k_neighbors=6, rewire_prob=0.15, rng=None):
    """
    Watts-Strogatz small-world graph.

    Returns adjacency list. Captures the real structure of trade trust networks:
    high local clustering (tight-knit crews) with occasional long-range shortcuts
    (cross-site, cross-domain connections).
    """
    if rng is None:
        rng = np.random.default_rng()

    # Start with ring lattice
    adj = [set() for _ in range(n_nodes)]
    for i in range(n_nodes):
        for j in range(1, k_neighbors // 2 + 1):
            neighbor = (i + j) % n_nodes
            adj[i].add(neighbor)
            adj[neighbor].add(i)

    # Rewire with probability
    for i in range(n_nodes):
        neighbors = list(adj[i])
        for j in neighbors:
            if rng.random() < rewire_prob:
                # Remove edge i-j, add edge i-k (random)
                candidates = [x for x in range(n_nodes)
                              if x != i and x not in adj[i]]
                if candidates:
                    k = rng.choice(candidates)
                    adj[i].discard(j)
                    adj[j].discard(i)
                    adj[i].add(k)
                    adj[k].add(i)

    return adj


# ---------------------------------------------------------------------------
# Node model
# ---------------------------------------------------------------------------

@dataclass
class Node:
    """Individual agent in the trust network."""
    id: int
    R_i: float              # hazard recognition capacity [0, 1]
    A_i: float              # adaptive learning rate [0, 1]
    L_f_i: float            # labor bandwidth [0, 1]
    p_engage: float         # engagement probability [0, 1]
    B_i: float              # local obstruction factor [0, 1]
    prior_dismissal: float  # accumulated resistance to activation

    active: bool = False    # whether node is currently contributing
    suppressed: bool = False  # permanently burned by wrong-order activation
    months_active: int = 0

    # Cohort
    cohort: str = "mid"     # "older_high_R", "younger_high_A", "mid"

    def degree(self, adj):
        return len(adj[self.id])


def generate_population(n_nodes, adj, rng):
    """
    Generate heterogeneous node population.

    Key structural choice: R_i correlates with network degree.
    High-R_i nodes are consulted more → more edges → hubs.
    This is emergent in real networks but we encode it directly.
    """
    nodes = []
    degrees = np.array([len(adj[i]) for i in range(n_nodes)])
    degree_rank = np.argsort(np.argsort(degrees))  # 0=lowest degree, n-1=highest
    degree_percentile = degree_rank / (n_nodes - 1)

    for i in range(n_nodes):
        dp = degree_percentile[i]

        # R_i correlated with degree (hub nodes have high R_i)
        R_i = np.clip(0.3 * rng.beta(2, 2) + 0.7 * dp, 0.05, 0.98)

        # A_i inversely correlated with age/R_i (younger nodes learn faster)
        A_i = np.clip(rng.beta(2, 2) * (1.2 - 0.5 * R_i), 0.05, 0.98)

        # Cohort assignment
        if R_i > 0.7:
            cohort = "older_high_R"
            L_f_i = np.clip(0.6 + 0.3 * rng.random(), 0.3, 0.95)
        elif A_i > 0.6:
            cohort = "younger_high_A"
            L_f_i = np.clip(0.2 + 0.3 * rng.random(), 0.1, 0.60)
        else:
            cohort = "mid"
            L_f_i = np.clip(0.3 + 0.3 * rng.random(), 0.2, 0.70)

        # Initial p_engage: low for everyone (latent pool)
        p_engage = np.clip(0.05 + 0.1 * rng.random(), 0.01, 0.20)

        # B_i: moderate baseline obstruction
        B_i = np.clip(0.4 + 0.3 * rng.random(), 0.2, 0.80)

        nodes.append(Node(
            id=i, R_i=R_i, A_i=A_i, L_f_i=L_f_i,
            p_engage=p_engage, B_i=B_i,
            prior_dismissal=1.2, cohort=cohort,
        ))

    return nodes


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

@dataclass
class SimConfig:
    """Simulation configuration."""
    n_nodes: int = 200
    k_neighbors: int = 6
    rewire_prob: float = 0.15
    t_months: int = 120
    seed: int = 42

    # Activation parameters
    signal_fidelity: float = 0.20    # baseline (low)
    outreach_mode: float = 0.20      # baseline (broadcast)

    # Intervention schedule (list of (month, param, value) tuples)
    interventions: list = field(default_factory=list)

    # Physics
    activation_threshold: float = 0.5     # p_engage above this → node activates
    resuppression_rate: float = 3.5        # how fast high-R_i nodes detect theater
    ri_transfer_rate: float = 0.02        # R_i propagation per month per edge
    ri_transfer_floor: float = 0.1        # minimum R_i difference for transfer
    referral_prob_per_edge: float = 0.08  # monthly prob an active node refers a neighbor
    B_i_reduction_rate: float = 0.04      # monthly B_i decay under intervention

    # Engagement update
    engage_update_rate: float = 0.05  # base monthly p_engage update
    engage_decay_rate: float = 0.01   # monthly erosion from inequality


def get_param_at_time(config, param_name, t_month):
    """Get effective parameter value after interventions."""
    val = getattr(config, param_name)
    for month, pname, pval in config.interventions:
        if pname == param_name and t_month >= month:
            val = pval
    return val


def simulate(config: SimConfig):
    """
    Run the agent-based network simulation.

    Each month:
    1. Update B_i for all nodes (if B_i reduction active)
    2. Update p_engage for all nodes (signal quality + network effects)
    3. Apply re-suppression to high-R_i nodes if activation during high B_i
    4. Activate nodes crossing threshold
    5. Propagate R_i along edges from active nodes
    6. Active nodes refer neighbors (cascade)
    7. Record system state
    """
    rng = np.random.default_rng(config.seed)
    adj = build_trust_network(config.n_nodes, config.k_neighbors,
                               config.rewire_prob, rng)
    nodes = generate_population(config.n_nodes, adj, rng)

    # --- Recording arrays ---
    T = config.t_months
    history = {
        "t": np.arange(T),
        "n_active": np.zeros(T),
        "n_suppressed": np.zeros(T),
        "mean_p_engage": np.zeros(T),
        "mean_R_i": np.zeros(T),
        "mean_R_i_active": np.zeros(T),
        "total_L_f": np.zeros(T),
        "hub_survival_rate": np.zeros(T),  # fraction of top-20% R_i nodes not suppressed
        "network_reach": np.zeros(T),      # avg reachable nodes from active set
        "activation_by_cohort": {"older_high_R": np.zeros(T),
                                 "younger_high_A": np.zeros(T),
                                 "mid": np.zeros(T)},
    }

    # Identify hub nodes (top 20% by R_i)
    sorted_by_ri = sorted(nodes, key=lambda n: n.R_i, reverse=True)
    hub_ids = {n.id for n in sorted_by_ri[:config.n_nodes // 5]}

    for t in range(T):
        sig_fidelity = get_param_at_time(config, "signal_fidelity", t)
        out_mode = get_param_at_time(config, "outreach_mode", t)
        b_i_intervention_active = any(
            pname == "B_i_reduction" and t >= month
            for month, pname, _ in config.interventions
        )

        for node in nodes:
            if node.suppressed:
                continue

            # --- B_i update ---
            if b_i_intervention_active:
                node.B_i = max(0.05, node.B_i - config.B_i_reduction_rate)

            # --- p_engage update ---
            # Raw signal strength (ODE model formula)
            raw_signal = sig_fidelity * (1.0 + out_mode * 0.55 * 4.0)

            # B_i FILTERS the signal: obstruction blocks visibility.
            # High B_i means the node can't see the structural difference
            # even if the offering is genuine.
            effective_signal = raw_signal * (1.0 - node.B_i)

            # Network boost: active trusted neighbors bypass obstruction
            active_neighbor_count = sum(1 for j in adj[node.id]
                                        if nodes[j].active and not nodes[j].suppressed)
            network_boost = 0.08 * active_neighbor_count * (1.0 - 0.5 * node.B_i)

            # Base engagement update
            dp = (config.engage_update_rate * effective_signal * (1.0 - node.p_engage)
                  / node.prior_dismissal
                  + network_boost * (1.0 - node.p_engage)
                  - config.engage_decay_rate * node.p_engage)

            # --- RE-SUPPRESSION: the core mechanism ---
            # When outreach is active AND this node's B_i is still high:
            # The outreach pattern-matches to prior institutional dismissal.
            # High-R_i nodes detect the mismatch FASTER (stronger pattern
            # recognition) and suppress HARDER (more data confirming prior).
            activation_attempt = sig_fidelity > 0.3 or out_mode > 0.3
            if activation_attempt and node.B_i > 0.30:
                # Suppression is proportional to:
                # - R_i: pattern recognition for theater
                # - B_i: obstruction confirming dismissal experience
                # - outreach intensity: louder outreach = stronger mismatch signal
                outreach_intensity = sig_fidelity * out_mode
                suppress_strength = (config.resuppression_rate
                                     * node.R_i * node.B_i * outreach_intensity)

                # Actively push p_engage DOWN
                dp -= suppress_strength * node.p_engage

                # Permanent prior_dismissal increase (scar tissue)
                node.prior_dismissal += 0.25 * node.R_i * node.B_i * outreach_intensity

            # Apply update
            new_p = np.clip(node.p_engage + dp, 0.0, 1.0)

            # Permanent suppression check: if p_engage is being driven down
            # and prior_dismissal has accumulated past a threshold, node is burned.
            # Lower thresholds for high-R_i nodes (they commit to dismissal faster).
            suppress_threshold = 0.06 - 0.03 * node.R_i  # high R_i → lower threshold
            dismiss_threshold = 1.6 + 0.5 * (1.0 - node.R_i)  # high R_i → lower bar
            if (new_p < suppress_threshold and node.prior_dismissal > dismiss_threshold
                    and activation_attempt):
                node.suppressed = True
                node.active = False
                node.p_engage = 0.0
                continue

            node.p_engage = new_p

            # --- Activation check ---
            if not node.active and node.p_engage > config.activation_threshold:
                # Stochastic activation
                if rng.random() < node.p_engage:
                    node.active = True
                    node.months_active = 0

            # --- R_i propagation from active nodes ---
            if node.active:
                node.months_active += 1
                for j in adj[node.id]:
                    neighbor = nodes[j]
                    if not neighbor.suppressed:
                        ri_gap = node.R_i - neighbor.R_i
                        if ri_gap > config.ri_transfer_floor:
                            # Sigmoid-like transfer: faster at mid-gap
                            transfer = (config.ri_transfer_rate * ri_gap
                                        * neighbor.A_i)  # A_i modulates learning speed
                            neighbor.R_i = min(0.98, neighbor.R_i + transfer)

                # --- Referral cascade ---
                for j in adj[node.id]:
                    neighbor = nodes[j]
                    if (not neighbor.active and not neighbor.suppressed
                            and rng.random() < config.referral_prob_per_edge):
                        # Peer referral boost to p_engage
                        referral_boost = 0.15 * (1.0 - neighbor.B_i)
                        neighbor.p_engage = min(1.0, neighbor.p_engage + referral_boost)

        # --- Record state ---
        active_nodes = [n for n in nodes if n.active]
        suppressed_nodes = [n for n in nodes if n.suppressed]

        history["n_active"][t] = len(active_nodes)
        history["n_suppressed"][t] = len(suppressed_nodes)
        history["mean_p_engage"][t] = np.mean([n.p_engage for n in nodes])
        history["mean_R_i"][t] = np.mean([n.R_i for n in nodes])

        if active_nodes:
            history["mean_R_i_active"][t] = np.mean([n.R_i for n in active_nodes])
            history["total_L_f"][t] = sum(n.L_f_i for n in active_nodes)
        else:
            history["mean_R_i_active"][t] = 0.0
            history["total_L_f"][t] = 0.0

        # Hub survival
        hubs_alive = sum(1 for hid in hub_ids if not nodes[hid].suppressed)
        history["hub_survival_rate"][t] = hubs_alive / len(hub_ids)

        # Network reach from active set (BFS depth 3)
        reachable = set()
        for n in active_nodes:
            frontier = {n.id}
            for _ in range(3):
                next_frontier = set()
                for fid in frontier:
                    next_frontier.update(adj[fid])
                frontier = next_frontier - reachable
                reachable.update(frontier)
        history["network_reach"][t] = len(reachable)

        # By cohort
        for cohort in ("older_high_R", "younger_high_A", "mid"):
            history["activation_by_cohort"][cohort][t] = sum(
                1 for n in active_nodes if n.cohort == cohort
            )

    history["nodes"] = nodes
    history["adj"] = adj
    history["hub_ids"] = hub_ids
    return history


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

def make_network_scenarios():
    """Three scenarios showing the network-level re-suppression asymmetry."""

    # Scenario 1: Correct order — B_i reduction first, then activation
    correct = SimConfig(
        interventions=[
            (0, "B_i_reduction", True),        # Start reducing B_i immediately
            (6, "signal_fidelity", 0.70),       # High-fidelity outreach at month 6
            (6, "outreach_mode", 0.80),          # Lateral network traversal
        ],
    )

    # Scenario 2: Wrong order — activation first, B_i reduction later
    wrong = SimConfig(
        interventions=[
            (3, "signal_fidelity", 0.70),       # Outreach at month 3 (B_i still high)
            (3, "outreach_mode", 0.80),
            (12, "B_i_reduction", True),         # B_i reduction at month 12 (too late)
        ],
    )

    # Scenario 3: Baseline — low-effort broadcast, no B_i reduction
    baseline = SimConfig(
        interventions=[],  # no changes — low fidelity, broadcast mode, high B_i
    )

    return {
        "correct": ("Correct: B_i first, then activate", correct, "#2ca02c"),
        "wrong": ("Wrong: activate before B_i reduction", wrong, "#d62728"),
        "baseline": ("Baseline: no intervention", baseline, "#555555"),
    }


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_network_results(all_results, save_path="network_activation.png"):
    """6-panel comparison of network simulation outcomes."""
    fig = plt.figure(figsize=(16, 11))
    gs = gridspec.GridSpec(3, 2, hspace=0.38, wspace=0.28)

    panels = [
        (gs[0, 0], "n_active", "Active nodes", None),
        (gs[0, 1], "n_suppressed", "Permanently suppressed nodes", None),
        (gs[1, 0], "hub_survival_rate", "Hub node survival (top 20% R_i)", [0, 1.05]),
        (gs[1, 1], "mean_R_i", "Mean R_i (population-wide)", None),
        (gs[2, 0], "total_L_f", "Total effective labor (active nodes)", None),
        (gs[2, 1], "network_reach", "Network reach from active set (3-hop)", None),
    ]

    for gs_pos, key, title, ylim in panels:
        ax = fig.add_subplot(gs_pos)
        for label, (name, _, color) in all_results.items():
            hist = all_results[label][1]
            ax.plot(hist["t"], hist[key], color=color, linewidth=2, label=name)
        ax.set_xlabel("Months", fontsize=9)
        ax.set_title(title, fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        if ylim:
            ax.set_ylim(ylim)

    fig.suptitle("Network-Level Activation and Re-suppression Dynamics",
                 fontsize=14, y=1.01)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


def plot_cohort_activation(all_results, save_path="network_cohorts.png"):
    """Show which cohorts activate and when under each scenario."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    cohort_colors = {
        "older_high_R": "#d62728",
        "younger_high_A": "#1f77b4",
        "mid": "#aaaaaa",
    }
    cohort_labels = {
        "older_high_R": "Older high-R_i",
        "younger_high_A": "Younger high-A_i",
        "mid": "Mid-career",
    }

    for ax, (label, (name, hist, _)) in zip(axes, all_results.items()):
        for cohort, color in cohort_colors.items():
            ax.plot(hist["t"], hist["activation_by_cohort"][cohort],
                    color=color, linewidth=2, label=cohort_labels[cohort])

        ax.set_xlabel("Months", fontsize=10)
        ax.set_ylabel("Active nodes", fontsize=10)
        ax.set_title(name, fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Cohort Activation Timing by Scenario", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


def plot_resuppression_anatomy(all_results, save_path="network_resuppression.png"):
    """
    Show the anatomy of re-suppression: which nodes get burned and why.
    Compares the R_i distribution of suppressed vs surviving nodes.
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    for ax, (label, (name, hist, color)) in zip(axes, all_results.items()):
        nodes = hist["nodes"]
        suppressed = [n for n in nodes if n.suppressed]
        surviving = [n for n in nodes if not n.suppressed]
        active = [n for n in nodes if n.active]

        bins = np.linspace(0, 1, 25)

        if surviving:
            ax.hist([n.R_i for n in surviving], bins=bins, alpha=0.5,
                    color="#2ca02c", label=f"Surviving ({len(surviving)})", density=True)
        if suppressed:
            ax.hist([n.R_i for n in suppressed], bins=bins, alpha=0.7,
                    color="#d62728", label=f"Suppressed ({len(suppressed)})", density=True)

        ax.set_xlabel("R_i (hazard recognition)", fontsize=10)
        ax.set_ylabel("Density", fontsize=10)
        ax.set_title(name, fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        # Annotate
        if suppressed:
            mean_suppressed_ri = np.mean([n.R_i for n in suppressed])
            mean_surviving_ri = np.mean([n.R_i for n in surviving]) if surviving else 0
            ax.text(0.97, 0.85,
                    f"Suppressed mean R_i: {mean_suppressed_ri:.2f}\n"
                    f"Surviving mean R_i: {mean_surviving_ri:.2f}",
                    transform=ax.transAxes, ha="right", va="top", fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    fig.suptitle("Re-suppression Anatomy: Who Gets Burned?", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    show = "--show" in sys.argv
    print("=== Agent-Based Network Simulation ===\n")

    scenarios = make_network_scenarios()
    all_results = {}

    for label, (name, config, color) in scenarios.items():
        print(f"Running: {name} ({config.n_nodes} nodes)...")
        hist = simulate(config)
        all_results[label] = (name, hist, color)

        # Summary stats
        final = config.t_months - 1
        n_active = int(hist["n_active"][final])
        n_suppressed = int(hist["n_suppressed"][final])
        hub_surv = hist["hub_survival_rate"][final]
        total_lf = hist["total_L_f"][final]
        print(f"  Active: {n_active}, Suppressed: {n_suppressed}, "
              f"Hub survival: {hub_surv:.0%}, L_f: {total_lf:.1f}")

    print()
    plot_network_results(all_results)
    plot_cohort_activation(all_results)
    plot_resuppression_anatomy(all_results)

    if show:
        plt.show()


if __name__ == "__main__":
    main()

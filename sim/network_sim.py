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
  python3 sim/network_sim.py              # original 3-scenario comparison
  python3 sim/network_sim.py community    # community structure + bridge node fragmentation
  python3 sim/network_sim.py partial      # partial-order regional phasing analysis
  python3 sim/network_sim.py all          # everything
  python3 sim/network_sim.py --show       # also display interactive

Plots are written to figures/ at the repository root.

Authors: Kavik, Claude (Anthropic)
License: CC0 1.0 Universal
"""

import os
import sys
from dataclasses import dataclass, field
from typing import List

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


# ---------------------------------------------------------------------------
# Figure output — resolved against the repo root, not the current directory
# ---------------------------------------------------------------------------

FIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures"
)


def _fig(name):
    """Absolute path for a figure output. Independent of working directory."""
    os.makedirs(FIG_DIR, exist_ok=True)
    return os.path.join(FIG_DIR, name)


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
    community: int = -1     # community/region assignment

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

    # Cross-community signal leakage (partial-order analysis only).
    # Intensity of an activation signal that reaches a node through a bridge
    # edge from a community that has already started activation, relative to
    # a locally addressed one. UNMEASURED — chosen, not calibrated. The
    # partial-order safety result is conditional on this value; see
    # legacy/ledger.json entry F-004.
    leak_intensity: float = 0.3

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

def plot_network_results(all_results, save_path=None):
    """6-panel comparison of network simulation outcomes."""
    save_path = save_path or _fig("network_activation.png")
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


def plot_cohort_activation(all_results, save_path=None):
    """Show which cohorts activate and when under each scenario."""
    save_path = save_path or _fig("network_cohorts.png")
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


def plot_resuppression_anatomy(all_results, save_path=None):
    """
    Show the anatomy of re-suppression: which nodes get burned and why.
    Compares the R_i distribution of suppressed vs surviving nodes.
    """
    save_path = save_path or _fig("network_resuppression.png")
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


# ===========================================================================
# EXTENSION: Community-Structured Network
# ===========================================================================

def build_community_network(n_nodes, n_communities=5, k_intra=6, p_inter=0.02,
                            n_bridges_per_pair=1, rng=None):
    """
    Stochastic block model with explicit bridge nodes.

    Each community is a dense cluster (worksite/region). Inter-community
    edges are sparse and pass through bridge nodes — high-R_i individuals
    who span organizational boundaries.

    Returns (adj, community_assignments, bridge_node_ids).
    """
    if rng is None:
        rng = np.random.default_rng()

    adj = [set() for _ in range(n_nodes)]
    community_size = n_nodes // n_communities
    communities = []

    # Assign nodes to communities
    assignments = np.zeros(n_nodes, dtype=int)
    for c in range(n_communities):
        start = c * community_size
        end = start + community_size if c < n_communities - 1 else n_nodes
        members = list(range(start, end))
        communities.append(members)
        for m in members:
            assignments[m] = c

    # Dense intra-community edges (ring lattice + rewire within community)
    for c, members in enumerate(communities):
        nc = len(members)
        for idx, i in enumerate(members):
            for offset in range(1, k_intra // 2 + 1):
                j = members[(idx + offset) % nc]
                adj[i].add(j)
                adj[j].add(i)

    # Bridge nodes: for each pair of communities, designate bridge nodes
    bridge_ids = set()
    for c1 in range(n_communities):
        for c2 in range(c1 + 1, n_communities):
            for _ in range(n_bridges_per_pair):
                # Pick highest-degree node from each community as bridge
                b1 = rng.choice(communities[c1])
                b2 = rng.choice(communities[c2])
                adj[b1].add(b2)
                adj[b2].add(b1)
                bridge_ids.add(b1)
                bridge_ids.add(b2)

    # Sparse random inter-community edges
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if assignments[i] != assignments[j]:
                if rng.random() < p_inter:
                    adj[i].add(j)
                    adj[j].add(i)

    return adj, assignments, bridge_ids


def generate_community_population(n_nodes, adj, assignments, bridge_ids, rng):
    """Generate population with community-aware attributes."""
    nodes = []
    degrees = np.array([len(adj[i]) for i in range(n_nodes)])
    degree_rank = np.argsort(np.argsort(degrees))
    degree_percentile = degree_rank / max(1, n_nodes - 1)

    for i in range(n_nodes):
        dp = degree_percentile[i]
        is_bridge = i in bridge_ids

        # Bridge nodes get elevated R_i — they span boundaries
        if is_bridge:
            R_i = np.clip(0.75 + 0.2 * rng.random(), 0.70, 0.98)
        else:
            R_i = np.clip(0.3 * rng.beta(2, 2) + 0.7 * dp, 0.05, 0.98)

        A_i = np.clip(rng.beta(2, 2) * (1.2 - 0.5 * R_i), 0.05, 0.98)

        if R_i > 0.7:
            cohort = "older_high_R"
            L_f_i = np.clip(0.6 + 0.3 * rng.random(), 0.3, 0.95)
        elif A_i > 0.6:
            cohort = "younger_high_A"
            L_f_i = np.clip(0.2 + 0.3 * rng.random(), 0.1, 0.60)
        else:
            cohort = "mid"
            L_f_i = np.clip(0.3 + 0.3 * rng.random(), 0.2, 0.70)

        p_engage = np.clip(0.05 + 0.1 * rng.random(), 0.01, 0.20)
        B_i = np.clip(0.4 + 0.3 * rng.random(), 0.2, 0.80)

        nodes.append(Node(
            id=i, R_i=R_i, A_i=A_i, L_f_i=L_f_i,
            p_engage=p_engage, B_i=B_i,
            prior_dismissal=1.2, cohort=cohort,
            community=int(assignments[i]),
        ))

    return nodes


def simulate_community(config, n_communities=5, k_intra=6, p_inter=0.02,
                        n_bridges=1):
    """
    Run simulation on community-structured network.

    Same dynamics as simulate() but uses community graph and tracks
    per-community and bridge-node metrics.
    """
    rng = np.random.default_rng(config.seed)
    adj, assignments, bridge_ids = build_community_network(
        config.n_nodes, n_communities, k_intra, p_inter, n_bridges, rng
    )
    nodes = generate_community_population(
        config.n_nodes, adj, assignments, bridge_ids, rng
    )

    T = config.t_months
    history = {
        "t": np.arange(T),
        "n_active": np.zeros(T),
        "n_suppressed": np.zeros(T),
        "total_L_f": np.zeros(T),
        "bridge_survival": np.zeros(T),
        "communities_reached": np.zeros(T),
        "per_community_active": np.zeros((n_communities, T)),
        "per_community_suppressed": np.zeros((n_communities, T)),
        "mean_R_i": np.zeros(T),
        "inter_community_edges_alive": np.zeros(T),
    }

    # Count initial inter-community edges
    total_inter_edges = 0
    for i in range(config.n_nodes):
        for j in adj[i]:
            if assignments[i] != assignments[j] and j > i:
                total_inter_edges += 1

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

            if b_i_intervention_active:
                node.B_i = max(0.05, node.B_i - config.B_i_reduction_rate)

            raw_signal = sig_fidelity * (1.0 + out_mode * 0.55 * 4.0)
            effective_signal = raw_signal * (1.0 - node.B_i)

            active_neighbor_count = sum(1 for j in adj[node.id]
                                        if nodes[j].active and not nodes[j].suppressed)
            network_boost = 0.08 * active_neighbor_count * (1.0 - 0.5 * node.B_i)

            dp = (config.engage_update_rate * effective_signal * (1.0 - node.p_engage)
                  / node.prior_dismissal
                  + network_boost * (1.0 - node.p_engage)
                  - config.engage_decay_rate * node.p_engage)

            activation_attempt = sig_fidelity > 0.3 or out_mode > 0.3
            if activation_attempt and node.B_i > 0.30:
                outreach_intensity = sig_fidelity * out_mode
                suppress_strength = (config.resuppression_rate
                                     * node.R_i * node.B_i * outreach_intensity)
                dp -= suppress_strength * node.p_engage
                node.prior_dismissal += 0.25 * node.R_i * node.B_i * outreach_intensity

            new_p = np.clip(node.p_engage + dp, 0.0, 1.0)

            suppress_threshold = 0.06 - 0.03 * node.R_i
            dismiss_threshold = 1.6 + 0.5 * (1.0 - node.R_i)
            if (new_p < suppress_threshold and node.prior_dismissal > dismiss_threshold
                    and activation_attempt):
                node.suppressed = True
                node.active = False
                node.p_engage = 0.0
                continue

            node.p_engage = new_p

            if not node.active and node.p_engage > config.activation_threshold:
                if rng.random() < node.p_engage:
                    node.active = True
                    node.months_active = 0

            if node.active:
                node.months_active += 1
                for j in adj[node.id]:
                    neighbor = nodes[j]
                    if not neighbor.suppressed:
                        ri_gap = node.R_i - neighbor.R_i
                        if ri_gap > config.ri_transfer_floor:
                            transfer = config.ri_transfer_rate * ri_gap * neighbor.A_i
                            neighbor.R_i = min(0.98, neighbor.R_i + transfer)

                for j in adj[node.id]:
                    neighbor = nodes[j]
                    if (not neighbor.active and not neighbor.suppressed
                            and rng.random() < config.referral_prob_per_edge):
                        referral_boost = 0.15 * (1.0 - neighbor.B_i)
                        neighbor.p_engage = min(1.0, neighbor.p_engage + referral_boost)

        # Record
        active_nodes = [n for n in nodes if n.active]
        history["n_active"][t] = len(active_nodes)
        history["n_suppressed"][t] = sum(1 for n in nodes if n.suppressed)
        history["total_L_f"][t] = sum(n.L_f_i for n in active_nodes)
        history["mean_R_i"][t] = np.mean([n.R_i for n in nodes])

        # Bridge survival
        bridges_alive = sum(1 for bid in bridge_ids if not nodes[bid].suppressed)
        history["bridge_survival"][t] = bridges_alive / max(1, len(bridge_ids))

        # Communities with at least one active node
        active_communities = set(n.community for n in active_nodes)
        history["communities_reached"][t] = len(active_communities)

        # Per-community
        for c in range(n_communities):
            history["per_community_active"][c, t] = sum(
                1 for n in active_nodes if n.community == c)
            history["per_community_suppressed"][c, t] = sum(
                1 for n in nodes if n.suppressed and n.community == c)

        # Inter-community edges with at least one non-suppressed endpoint
        alive_inter = 0
        for i in range(config.n_nodes):
            if nodes[i].suppressed:
                continue
            for j in adj[i]:
                if j > i and assignments[i] != assignments[j] and not nodes[j].suppressed:
                    alive_inter += 1
        history["inter_community_edges_alive"][t] = alive_inter / max(1, total_inter_edges)

    history["nodes"] = nodes
    history["adj"] = adj
    history["bridge_ids"] = bridge_ids
    history["assignments"] = assignments
    history["n_communities"] = n_communities
    return history


def run_community_analysis(save_path=None):
    """Show how community structure amplifies bridge-node fragmentation."""
    save_path = save_path or _fig("community_fragmentation.png")
    print("\n=== Community Structure Analysis ===")

    scenarios = {
        "correct": ("Correct: B_i first", SimConfig(
            n_nodes=250,
            interventions=[
                (0, "B_i_reduction", True),
                (6, "signal_fidelity", 0.70),
                (6, "outreach_mode", 0.80),
            ],
        ), "#2ca02c"),
        "wrong": ("Wrong: activate first", SimConfig(
            n_nodes=250,
            interventions=[
                (3, "signal_fidelity", 0.70),
                (3, "outreach_mode", 0.80),
                (12, "B_i_reduction", True),
            ],
        ), "#d62728"),
    }

    results = {}
    for key, (name, config, color) in scenarios.items():
        print(f"Running: {name} ({config.n_nodes} nodes, 5 communities)...")
        hist = simulate_community(config, n_communities=5, k_intra=6,
                                   p_inter=0.015, n_bridges=2)
        results[key] = (name, hist, color)

        final = config.t_months - 1
        n_active = int(hist["n_active"][final])
        n_suppressed = int(hist["n_suppressed"][final])
        bridge_surv = hist["bridge_survival"][final]
        communities = int(hist["communities_reached"][final])
        inter_edges = hist["inter_community_edges_alive"][final]
        print(f"  Active: {n_active}, Suppressed: {n_suppressed}, "
              f"Bridge survival: {bridge_surv:.0%}, "
              f"Communities reached: {communities}/5, "
              f"Inter-edges alive: {inter_edges:.0%}")

    # --- Plot ---
    fig = plt.figure(figsize=(16, 12))
    gs = gridspec.GridSpec(3, 2, hspace=0.38, wspace=0.30)

    # Panel 1: Active nodes
    ax = fig.add_subplot(gs[0, 0])
    for key, (name, hist, color) in results.items():
        ax.plot(hist["t"], hist["n_active"], color=color, linewidth=2, label=name)
    ax.set_title("Active nodes", fontsize=11)
    ax.set_xlabel("Months"); ax.set_ylabel("Count")
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    # Panel 2: Bridge node survival
    ax = fig.add_subplot(gs[0, 1])
    for key, (name, hist, color) in results.items():
        ax.plot(hist["t"], hist["bridge_survival"], color=color, linewidth=2, label=name)
    ax.set_title("Bridge node survival rate", fontsize=11)
    ax.set_xlabel("Months"); ax.set_ylabel("Fraction")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    # Panel 3: Inter-community edges alive
    ax = fig.add_subplot(gs[1, 0])
    for key, (name, hist, color) in results.items():
        ax.plot(hist["t"], hist["inter_community_edges_alive"],
                color=color, linewidth=2, label=name)
    ax.set_title("Inter-community connectivity (fraction of edges alive)", fontsize=11)
    ax.set_xlabel("Months"); ax.set_ylabel("Fraction")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    # Panel 4: Communities reached by activation cascade
    ax = fig.add_subplot(gs[1, 1])
    for key, (name, hist, color) in results.items():
        ax.plot(hist["t"], hist["communities_reached"], color=color,
                linewidth=2, label=name)
    ax.set_title("Communities reached by activation cascade", fontsize=11)
    ax.set_xlabel("Months"); ax.set_ylabel("Count (of 5)")
    ax.set_ylim(0, 5.5)
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    # Panel 5-6: Per-community activation heatmaps
    for idx, (key, (name, hist, color)) in enumerate(results.items()):
        ax = fig.add_subplot(gs[2, idx])
        n_c = hist["n_communities"]
        im = ax.imshow(hist["per_community_active"], aspect="auto",
                       cmap="YlGn", interpolation="nearest",
                       extent=[0, hist["t"][-1], n_c - 0.5, -0.5])
        ax.set_xlabel("Months"); ax.set_ylabel("Community")
        ax.set_title(f"Per-community activation: {name}", fontsize=10)
        ax.set_yticks(range(n_c))
        fig.colorbar(im, ax=ax, label="Active nodes", shrink=0.8)

    fig.suptitle("Community Structure: Bridge Node Fragmentation Under Wrong-Order Activation",
                 fontsize=13, y=1.01)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


# ===========================================================================
# EXTENSION: Partial-Order Regional Strategy
# ===========================================================================

def simulate_partial_order(config, n_communities=5, phase_schedule=None,
                            k_intra=6, p_inter=0.015, n_bridges=2):
    """
    Simulate with per-community intervention timing.

    phase_schedule: dict mapping community_id -> (b_i_start_month, activation_start_month)
    This allows B_i reduction to start in some regions while activation
    starts in others, testing whether activation signal leaks across
    community boundaries before B_i is reduced there.
    """
    rng = np.random.default_rng(config.seed)
    adj, assignments, bridge_ids = build_community_network(
        config.n_nodes, n_communities, k_intra, p_inter, n_bridges, rng
    )
    nodes = generate_community_population(
        config.n_nodes, adj, assignments, bridge_ids, rng
    )

    if phase_schedule is None:
        phase_schedule = {c: (0, 6) for c in range(n_communities)}

    T = config.t_months
    history = {
        "t": np.arange(T),
        "n_active": np.zeros(T),
        "n_suppressed": np.zeros(T),
        "total_L_f": np.zeros(T),
        "per_community_active": np.zeros((n_communities, T)),
        "per_community_suppressed": np.zeros((n_communities, T)),
        "per_community_mean_p_engage": np.zeros((n_communities, T)),
        "bridge_survival": np.zeros(T),
        "mean_R_i": np.zeros(T),
    }

    for t in range(T):
        for node in nodes:
            if node.suppressed:
                continue

            c = node.community
            b_i_start, act_start = phase_schedule.get(c, (0, 6))

            # Per-community B_i reduction
            if t >= b_i_start:
                node.B_i = max(0.05, node.B_i - config.B_i_reduction_rate)

            # Per-community activation signal
            if t >= act_start:
                sig_fidelity = 0.70
                out_mode = 0.80
            else:
                sig_fidelity = config.signal_fidelity
                out_mode = config.outreach_mode

            raw_signal = sig_fidelity * (1.0 + out_mode * 0.55 * 4.0)
            effective_signal = raw_signal * (1.0 - node.B_i)

            active_neighbor_count = sum(1 for j in adj[node.id]
                                        if nodes[j].active and not nodes[j].suppressed)
            # Cross-community referral: active neighbors in OTHER communities
            # can push engagement even if THIS community hasn't started activation.
            # This is the signal leakage mechanism.
            cross_community_active = sum(
                1 for j in adj[node.id]
                if nodes[j].active and not nodes[j].suppressed
                and nodes[j].community != c
            )
            network_boost = 0.08 * active_neighbor_count * (1.0 - 0.5 * node.B_i)

            dp = (config.engage_update_rate * effective_signal * (1.0 - node.p_engage)
                  / node.prior_dismissal
                  + network_boost * (1.0 - node.p_engage)
                  - config.engage_decay_rate * node.p_engage)

            # Re-suppression: activation attempt in this node's context
            # includes LEAKED signal from adjacent communities
            local_activation = sig_fidelity > 0.3 or out_mode > 0.3
            leaked_activation = cross_community_active > 0 and node.B_i > 0.30
            activation_attempt = local_activation or leaked_activation

            if activation_attempt and node.B_i > 0.30:
                # Leaked activation is weaker but still damaging
                if local_activation:
                    outreach_intensity = sig_fidelity * out_mode
                else:
                    outreach_intensity = (config.leak_intensity * cross_community_active
                                          / max(1, len(adj[node.id])))

                suppress_strength = (config.resuppression_rate
                                     * node.R_i * node.B_i * outreach_intensity)
                dp -= suppress_strength * node.p_engage
                node.prior_dismissal += 0.25 * node.R_i * node.B_i * outreach_intensity

            new_p = np.clip(node.p_engage + dp, 0.0, 1.0)

            suppress_threshold = 0.06 - 0.03 * node.R_i
            dismiss_threshold = 1.6 + 0.5 * (1.0 - node.R_i)
            if (new_p < suppress_threshold and node.prior_dismissal > dismiss_threshold
                    and activation_attempt):
                node.suppressed = True
                node.active = False
                node.p_engage = 0.0
                continue

            node.p_engage = new_p

            if not node.active and node.p_engage > config.activation_threshold:
                if rng.random() < node.p_engage:
                    node.active = True
                    node.months_active = 0

            if node.active:
                node.months_active += 1
                for j in adj[node.id]:
                    neighbor = nodes[j]
                    if not neighbor.suppressed:
                        ri_gap = node.R_i - neighbor.R_i
                        if ri_gap > config.ri_transfer_floor:
                            transfer = config.ri_transfer_rate * ri_gap * neighbor.A_i
                            neighbor.R_i = min(0.98, neighbor.R_i + transfer)

                for j in adj[node.id]:
                    neighbor = nodes[j]
                    if (not neighbor.active and not neighbor.suppressed
                            and rng.random() < config.referral_prob_per_edge):
                        referral_boost = 0.15 * (1.0 - neighbor.B_i)
                        neighbor.p_engage = min(1.0, neighbor.p_engage + referral_boost)

        # Record
        active_nodes = [n for n in nodes if n.active]
        history["n_active"][t] = len(active_nodes)
        history["n_suppressed"][t] = sum(1 for n in nodes if n.suppressed)
        history["total_L_f"][t] = sum(n.L_f_i for n in active_nodes)
        history["mean_R_i"][t] = np.mean([n.R_i for n in nodes])

        bridges_alive = sum(1 for bid in bridge_ids if not nodes[bid].suppressed)
        history["bridge_survival"][t] = bridges_alive / max(1, len(bridge_ids))

        for c_id in range(n_communities):
            c_nodes = [n for n in nodes if n.community == c_id]
            history["per_community_active"][c_id, t] = sum(
                1 for n in c_nodes if n.active)
            history["per_community_suppressed"][c_id, t] = sum(
                1 for n in c_nodes if n.suppressed)
            history["per_community_mean_p_engage"][c_id, t] = np.mean(
                [n.p_engage for n in c_nodes])

    history["nodes"] = nodes
    history["adj"] = adj
    history["bridge_ids"] = bridge_ids
    history["n_communities"] = n_communities
    history["phase_schedule"] = phase_schedule
    return history


def run_partial_order_analysis(save_path=None):
    """
    Test whether partial-order strategies (phased by region) are safe.

    Strategies:
    1. Uniform correct: all communities B_i first (month 0), activate (month 6)
    2. Staggered safe: B_i reduction in all communities (month 0),
       activation rolls out community by community (months 6, 9, 12, 15, 18)
    3. Parallel mixed: some communities start activation early while others
       are still reducing B_i — tests signal leakage
    4. Wrong uniform: activation everywhere at month 3, B_i at month 12
    """
    save_path = save_path or _fig("partial_order.png")
    print("\n=== Partial-Order Regional Strategy Analysis ===")

    n_communities = 5
    base_config = SimConfig(n_nodes=250, t_months=120, seed=42)

    strategies = {
        "uniform_correct": {
            "name": "All regions: B_i first, then activate",
            "schedule": {c: (0, 6) for c in range(n_communities)},
            "color": "#2ca02c",
        },
        "staggered_safe": {
            "name": "Staggered: B_i everywhere, activation rolls out",
            "schedule": {c: (0, 6 + c * 3) for c in range(n_communities)},
            "color": "#1f77b4",
        },
        "parallel_mixed": {
            "name": "Mixed: regions 0-1 activate early, 2-4 still reducing B_i",
            "schedule": {
                0: (0, 3),    # B_i and activation nearly simultaneous
                1: (0, 3),
                2: (0, 12),   # B_i early, activation late
                3: (0, 15),
                4: (0, 18),
            },
            "color": "#ff7f0e",
        },
        "wrong_uniform": {
            "name": "All regions: activate first, B_i later",
            "schedule": {c: (12, 3) for c in range(n_communities)},
            "color": "#d62728",
        },
    }

    results = {}
    for key, strat in strategies.items():
        config = SimConfig(n_nodes=250, t_months=120, seed=42)
        print(f"Running: {strat['name']}...")
        hist = simulate_partial_order(
            config, n_communities=n_communities,
            phase_schedule=strat["schedule"]
        )
        results[key] = hist

        final = config.t_months - 1
        print(f"  Active: {int(hist['n_active'][final])}, "
              f"Suppressed: {int(hist['n_suppressed'][final])}, "
              f"Bridge survival: {hist['bridge_survival'][final]:.0%}")

    # --- Plot ---
    fig = plt.figure(figsize=(16, 14))
    gs = gridspec.GridSpec(3, 2, hspace=0.38, wspace=0.30)

    # Panel 1: Total active nodes
    ax = fig.add_subplot(gs[0, 0])
    for key, strat in strategies.items():
        ax.plot(results[key]["t"], results[key]["n_active"],
                color=strat["color"], linewidth=2, label=strat["name"])
    ax.set_title("Total active nodes", fontsize=11)
    ax.set_xlabel("Months"); ax.set_ylabel("Count")
    ax.legend(fontsize=7, loc="lower right"); ax.grid(True, alpha=0.3)

    # Panel 2: Suppressed nodes
    ax = fig.add_subplot(gs[0, 1])
    for key, strat in strategies.items():
        ax.plot(results[key]["t"], results[key]["n_suppressed"],
                color=strat["color"], linewidth=2, label=strat["name"])
    ax.set_title("Permanently suppressed nodes", fontsize=11)
    ax.set_xlabel("Months"); ax.set_ylabel("Count")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    # Panel 3: Total L_f
    ax = fig.add_subplot(gs[1, 0])
    for key, strat in strategies.items():
        ax.plot(results[key]["t"], results[key]["total_L_f"],
                color=strat["color"], linewidth=2, label=strat["name"])
    ax.set_title("Total effective labor", fontsize=11)
    ax.set_xlabel("Months"); ax.set_ylabel("L_f")
    ax.legend(fontsize=7, loc="lower right"); ax.grid(True, alpha=0.3)

    # Panel 4: Bridge survival
    ax = fig.add_subplot(gs[1, 1])
    for key, strat in strategies.items():
        ax.plot(results[key]["t"], results[key]["bridge_survival"],
                color=strat["color"], linewidth=2, label=strat["name"])
    ax.set_title("Bridge node survival", fontsize=11)
    ax.set_xlabel("Months"); ax.set_ylabel("Fraction")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    # Panel 5-6: Per-community heatmaps for mixed vs uniform correct
    for idx, (key, title) in enumerate([
        ("parallel_mixed", "Mixed strategy: per-community activation"),
        ("wrong_uniform", "Wrong order: per-community suppression"),
    ]):
        ax = fig.add_subplot(gs[2, idx])
        if "suppress" in title.lower():
            data = results[key]["per_community_suppressed"]
            cmap = "Reds"
            clabel = "Suppressed"
        else:
            data = results[key]["per_community_active"]
            cmap = "YlGn"
            clabel = "Active"
        im = ax.imshow(data, aspect="auto", cmap=cmap, interpolation="nearest",
                       extent=[0, 119, n_communities - 0.5, -0.5])
        ax.set_xlabel("Months"); ax.set_ylabel("Community")
        ax.set_title(title, fontsize=10)
        ax.set_yticks(range(n_communities))

        # Annotate phase schedule
        schedule = strategies[key]["schedule"]
        for c_id, (b_start, a_start) in schedule.items():
            ax.axvline(a_start, ymin=(n_communities - c_id - 0.5) / n_communities,
                       ymax=(n_communities - c_id + 0.5) / n_communities,
                       color="white", linewidth=1.5, linestyle="--", alpha=0.8)

        fig.colorbar(im, ax=ax, label=clabel, shrink=0.8)

    fig.suptitle("Partial-Order Regional Strategies: Is Phased Activation Safe?",
                 fontsize=13, y=1.01)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_core(show=False):
    """Run the original 3-scenario comparison."""
    print("=== Agent-Based Network Simulation ===\n")
    scenarios = make_network_scenarios()
    all_results = {}

    for label, (name, config, color) in scenarios.items():
        print(f"Running: {name} ({config.n_nodes} nodes)...")
        hist = simulate(config)
        all_results[label] = (name, hist, color)

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


def main():
    args = set(sys.argv[1:])
    show = "--show" in args
    args.discard("--show")

    mode = args.pop() if args else "core"

    if mode in ("core", "all"):
        run_core(show)
    if mode in ("community", "all"):
        run_community_analysis()
    if mode in ("partial", "all"):
        run_partial_order_analysis()

    if mode not in ("core", "community", "partial", "all"):
        print(f"Unknown mode: {mode}")
        print("Usage: python3 network_sim.py [core|community|partial|all] [--show]")
        sys.exit(1)

    if show:
        plt.show()


if __name__ == "__main__":
    main()

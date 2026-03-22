"""
Infrastructure Stability Model — ODE Simulation Engine

Simulates the coupled energy-material-labor system defined in system-model.json.
Demonstrates how intervention lever sequencing determines whether Phi (maintenance
burden ratio) stabilizes or crosses the structural decay threshold.

Four scenarios:
  1. Baseline — no intervention, drift toward decay
  2. Wrong order — activation before B_i reduction (re-suppression failure)
  3. Correct sequence — B_i reduction first, then activation and epsilon reduction
  4. Emergency — all levers simultaneously after Phi crosses 1.0

Usage:
  python3 sim.py              # run all scenarios, save plots
  python3 sim.py --show       # also display interactive plots

Authors: Kavik, Claude (Anthropic)
License: CC0 1.0 Universal
"""

import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


# ---------------------------------------------------------------------------
# Parameters — values from system-model.json
# ---------------------------------------------------------------------------

PARAMS = {
    # Thermodynamic
    "alpha": 0.30,        # baseline maintenance energy coefficient
    "beta0": 1.25,        # base maintenance energy exponent
    "gamma": 0.30,        # coupling-to-beta sensitivity

    # Labor dynamics
    "b1": 0.08,           # exclusion pressure on labor bandwidth
    "b2": 0.05,           # inequality pressure on labor bandwidth
    "b3": 0.10,           # training rate input

    # Complexity dynamics
    "a1": 0.07,           # yield-bias driven complexity growth
    "a2": 0.06,           # stability-weight driven complexity reduction

    # Engagement dynamics
    "prior_dismissal": 1.2,   # resistance coefficient for p_engage update
    "gamma_t": 0.55,          # trust network clustering coefficient
    "k_avg": 4.0,             # average node degree in trust network
    "signal_fidelity": 0.20,  # 0=broadcast/PR, 1=credible demonstrated difference
    "outreach_mode": 0.20,    # 0=institutional broadcast, 1=lateral peer network
    "decay_rate": 0.05,       # ongoing erosion of engagement from inequality

    # External forcing (baseline)
    "Y_bias": 1.0,            # yield bias pressure (drives complexity growth)
    "S_weight": 0.3,          # stability weight (counteracts complexity)
    "I": 0.5,                 # inequality pressure
    "T_rate": 0.12,           # training pipeline input rate
    "E": 1.0,                 # primary energy throughput (normalized)
    "L_latent": 0.8,          # latent high-skill pool size

    # Coupling dynamics
    "c1": 1.0,                # optimization pressure scaling
    "c2": 1.0,                # decentralization policy scaling
    "optimization_pressure": 0.05,    # drives kappa upward
    "decentralization_policy": 0.01,  # counteracts kappa growth

    # Obstruction and exclusion (not ODE state — policy parameters)
    "B_i": 0.6,               # signal obstruction factor
    "epsilon": 0.35,          # labor exclusion coefficient

    # Re-suppression penalty
    "suppression_penalty_rate": 4.0,  # rate of prior_dismissal damage
    "B_i_activation_threshold": 0.3,  # B_i above this during outreach causes damage
}

# State: [C, L_training, p_engage, kappa, prior_dismissal]
INITIAL_STATE = np.array([
    1.2,    # C — system complexity
    0.80,   # L_training — training channel labor
    0.10,   # p_engage — engagement probability (low due to prior dismissal)
    0.50,   # kappa — coupling coefficient
    1.2,    # prior_dismissal — starts at typical value
])

STATE_LABELS = ["C", "L_training", "p_engage", "kappa", "prior_dismissal"]

# State variable domains (min, max) for soft clamping
STATE_DOMAINS = np.array([
    [0.1, 10.0],   # C
    [0.01, 5.0],   # L_training
    [0.0, 1.0],    # p_engage
    [0.01, 3.0],   # kappa
    [0.3, 10.0],   # prior_dismissal
])


# ---------------------------------------------------------------------------
# Intervention system
# ---------------------------------------------------------------------------

@dataclass
class Intervention:
    """A time-triggered or condition-triggered parameter change."""
    param: str                            # parameter key to modify
    target: float                         # target value
    ramp_months: float = 3.0              # linear ramp duration
    start_month: Optional[float] = None   # time trigger (months)
    trigger: Optional[Callable] = None    # condition trigger: f(t, y, derived) -> bool
    _activated_at: Optional[float] = field(default=None, repr=False, init=False)

    def get_value(self, t_months, base_value):
        """Return interpolated value at time t_months."""
        if self._activated_at is None:
            if self.start_month is not None and t_months >= self.start_month:
                self._activated_at = self.start_month
            else:
                return base_value

        elapsed = t_months - self._activated_at
        if elapsed <= 0:
            return base_value
        if elapsed >= self.ramp_months:
            return self.target
        frac = elapsed / self.ramp_months
        return base_value + frac * (self.target - base_value)


def get_effective_params(t_years, base_params, interventions):
    """Apply active interventions to get effective parameter values at time t."""
    t_months = t_years * 12.0
    params = dict(base_params)
    for iv in interventions:
        base_val = base_params[iv.param]
        params[iv.param] = iv.get_value(t_months, base_val)
    return params


# ---------------------------------------------------------------------------
# ODE system
# ---------------------------------------------------------------------------

def _soft_clamp_derivative(val, dval, lo, hi, margin=0.05):
    """Smoothly reduce derivative near domain boundaries."""
    if dval > 0 and val > hi - margin:
        scale = max(0.0, (hi - val) / margin)
        return dval * scale
    if dval < 0 and val < lo + margin:
        scale = max(0.0, (val - lo) / margin)
        return dval * scale
    return dval


def ode_system(t, y, base_params, interventions):
    """
    5-variable coupled ODE system.

    State vector y = [C, L_training, p_engage, kappa, prior_dismissal]

    Returns dy/dt.
    """
    C, L_training, p_engage, kappa, prior_dismissal_state = y

    # Clamp state to domains for computation safety
    C = np.clip(C, STATE_DOMAINS[0, 0], STATE_DOMAINS[0, 1])
    L_training = np.clip(L_training, STATE_DOMAINS[1, 0], STATE_DOMAINS[1, 1])
    p_engage = np.clip(p_engage, STATE_DOMAINS[2, 0], STATE_DOMAINS[2, 1])
    kappa = np.clip(kappa, STATE_DOMAINS[3, 0], STATE_DOMAINS[3, 1])
    prior_dismissal_state = np.clip(prior_dismissal_state, STATE_DOMAINS[4, 0], STATE_DOMAINS[4, 1])

    # Get effective parameters (with interventions applied)
    p = get_effective_params(t, base_params, interventions)

    # Derived quantities
    beta_eff = p["beta0"] + p["gamma"] * kappa
    Em = p["alpha"] * C ** beta_eff
    L_latent_recovered = p["L_latent"] * p_engage * (1.0 - p["B_i"])
    L_f_active = max(0.01, L_training * (1.0 - p["epsilon"]) + L_latent_recovered)
    Phi = Em / (p["E"] * L_f_active)

    # --- Derivatives ---

    # dC/dt: complexity dynamics
    dC = p["a1"] * p["Y_bias"] - p["a2"] * p["S_weight"]

    # dL_training/dt: training labor pipeline
    dL_training = -p["b1"] * p["epsilon"] - p["b2"] * p["I"] + p["b3"] * p["T_rate"]

    # dp_engage/dt: engagement probability (Bayesian-like update)
    signal_eff = p["signal_fidelity"] * (1.0 + p["outreach_mode"] * p["gamma_t"] * p["k_avg"])
    dp_engage = (signal_eff * (1.0 - p_engage) / prior_dismissal_state
                 - p["decay_rate"] * p_engage * p["I"])

    # dkappa/dt: coupling dynamics (ratchet character)
    dkappa = (p["c1"] * p["optimization_pressure"]
              - p["c2"] * p["decentralization_policy"])

    # Re-suppression mechanics — the core sequencing constraint.
    # When outreach is active AND B_i is still high:
    # 1. p_engage is actively pushed DOWN (confirmed dismissal)
    # 2. prior_dismissal increases permanently (resistance to future activation)
    activation_intensity = p["signal_fidelity"] * p["outreach_mode"]
    B_i_excess = max(0.0, p["B_i"] - p["B_i_activation_threshold"])
    resuppression = p["suppression_penalty_rate"] * activation_intensity * B_i_excess

    # Direct suppression of engagement during wrong-order activation
    dp_engage -= resuppression * p_engage

    # Permanent increase to prior_dismissal resistance
    d_prior_dismissal = resuppression

    # Apply soft clamping at domain boundaries
    derivs = [dC, dL_training, dp_engage, dkappa, d_prior_dismissal]
    state = [C, L_training, p_engage, kappa, prior_dismissal_state]
    for i in range(5):
        derivs[i] = _soft_clamp_derivative(
            state[i], derivs[i], STATE_DOMAINS[i, 0], STATE_DOMAINS[i, 1]
        )

    return derivs


def compute_derived(t_array, y_array, base_params, interventions):
    """Post-process ODE solution to compute Phi, Em, L_f_active, F, beta_eff."""
    n = len(t_array)
    result = {
        "Phi": np.zeros(n),
        "Em": np.zeros(n),
        "L_f_active": np.zeros(n),
        "F": np.zeros(n),
        "beta_eff": np.zeros(n),
    }

    for i in range(n):
        t = t_array[i]
        C = y_array[0, i]
        L_training = y_array[1, i]
        p_engage = y_array[2, i]
        kappa = y_array[3, i]

        p = get_effective_params(t, base_params, interventions)

        beta_eff = p["beta0"] + p["gamma"] * kappa
        Em = p["alpha"] * C ** beta_eff
        L_latent_recovered = p["L_latent"] * p_engage * (1.0 - p["B_i"])
        L_f_active = max(0.01, L_training * (1.0 - p["epsilon"]) + L_latent_recovered)
        Phi = Em / (p["E"] * L_f_active)
        F = kappa * Phi

        result["Phi"][i] = Phi
        result["Em"][i] = Em
        result["L_f_active"][i] = L_f_active
        result["F"][i] = F
        result["beta_eff"][i] = beta_eff

    return result


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------

def run_scenario(name, interventions, t_months=120, params=None, y0=None):
    """Run a single scenario and return results dict."""
    if params is None:
        params = dict(PARAMS)
    if y0 is None:
        y0 = INITIAL_STATE.copy()

    # Reset intervention activation state
    for iv in interventions:
        iv._activated_at = None

    t_span = (0.0, t_months / 12.0)
    t_eval = np.linspace(t_span[0], t_span[1], 500)

    sol = solve_ivp(
        ode_system,
        t_span,
        y0,
        method="Radau",
        t_eval=t_eval,
        args=(params, interventions),
        rtol=1e-6,
        atol=1e-8,
        max_step=0.05,
    )

    if not sol.success:
        print(f"Warning: solver failed for scenario '{name}': {sol.message}")

    derived = compute_derived(sol.t, sol.y, params, interventions)

    return {
        "name": name,
        "t_months": sol.t * 12.0,
        "t_years": sol.t,
        "state": {label: sol.y[i] for i, label in enumerate(STATE_LABELS)},
        "derived": derived,
    }


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

def make_scenarios():
    """Define the four demonstration scenarios."""

    # Scenario 1: Baseline — no intervention
    baseline = []

    # Scenario 2: Wrong order — activation before B_i reduction
    wrong_order = [
        # Month 3: activate outreach (L1) while B_i is still high
        Intervention("signal_fidelity", target=0.70, ramp_months=2, start_month=3),
        Intervention("outreach_mode", target=0.80, ramp_months=2, start_month=3),
        # Month 12: reduce B_i (L4) — too late, damage done
        Intervention("B_i", target=0.15, ramp_months=6, start_month=12),
        # Month 18: reduce epsilon (L3)
        Intervention("epsilon", target=0.15, ramp_months=6, start_month=18),
    ]

    # Scenario 3: Correct sequence — B_i first, then activation
    correct_order = [
        # Month 0-6: reduce B_i first (L4)
        Intervention("B_i", target=0.15, ramp_months=6, start_month=0),
        # Month 6: activate outreach (L1) — B_i is now low
        Intervention("signal_fidelity", target=0.70, ramp_months=3, start_month=6),
        Intervention("outreach_mode", target=0.80, ramp_months=3, start_month=6),
        # Month 6: throttle complexity (L5)
        Intervention("Y_bias", target=0.4, ramp_months=3, start_month=6),
        Intervention("S_weight", target=0.7, ramp_months=3, start_month=6),
        # Month 12: reduce epsilon (L3)
        Intervention("epsilon", target=0.15, ramp_months=6, start_month=12),
        # Month 18: reduce kappa (L6)
        Intervention("decentralization_policy", target=0.06, ramp_months=12, start_month=18),
    ]

    # Scenario 4: Emergency — all levers at month 36 (delayed response)
    # Simulates waiting until crisis is undeniable, then deploying everything.
    emergency = [
        Intervention("B_i", target=0.15, ramp_months=3, start_month=36),
        Intervention("signal_fidelity", target=0.70, ramp_months=3, start_month=36),
        Intervention("outreach_mode", target=0.80, ramp_months=3, start_month=36),
        Intervention("Y_bias", target=0.4, ramp_months=3, start_month=36),
        Intervention("S_weight", target=0.7, ramp_months=3, start_month=36),
        Intervention("epsilon", target=0.15, ramp_months=3, start_month=36),
        Intervention("decentralization_policy", target=0.06, ramp_months=6, start_month=36),
    ]

    return {
        "baseline": ("1. Baseline (no intervention)", baseline),
        "wrong_order": ("2. Wrong order (activate before B_i reduction)", wrong_order),
        "correct": ("3. Correct sequence (B_i first)", correct_order),
        "emergency": ("4. Emergency (all levers at month 36)", emergency),
    }


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

SCENARIO_COLORS = {
    "baseline": "#555555",
    "wrong_order": "#d62728",
    "correct": "#2ca02c",
    "emergency": "#ff7f0e",
}

SCENARIO_STYLES = {
    "baseline": "--",
    "wrong_order": "-.",
    "correct": "-",
    "emergency": ":",
}


def plot_phi_trajectory(results, save_path="phi_trajectory.png"):
    """Plot Phi over time for all scenarios with regime threshold bands."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # Regime bands
    ax.axhspan(0.0, 0.70, alpha=0.12, color="green", label="_")
    ax.axhspan(0.70, 1.00, alpha=0.12, color="orange", label="_")
    ax.axhspan(1.00, 2.50, alpha=0.12, color="red", label="_")

    # Threshold lines
    ax.axhline(0.70, color="orange", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.axhline(1.00, color="red", linewidth=0.8, linestyle="--", alpha=0.6)

    # Regime labels
    ax.text(2, 0.35, "Stable surplus", fontsize=9, color="green", alpha=0.7, ha="left")
    ax.text(2, 0.85, "Marginal (invisible to financial metrics)", fontsize=9, color="darkorange", alpha=0.7, ha="left")
    ax.text(2, 1.15, "Structural decay", fontsize=9, color="red", alpha=0.7, ha="left")

    for key, res in results.items():
        ax.plot(
            res["t_months"], res["derived"]["Phi"],
            color=SCENARIO_COLORS[key],
            linestyle=SCENARIO_STYLES[key],
            linewidth=2.2,
            label=res["name"],
        )

    ax.set_xlabel("Time (months)", fontsize=11)
    ax.set_ylabel("\u03a6 (maintenance burden ratio)", fontsize=11)
    ax.set_title("Infrastructure Stability: \u03a6 Trajectory Under Different Intervention Sequences", fontsize=13)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    ax.set_xlim(0, None)
    ax.set_ylim(0, 2.5)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    print(f"Saved: {save_path}")
    return fig


def plot_state_variables(results, save_path="state_variables.png"):
    """Plot key state and derived variables for all scenarios."""
    fig = plt.figure(figsize=(14, 10))
    gs = gridspec.GridSpec(2, 3, hspace=0.35, wspace=0.30)

    panels = [
        (gs[0, 0], "C", "state", "System complexity (C)", None),
        (gs[0, 1], "L_f_active", "derived", "Effective labor (L_f_active)", None),
        (gs[0, 2], "p_engage", "state", "Engagement probability (p_engage)", [0, 1]),
        (gs[1, 0], "kappa", "state", "Coupling coefficient (\u03ba)", None),
        (gs[1, 1], "prior_dismissal", "state", "Prior dismissal resistance", None),
        (gs[1, 2], "F", "derived", "Cascade risk (F = \u03ba\u00b7\u03a6)", None),
    ]

    for gs_pos, var, source, title, ylim in panels:
        ax = fig.add_subplot(gs_pos)
        for key, res in results.items():
            if source == "state":
                data = res["state"][var]
            else:
                data = res["derived"][var]
            ax.plot(
                res["t_months"], data,
                color=SCENARIO_COLORS[key],
                linestyle=SCENARIO_STYLES[key],
                linewidth=1.8,
                label=res["name"],
            )
        ax.set_xlabel("Months", fontsize=9)
        ax.set_title(title, fontsize=10)
        ax.grid(True, alpha=0.3)
        if ylim:
            ax.set_ylim(ylim)

    # Single legend at bottom
    handles, labels = fig.axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=8,
              bbox_to_anchor=(0.5, -0.02), framealpha=0.9)

    fig.suptitle("State Variable Trajectories by Scenario", fontsize=13, y=1.01)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    show = "--show" in sys.argv

    scenarios = make_scenarios()
    results = {}

    for key, (name, interventions) in scenarios.items():
        print(f"Running: {name}")
        results[key] = run_scenario(name, interventions, t_months=120)

    # Print summary table
    print("\n--- Phi at key timepoints ---")
    print(f"{'Scenario':<50} {'12mo':>7} {'36mo':>7} {'60mo':>7} {'120mo':>7}")
    print("-" * 80)
    for key, res in results.items():
        t = res["t_months"]
        phi = res["derived"]["Phi"]
        vals = []
        for target_month in [12, 36, 60, 120]:
            idx = np.argmin(np.abs(t - target_month))
            vals.append(f"{phi[idx]:.3f}")
        print(f"{res['name']:<50} {'  '.join(vals)}")

    print()
    plot_phi_trajectory(results)
    plot_state_variables(results)

    if show:
        plt.show()


if __name__ == "__main__":
    main()

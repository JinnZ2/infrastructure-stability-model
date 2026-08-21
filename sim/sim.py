"""
Infrastructure Stability Model — ODE Simulation Engine

Simulates the coupled energy-material-labor system defined in system-model.json.
Demonstrates how intervention lever sequencing determines whether Phi (maintenance
burden ratio) stabilizes or crosses the structural decay threshold.

Usage:
  python3 sim/sim.py                # run core 4-scenario comparison
  python3 sim/sim.py sweep          # parameter sensitivity analysis
  python3 sim/sim.py handoff        # temporal cohort handoff visualization
  python3 sim/sim.py shocks         # stochastic disruption Monte Carlo (see F-013)
  python3 sim/sim.py enso           # ENSO common-mode forcing vs the Poisson assumption
  python3 sim/sim.py rate           # is the collapse condition a level or a rate?
  python3 sim/sim.py all            # run everything
  python3 sim/sim.py --show         # also display interactive plots (with any mode)

Plots are written to figures/ at the repository root.

Authors: Kavik, Claude (Anthropic)
License: CC0 1.0 Universal
"""

import os
import sys
from dataclasses import dataclass, field, replace
from typing import Callable, Optional

import numpy as np
from scipy.integrate import solve_ivp
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

    # Climate common-mode multiplier on effective labor bandwidth.
    # 1.0 = no climate forcing, which is the default and reproduces every
    # result committed before the ENSO layer existed. Driven by ENSOForcing
    # when one is supplied. See ledger F-013.
    "L_climate_mult": 1.0,

    # Re-suppression penalty
    "suppression_penalty_rate": 4.0,  # rate of prior_dismissal damage
    "B_i_activation_threshold": 0.3,  # B_i above this during outreach causes damage

    # --- State feedback gains (ledger F-014) --------------------------------
    # Zero by default. At zero these terms vanish and the model reproduces
    # every result committed before 2026-08-21 exactly, which is why the
    # legacy behavior is the zero-gain limit rather than a separate code path.
    #
    # They are zero because the original ODEs had no state dependence at all:
    # dC/dt, dL_training/dt and dkappa/dt were functions of parameters only,
    # so C, L_training and kappa were straight ramps, Phi was a readout that
    # fed back into nothing, and no perturbation to those variables could
    # propagate. Use FEEDBACK_PARAMS to switch them on.
    "a3_phi_complexity": 0.0,     # Phi above threshold constrains complexity growth
    "b4_mentor_capacity": 0.0,    # training throughput limited by experienced staff
    "c3_phi_coupling": 0.0,       # Phi above threshold ratchets coupling tighter
    "phi_feedback_threshold": 0.70,  # marginal regime boundary
    "L_f_reference": 0.85,        # L_f_active at which mentor capacity is nominal
}


# Feedback-enabled parameter set. Gains are asserted, not calibrated — they set
# the strength of three mechanisms, not their existence:
#
#   a3  Tainter. Maintenance burden constrains further complexity: past the
#       marginal threshold you cannot commission what you cannot maintain, and
#       past 1.0 things fail and are not replaced.
#   b4  Mentor capacity. Training throughput is bounded by how many experienced
#       people are available to teach, which is L_f_active. This is the same
#       claim the L2 lever makes about older nodes as mentor hubs.
#   c3  Stress ratchet. Under maintenance stress, operators defer redundancy
#       and tighten coupling to hold service, which raises kappa.
FEEDBACK_PARAMS = dict(PARAMS)
FEEDBACK_PARAMS.update({
    "a3_phi_complexity": 0.06,
    "b4_mentor_capacity": 1.0,
    "c3_phi_coupling": 0.03,
})

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


def get_effective_params(t_years, base_params, interventions, forcing=None):
    """
    Apply active interventions, then climate forcing, to get effective
    parameter values at time t.

    Order matters: interventions are decisions, forcing is weather. A lever
    that targets B_i=0.15 sets B_i to 0.15 whatever the climate is doing; the
    climate then scales the physical terms on top of that. Reversing the order
    would let a drought undo a policy, which is not what either represents.

    Two interventions on the SAME parameter compose by sequence, not by
    overwrite: the later one ramps from whatever the earlier one had reached.
    Before this was fixed (ledger F-017) each intervention was evaluated
    against the pristine base value and the last one in the list won outright,
    so a second intervention on a parameter silently erased the first — and
    before its own start_month it returned the base value, clobbering an
    active earlier intervention with the untouched baseline. A two-stage
    schedule on one parameter therefore did nothing at all.
    """
    t_months = t_years * 12.0
    params = dict(base_params)
    for iv in sorted(interventions,
                     key=lambda i: (i.start_month if i.start_month is not None
                                    else float("-inf"))):
        params[iv.param] = iv.get_value(t_months, params[iv.param])
    if forcing is not None:
        params = forcing.apply(params, t_months)
    return params


# ---------------------------------------------------------------------------
# Climate common-mode forcing (ENSO)
# ---------------------------------------------------------------------------
#
# Added 2026-08-21. See ledger F-013, F-014, F-015.
#
# The committed shock model (run_stochastic_shocks) draws disruptions from a
# Poisson process, recovers in 3 months, and perturbs only complexity and the
# training labor channel. Every one of those three choices is contradicted by
# the ENSO literature:
#
#   independence   ENSO is quasi-periodic, not memoryless. Events recur on a
#                  2-7 year cycle, and teleconnections correlate their impacts
#                  across widely separated regions in the same year.
#
#   recovery time  Callahan & Mankin (Science, 2023) find country-level growth
#                  depressed for at least five years after an event, with a
#                  tail out to fourteen. A 3-month recovery is off by more than
#                  an order of magnitude, and it guarantees the system returns
#                  to baseline between events.
#
#   single channel ENSO is a COMMON-MODE driver. It raises maintenance demand
#                  (damage), lowers primary energy throughput (irradiance and
#                  hydrological deficits), and lowers effective labor (heat
#                  stress on outdoor work) in the same phase. Phi = Em/(E*L_f)
#                  is therefore hit in numerator and denominator at once.
#
# Every coefficient below is a rough order-of-magnitude reading of that
# literature, not a calibration. They are exposed so they can be argued with.

@dataclass
class ENSOForcing:
    """
    A common-mode climate driver acting on Em, E, and L_f together.

    Set common_mode=False and recovery_years=0 with quasi_periodic=False to
    recover the behavior of the committed Poisson shock model; that
    equivalence is checked explicitly in run_enso_comparison.
    """

    # --- arrival structure ---
    quasi_periodic: bool = True
    period_years: float = 4.0       # ENSO recurrence. 2-7yr observed; ~4 typical.
    period_jitter: float = 0.9      # sd in years. Quasi-periodic, not clockwork.
    rate_per_year: float = 0.4      # used only when quasi_periodic is False

    # --- event shape ---
    event_width_months: float = 9.0   # duration of the peak phase
    amplitude_lo: float = 0.5         # event-to-event strength spread
    amplitude_hi: float = 1.5

    # --- persistence after the event ---
    recovery_years: float = 5.0     # Callahan & Mankin: >=5yr depressed growth
    residual_fraction: float = 0.35  # share of peak impact that persists and decays

    # --- channels (fractional impact at unit amplitude, at peak) ---
    common_mode: bool = True
    Em_surge: float = 0.25          # maintenance demand up
    E_deficit: float = 0.08         # primary energy throughput down
    L_deficit: float = 0.06         # effective labor bandwidth down
    C_bump: float = 0.30            # complexity spike, as in the committed model
    L_training_loss: float = 0.15   # training-channel loss, as in the committed model

    # populated by schedule()
    times: tuple = ()
    magnitudes: tuple = ()

    def schedule(self, t_months_total, rng):
        """Draw an arrival schedule. Returns a new forcing with times filled in."""
        if self.quasi_periodic:
            times, t = [], rng.uniform(0.0, self.period_years) * 12.0
            while t < t_months_total:
                times.append(t)
                gap = max(1.0, rng.normal(self.period_years, self.period_jitter))
                t += gap * 12.0
        else:
            n = rng.poisson(self.rate_per_year * (t_months_total / 12.0))
            times = sorted(rng.uniform(0, t_months_total, n))

        mags = rng.uniform(self.amplitude_lo, self.amplitude_hi, len(times))
        return replace(self, times=tuple(times), magnitudes=tuple(mags))

    def intensity(self, t_months):
        """
        Total forcing intensity at time t: the superposition of every event's
        peak phase and its decaying residual.

        The residual is what makes recovery time matter. With recovery_years
        at 5 and a period of 4, a new event arrives before the previous one
        has decayed, so intensity accumulates instead of resetting.
        """
        total = 0.0
        for start, mag in zip(self.times, self.magnitudes):
            elapsed = t_months - start
            if elapsed < 0:
                continue
            if elapsed < self.event_width_months:
                # peak phase: half-sine, so the forcing is continuous at both
                # ends and the stiff solver does not have to chase a step
                frac = elapsed / self.event_width_months
                total += mag * np.sin(np.pi * frac)
            elif self.recovery_years > 0:
                # persistent drag, exponential decay over the recovery timescale
                tau = self.recovery_years * 12.0
                total += mag * self.residual_fraction * np.exp(
                    -(elapsed - self.event_width_months) / tau)
        return total

    def apply(self, params, t_months):
        """Return params with the common-mode channels scaled by intensity."""
        x = self.intensity(t_months)
        if x <= 0.0:
            return params
        out = dict(params)
        if self.common_mode:
            out["alpha"] = params["alpha"] * (1.0 + self.Em_surge * x)
            out["E"] = params["E"] * max(0.05, 1.0 - self.E_deficit * x)
            out["L_climate_mult"] = params["L_climate_mult"] * max(
                0.05, 1.0 - self.L_deficit * x)
        return out

    def state_perturbation(self, t_months):
        """
        Direct perturbation of C and L_training, matching the channels the
        committed Poisson model used. Kept separate from apply() so the two
        mechanisms can be enabled independently.
        """
        x = self.intensity(t_months)
        return self.C_bump * x, max(0.05, 1.0 - self.L_training_loss * x)


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


def ode_system(t, y, base_params, interventions, forcing=None):
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

    # Get effective parameters (with interventions and climate forcing applied)
    p = get_effective_params(t, base_params, interventions, forcing)

    # Derived quantities
    beta_eff = p["beta0"] + p["gamma"] * kappa
    Em = p["alpha"] * C ** beta_eff
    L_latent_recovered = p["L_latent"] * p_engage * (1.0 - p["B_i"])
    L_f_active = max(0.01, (L_training * (1.0 - p["epsilon"]) + L_latent_recovered)
                     * p["L_climate_mult"])
    Phi = Em / (p["E"] * L_f_active)

    # --- Derivatives ---

    # Excess maintenance burden above the marginal threshold. This is the
    # single quantity that carries state back into the dynamics; with the
    # gains at zero it multiplies nothing and the system is a set of ramps.
    phi_excess = max(0.0, Phi - p["phi_feedback_threshold"])

    # dC/dt: complexity dynamics, constrained by maintenance burden
    dC = (p["a1"] * p["Y_bias"] - p["a2"] * p["S_weight"]
          - p["a3_phi_complexity"] * phi_excess * C)

    # dL_training/dt: training labor pipeline, throughput bounded by the
    # experienced staff available to teach
    mentor_capacity = 1.0
    if p["b4_mentor_capacity"] > 0.0:
        ratio = L_f_active / max(1e-6, p["L_f_reference"])
        mentor_capacity = 1.0 + p["b4_mentor_capacity"] * (ratio - 1.0)
        mentor_capacity = float(np.clip(mentor_capacity, 0.0, 3.0))
    dL_training = (-p["b1"] * p["epsilon"] - p["b2"] * p["I"]
                   + p["b3"] * p["T_rate"] * mentor_capacity)

    # dp_engage/dt: engagement probability (Bayesian-like update)
    signal_eff = p["signal_fidelity"] * (1.0 + p["outreach_mode"] * p["gamma_t"] * p["k_avg"])
    dp_engage = (signal_eff * (1.0 - p_engage) / prior_dismissal_state
                 - p["decay_rate"] * p_engage * p["I"])

    # dkappa/dt: coupling dynamics (ratchet character), tightened by stress
    dkappa = (p["c1"] * p["optimization_pressure"]
              - p["c2"] * p["decentralization_policy"]
              + p["c3_phi_coupling"] * phi_excess)

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


def compute_derived(t_array, y_array, base_params, interventions, forcing=None):
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

        p = get_effective_params(t, base_params, interventions, forcing)

        beta_eff = p["beta0"] + p["gamma"] * kappa
        Em = p["alpha"] * C ** beta_eff
        L_latent_recovered = p["L_latent"] * p_engage * (1.0 - p["B_i"])
        L_f_active = max(0.01, (L_training * (1.0 - p["epsilon"]) + L_latent_recovered)
                         * p["L_climate_mult"])
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

def run_scenario(name, interventions, t_months=120, params=None, y0=None,
                 forcing=None):
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
        args=(params, interventions, forcing),
        rtol=1e-6,
        atol=1e-8,
        max_step=0.05,
    )

    if not sol.success:
        print(f"Warning: solver failed for scenario '{name}': {sol.message}")

    derived = compute_derived(sol.t, sol.y, params, interventions, forcing)

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


def plot_phi_trajectory(results, save_path=None):
    """Plot Phi over time for all scenarios with regime threshold bands."""
    save_path = save_path or _fig("phi_trajectory.png")
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


def plot_state_variables(results, save_path=None):
    """Plot key state and derived variables for all scenarios."""
    save_path = save_path or _fig("state_variables.png")
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


# ===========================================================================
# EXTENSION 1: Parameter Sensitivity Sweep
# ===========================================================================

def run_sensitivity_sweep(save_prefix="sensitivity", n_points=40):
    """Vary epsilon, B_i, and signal_fidelity; show Phi response at 60 months."""
    print("\n=== Parameter Sensitivity Sweep ===")

    # --- 1D sweeps: vary one parameter, measure Phi at 60 months ---
    sweep_params = [
        ("epsilon", np.linspace(0.0, 0.80, n_points),
         "Labor exclusion coefficient (\u03b5)", "Reduces effective training labor"),
        ("B_i", np.linspace(0.0, 0.90, n_points),
         "Signal obstruction (B_i)", "Blocks latent node recovery"),
        ("signal_fidelity", np.linspace(0.0, 1.0, n_points),
         "Signal fidelity", "Genuine vs theatrical outreach quality"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for ax, (param_name, values, xlabel, desc) in zip(axes, sweep_params):
        phi_60 = []
        for val in values:
            params = dict(PARAMS)
            params[param_name] = val
            # No interventions — pure parameter effect
            res = run_scenario("_sweep", [], t_months=60, params=params)
            idx = np.argmin(np.abs(res["t_months"] - 60))
            phi_60.append(res["derived"]["Phi"][idx])

        ax.plot(values, phi_60, color="#1f77b4", linewidth=2)
        ax.axhline(0.70, color="orange", linewidth=0.8, linestyle="--", alpha=0.6)
        ax.axhline(1.00, color="red", linewidth=0.8, linestyle="--", alpha=0.6)
        ax.axhspan(0.0, 0.70, alpha=0.08, color="green")
        ax.axhspan(0.70, 1.00, alpha=0.08, color="orange")
        ax.axhspan(1.00, max(phi_60) * 1.1, alpha=0.08, color="red")

        # Mark baseline value
        baseline_val = PARAMS[param_name]
        baseline_idx = np.argmin(np.abs(values - baseline_val))
        ax.axvline(baseline_val, color="gray", linewidth=1, linestyle=":", alpha=0.7)
        ax.plot(baseline_val, phi_60[baseline_idx], "ko", markersize=6)
        ax.annotate("baseline", (baseline_val, phi_60[baseline_idx]),
                    textcoords="offset points", xytext=(8, 8), fontsize=8, color="gray")

        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel("\u03a6 at 60 months", fontsize=10)
        ax.set_title(f"\u03a6 sensitivity to {param_name}", fontsize=11)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Parameter Sensitivity: \u03a6 at 60 Months vs Single Parameter Variation",
                 fontsize=13, y=1.02)
    fig.tight_layout()
    path_1d = _fig(f"{save_prefix}_1d.png")
    fig.savefig(path_1d, dpi=150, bbox_inches="tight")
    print(f"Saved: {path_1d}")

    # --- 2D heatmap: epsilon vs B_i ---
    print("Running epsilon x B_i heatmap...")
    n2d = 30
    eps_range = np.linspace(0.0, 0.70, n2d)
    bi_range = np.linspace(0.0, 0.80, n2d)
    phi_grid = np.zeros((n2d, n2d))

    for i, eps_val in enumerate(eps_range):
        for j, bi_val in enumerate(bi_range):
            params = dict(PARAMS)
            params["epsilon"] = eps_val
            params["B_i"] = bi_val
            res = run_scenario("_heatmap", [], t_months=60, params=params)
            idx = np.argmin(np.abs(res["t_months"] - 60))
            phi_grid[j, i] = res["derived"]["Phi"][idx]

    fig2, ax2 = plt.subplots(figsize=(9, 7))
    im = ax2.contourf(eps_range, bi_range, phi_grid,
                      levels=[0, 0.5, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 3.0],
                      cmap="RdYlGn_r")
    cbar = fig2.colorbar(im, ax=ax2, label="\u03a6 at 60 months")

    # Threshold contours
    cs1 = ax2.contour(eps_range, bi_range, phi_grid, levels=[0.7],
                      colors=["orange"], linewidths=2, linestyles="--")
    ax2.clabel(cs1, fmt="\u03a6=0.7", fontsize=9)
    cs2 = ax2.contour(eps_range, bi_range, phi_grid, levels=[1.0],
                      colors=["red"], linewidths=2, linestyles="-")
    ax2.clabel(cs2, fmt="\u03a6=1.0", fontsize=9)

    # Baseline marker
    ax2.plot(PARAMS["epsilon"], PARAMS["B_i"], "w*", markersize=14,
             markeredgecolor="black", markeredgewidth=1.2)
    ax2.annotate("baseline", (PARAMS["epsilon"], PARAMS["B_i"]),
                textcoords="offset points", xytext=(10, -12), fontsize=9,
                color="white", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="white", lw=1.5))

    ax2.set_xlabel("Labor exclusion (\u03b5)", fontsize=11)
    ax2.set_ylabel("Signal obstruction (B_i)", fontsize=11)
    ax2.set_title("Stability Landscape: \u03a6 at 60 Months", fontsize=13)
    fig2.tight_layout()
    path_2d = _fig(f"{save_prefix}_2d.png")
    fig2.savefig(path_2d, dpi=150, bbox_inches="tight")
    print(f"Saved: {path_2d}")

    return fig, fig2


# ===========================================================================
# EXTENSION 2: Temporal Cohort Handoff
# ===========================================================================

def ode_system_cohort(t, y, base_params, interventions):
    """
    7-variable ODE with age-cohort decomposition.

    State: [C, L_old, L_young, p_engage, kappa, prior_dismissal, mentor_hours]

    L_old: older high-R_i nodes (declining via retirement)
    L_young: younger high-A_i nodes (ramping via mentor-dependent learning curve)
    mentor_hours: cumulative mentorship contact (drives learning curve)
    """
    C, L_old, L_young, p_engage, kappa, prior_dismissal_state, mentor_hours = y

    # Domain clamps
    C = max(0.1, C)
    L_old = max(0.01, L_old)
    L_young = max(0.01, L_young)
    p_engage = np.clip(p_engage, 0.0, 1.0)
    kappa = max(0.01, kappa)
    prior_dismissal_state = max(0.3, prior_dismissal_state)
    mentor_hours = max(0.0, mentor_hours)

    p = get_effective_params(t, base_params, interventions)

    # Derived
    beta_eff = p["beta0"] + p["gamma"] * kappa
    Em = p["alpha"] * C ** beta_eff
    L_latent_recovered = p["L_latent"] * p_engage * (1.0 - p["B_i"])
    L_training_total = (L_old + L_young) * (1.0 - p["epsilon"]) + L_latent_recovered
    L_f_active = max(0.01, L_training_total)

    # --- Derivatives ---

    # Complexity
    dC = p["a1"] * p["Y_bias"] - p["a2"] * p["S_weight"]

    # Older nodes: retirement curve (sigmoid decline)
    # Retirement accelerates after year 5, steep by year 10
    t_years = t
    retirement_rate = p.get("retirement_rate", 0.06)
    retirement_accel = p.get("retirement_accel", 0.008)
    dL_old = -(retirement_rate + retirement_accel * t_years) * L_old

    # Younger nodes: mentor-dependent learning curve (sigmoid)
    # Learning rate depends on mentor contact density (L_old * pairing ratio)
    mentor_density = L_old * p.get("pair_ratio", 2.0)
    # Sigmoid learning: slow start, accelerating, then saturating
    learning_ceiling = p.get("young_ceiling", 1.2)
    learning_rate = p.get("young_learning_rate", 0.15)
    gap_to_ceiling = max(0.0, learning_ceiling - L_young)
    dL_young = learning_rate * mentor_density * gap_to_ceiling * (L_young / (L_young + 0.1))

    # Engagement (same as base model)
    signal_eff = p["signal_fidelity"] * (1.0 + p["outreach_mode"] * p["gamma_t"] * p["k_avg"])
    dp_engage = (signal_eff * (1.0 - p_engage) / prior_dismissal_state
                 - p["decay_rate"] * p_engage * p["I"])

    # Coupling
    dkappa = p["c1"] * p["optimization_pressure"] - p["c2"] * p["decentralization_policy"]

    # Re-suppression
    activation_intensity = p["signal_fidelity"] * p["outreach_mode"]
    B_i_excess = max(0.0, p["B_i"] - p["B_i_activation_threshold"])
    resuppression = p["suppression_penalty_rate"] * activation_intensity * B_i_excess
    dp_engage -= resuppression * p_engage
    d_prior_dismissal = resuppression

    # Mentor hours accumulator
    d_mentor_hours = mentor_density

    return [dC, dL_old, dL_young, dp_engage, dkappa, d_prior_dismissal, d_mentor_hours]


def run_handoff_analysis(save_path=None):
    """Simulate and visualize the older→younger cohort handoff."""
    save_path = save_path or _fig("temporal_handoff.png")
    print("\n=== Temporal Cohort Handoff Analysis ===")

    # Correct-sequence interventions (same as core scenario 3)
    interventions = [
        Intervention("B_i", target=0.15, ramp_months=6, start_month=0),
        Intervention("signal_fidelity", target=0.70, ramp_months=3, start_month=6),
        Intervention("outreach_mode", target=0.80, ramp_months=3, start_month=6),
        Intervention("Y_bias", target=0.4, ramp_months=3, start_month=6),
        Intervention("S_weight", target=0.7, ramp_months=3, start_month=6),
        Intervention("epsilon", target=0.15, ramp_months=6, start_month=12),
        Intervention("decentralization_policy", target=0.06, ramp_months=12, start_month=18),
    ]

    params = dict(PARAMS)
    # Additional cohort params
    params["retirement_rate"] = 0.06
    params["retirement_accel"] = 0.008
    params["pair_ratio"] = 2.0
    params["young_ceiling"] = 1.2
    params["young_learning_rate"] = 0.15

    scenarios = {}

    # Scenario A: Early mentorship pairing (month 0)
    for label, pair_start, pair_ratio, retire_rate in [
        ("Early mentorship (month 0)", 0, 2.0, 0.06),
        ("Late mentorship (month 24)", 24, 2.0, 0.06),
        ("Early + accelerated retirement", 0, 2.0, 0.10),
    ]:
        p = dict(params)
        p["pair_ratio"] = pair_ratio
        p["retirement_rate"] = retire_rate

        for iv in interventions:
            iv._activated_at = None

        # State: [C, L_old, L_young, p_engage, kappa, prior_dismissal, mentor_hours]
        # Late mentorship: set pair_ratio to 0 initially, ramp at start month
        ivs = list(interventions)
        if pair_start > 0:
            p["pair_ratio"] = 0.0
            ivs.append(Intervention("pair_ratio", target=2.0, ramp_months=6,
                                    start_month=pair_start))
            for iv in ivs:
                iv._activated_at = None

        y0 = np.array([1.2, 0.60, 0.15, 0.10, 0.50, 1.2, 0.0])
        t_months = 180  # 15 years to see full handoff
        t_span = (0.0, t_months / 12.0)
        t_eval = np.linspace(t_span[0], t_span[1], 600)

        sol = solve_ivp(
            ode_system_cohort, t_span, y0, method="Radau",
            t_eval=t_eval, args=(p, ivs),
            rtol=1e-6, atol=1e-8, max_step=0.05,
        )

        # Compute Phi for this cohort model
        n = len(sol.t)
        Phi = np.zeros(n)
        L_f = np.zeros(n)
        for i in range(n):
            pp = get_effective_params(sol.t[i], p, ivs)
            C_i = sol.y[0, i]
            L_old_i = sol.y[1, i]
            L_young_i = sol.y[2, i]
            p_eng_i = sol.y[3, i]
            kap_i = sol.y[4, i]
            beta_eff = pp["beta0"] + pp["gamma"] * kap_i
            Em = pp["alpha"] * C_i ** beta_eff
            L_lat = pp["L_latent"] * p_eng_i * (1.0 - pp["B_i"])
            lf = max(0.01, (L_old_i + L_young_i) * (1.0 - pp["epsilon"]) + L_lat)
            Phi[i] = Em / (pp["E"] * lf)
            L_f[i] = lf

        scenarios[label] = {
            "t_months": sol.t * 12.0,
            "L_old": sol.y[1],
            "L_young": sol.y[2],
            "L_f": L_f,
            "Phi": Phi,
        }

    # Plot
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    colors = ["#2ca02c", "#d62728", "#ff7f0e"]

    for idx, (label, data) in enumerate(scenarios.items()):
        t = data["t_months"]
        c = colors[idx]

        # Top-left: L_old over time
        axes[0, 0].plot(t, data["L_old"], color=c, linewidth=2, label=label)
        # Top-right: L_young over time
        axes[0, 1].plot(t, data["L_young"], color=c, linewidth=2, label=label)
        # Bottom-left: Total L_f with components
        axes[1, 0].plot(t, data["L_f"], color=c, linewidth=2, label=label)
        # Bottom-right: Phi trajectory
        axes[1, 1].plot(t, data["Phi"], color=c, linewidth=2, label=label)

    axes[0, 0].set_title("Older cohort (L_old) — retirement decline", fontsize=11)
    axes[0, 0].set_ylabel("Labor bandwidth")
    axes[0, 1].set_title("Younger cohort (L_young) — mentor-dependent ramp", fontsize=11)
    axes[0, 1].set_ylabel("Labor bandwidth")
    axes[1, 0].set_title("Total effective labor (L_f_active)", fontsize=11)
    axes[1, 0].set_ylabel("Labor bandwidth")

    # Phi plot with regime bands
    ax_phi = axes[1, 1]
    ax_phi.axhspan(0.0, 0.70, alpha=0.10, color="green")
    ax_phi.axhspan(0.70, 1.00, alpha=0.10, color="orange")
    ax_phi.axhspan(1.00, 2.0, alpha=0.10, color="red")
    ax_phi.axhline(0.70, color="orange", linewidth=0.8, linestyle="--", alpha=0.5)
    ax_phi.axhline(1.00, color="red", linewidth=0.8, linestyle="--", alpha=0.5)
    ax_phi.set_title("\u03a6 trajectory — handoff timing determines stability", fontsize=11)
    ax_phi.set_ylabel("\u03a6")

    for ax in axes.flat:
        ax.set_xlabel("Months")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    fig.suptitle("Temporal Cohort Handoff: Older Node Retirement vs Younger Node Ramp",
                 fontsize=13, y=1.01)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


# ===========================================================================
# EXTENSION 3: Stochastic Shocks (Monte Carlo)
# ===========================================================================

def run_stochastic_shocks(save_path=None, n_runs=50, seed=42):
    """Monte Carlo with Poisson-distributed disruption events."""
    save_path = save_path or _fig("stochastic_shocks.png")
    print(f"\n=== Stochastic Shock Simulation ({n_runs} runs) ===")
    rng = np.random.default_rng(seed)

    t_months_total = 120
    t_span = (0.0, t_months_total / 12.0)
    n_eval = 500
    t_eval = np.linspace(t_span[0], t_span[1], n_eval)

    # Shock parameters
    shock_rate_per_year = 0.4        # expected shocks per year (~1 every 2.5yr)
    shock_C_bump = 0.3               # complexity spike per shock
    shock_L_fraction = 0.15          # fraction of L_training lost per shock
    shock_duration_months = 3        # recovery period

    def ode_with_shocks(t, y, base_params, interventions, shock_times, shock_magnitudes):
        """ODE with transient shock perturbations."""
        # Check active shocks
        C_shock = 0.0
        L_shock_mult = 1.0
        t_mo = t * 12.0
        for st, sm in zip(shock_times, shock_magnitudes):
            elapsed = t_mo - st
            if 0 <= elapsed < shock_duration_months:
                # Shock decays linearly over duration
                decay = 1.0 - elapsed / shock_duration_months
                C_shock += shock_C_bump * sm * decay
                L_shock_mult *= (1.0 - shock_L_fraction * sm * decay)

        # Modify state temporarily for this evaluation
        y_mod = list(y)
        y_mod[0] = y[0] + C_shock          # C gets bumped
        y_mod[1] = y[1] * L_shock_mult     # L_training reduced

        return ode_system(t, y_mod, base_params, interventions)

    # Two margin levels to compare
    margin_configs = [
        ("Correct sequence (\u03a6\u22480.31)",
         [  # Same as scenario 3
             Intervention("B_i", target=0.15, ramp_months=6, start_month=0),
             Intervention("signal_fidelity", target=0.70, ramp_months=3, start_month=6),
             Intervention("outreach_mode", target=0.80, ramp_months=3, start_month=6),
             Intervention("Y_bias", target=0.4, ramp_months=3, start_month=6),
             Intervention("S_weight", target=0.7, ramp_months=3, start_month=6),
             Intervention("epsilon", target=0.15, ramp_months=6, start_month=12),
             Intervention("decentralization_policy", target=0.06, ramp_months=12, start_month=18),
         ], "#2ca02c"),
        ("Wrong order (\u03a6\u22480.62)",
         [  # Same as scenario 2
             Intervention("signal_fidelity", target=0.70, ramp_months=2, start_month=3),
             Intervention("outreach_mode", target=0.80, ramp_months=2, start_month=3),
             Intervention("B_i", target=0.15, ramp_months=6, start_month=12),
             Intervention("epsilon", target=0.15, ramp_months=6, start_month=18),
         ], "#d62728"),
        ("Baseline (no intervention)",
         [], "#555555"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for ax, (config_name, interventions_template, color) in zip(axes, margin_configs):
        phi_runs = np.zeros((n_runs, n_eval))

        for run in range(n_runs):
            # Generate shock schedule
            n_shocks = rng.poisson(shock_rate_per_year * (t_months_total / 12.0))
            shock_times = np.sort(rng.uniform(0, t_months_total, n_shocks))
            shock_magnitudes = rng.uniform(0.5, 1.5, n_shocks)

            # Deep copy interventions
            ivs = [Intervention(iv.param, iv.target, iv.ramp_months, iv.start_month)
                   for iv in interventions_template]

            sol = solve_ivp(
                ode_with_shocks, t_span, INITIAL_STATE.copy(), method="Radau",
                t_eval=t_eval, args=(dict(PARAMS), ivs, shock_times, shock_magnitudes),
                rtol=1e-5, atol=1e-7, max_step=0.05,
            )

            if sol.success and len(sol.t) == n_eval:
                derived = compute_derived(sol.t, sol.y, dict(PARAMS), ivs)
                phi_runs[run] = derived["Phi"]
            else:
                phi_runs[run] = np.nan

        t_months_arr = t_eval * 12.0

        # Percentile envelope
        p5 = np.nanpercentile(phi_runs, 5, axis=0)
        p25 = np.nanpercentile(phi_runs, 25, axis=0)
        p50 = np.nanmedian(phi_runs, axis=0)
        p75 = np.nanpercentile(phi_runs, 75, axis=0)
        p95 = np.nanpercentile(phi_runs, 95, axis=0)

        # Regime bands
        ax.axhspan(0.0, 0.70, alpha=0.08, color="green")
        ax.axhspan(0.70, 1.00, alpha=0.08, color="orange")
        ax.axhspan(1.00, max(2.5, np.nanmax(p95) * 1.05), alpha=0.08, color="red")
        ax.axhline(0.70, color="orange", linewidth=0.8, linestyle="--", alpha=0.5)
        ax.axhline(1.00, color="red", linewidth=0.8, linestyle="--", alpha=0.5)

        # Envelope
        ax.fill_between(t_months_arr, p5, p95, alpha=0.15, color=color, label="5-95th pct")
        ax.fill_between(t_months_arr, p25, p75, alpha=0.30, color=color, label="25-75th pct")
        ax.plot(t_months_arr, p50, color=color, linewidth=2, label="Median")

        ax.set_xlabel("Months", fontsize=10)
        ax.set_ylabel("\u03a6", fontsize=10)
        ax.set_title(config_name, fontsize=11)
        ax.legend(fontsize=8, loc="upper left")
        ax.set_ylim(0, 2.5)
        ax.grid(True, alpha=0.3)

        # Count runs that cross Phi=1.0
        ever_above_1 = np.any(phi_runs > 1.0, axis=1)
        pct_decay = np.nanmean(ever_above_1) * 100
        ax.text(0.97, 0.97, f"{pct_decay:.0f}% enter decay",
                transform=ax.transAxes, ha="right", va="top", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    fig.suptitle(f"Stochastic Disruptions: \u03a6 Under Random Shocks ({n_runs} Monte Carlo runs)",
                 fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# ===========================================================================
# EXTENSION 4: ENSO common-mode forcing vs the Poisson shock assumption
# ===========================================================================

# Named configurations, each isolating one assumption in the committed shock
# model, so the difference can be attributed rather than just observed.
def _enso_ladder():
    """
    Factor ladder. Each rung changes exactly one thing from the rung above.

    A is the committed model's assumption set expressed in ENSOForcing terms.
    E and F are the two ENSO periodicities from the 2026 npj Climate and
    Atmospheric Science non-monotonic result: ~4 years under moderate warming,
    shortening to 2-3 years under extreme warming.
    """
    poisson_like = dict(
        quasi_periodic=False, recovery_years=0.0, common_mode=False,
        event_width_months=3.0, residual_fraction=0.0,
    )
    return [
        ("A. Poisson, 3mo recovery, single channel (committed)",
         ENSOForcing(**poisson_like), "#555555"),
        ("B. + multi-year persistence (Callahan-Mankin 5yr)",
         ENSOForcing(**{**poisson_like, "recovery_years": 5.0,
                        "residual_fraction": 0.35}), "#1f77b4"),
        ("C. + quasi-periodic arrivals (4yr ENSO cycle)",
         ENSOForcing(**{**poisson_like, "recovery_years": 5.0,
                        "residual_fraction": 0.35, "quasi_periodic": True,
                        "period_years": 4.0, "event_width_months": 9.0}),
         "#ff7f0e"),
        ("D. + common mode on Em, E and L_f together",
         ENSOForcing(quasi_periodic=True, period_years=4.0,
                     recovery_years=5.0, common_mode=True), "#d62728"),
        ("E. D with 2.5yr period (extreme-warming ENSO)",
         ENSOForcing(quasi_periodic=True, period_years=2.5, period_jitter=0.5,
                     recovery_years=5.0, common_mode=True), "#8c564b"),
    ]


def run_enso_comparison(save_path=None, n_runs=60, seed=7, t_months_total=120,
                        params=None, policy="correct"):
    """
    Does the Poisson independence assumption understate risk, and if so, which
    part of it is responsible?

    Runs the factor ladder under the correct-sequence intervention set, so any
    difference is attributable to the shock structure rather than to the
    policy. Reports median and 90th-percentile Phi at 120 months and the
    fraction of runs that finish above the Phi=1.0 cascade threshold.
    """
    save_path = save_path or _fig("enso_common_mode.png")
    params = dict(FEEDBACK_PARAMS if params is None else params)
    fb = "feedback on" if params["a3_phi_complexity"] else "feedback OFF (legacy)"
    print(f"\n=== ENSO Common-Mode Forcing ({n_runs} runs per rung, "
          f"{policy} policy, {fb}) ===")

    t_span = (0.0, t_months_total / 12.0)
    n_eval = 400
    t_eval = np.linspace(t_span[0], t_span[1], n_eval)

    def correct_sequence():
        return [
            Intervention("B_i", target=0.15, ramp_months=6, start_month=0),
            Intervention("signal_fidelity", target=0.70, ramp_months=3, start_month=6),
            Intervention("outreach_mode", target=0.80, ramp_months=3, start_month=6),
            Intervention("Y_bias", target=0.4, ramp_months=3, start_month=6),
            Intervention("S_weight", target=0.7, ramp_months=3, start_month=6),
            Intervention("epsilon", target=0.15, ramp_months=6, start_month=12),
            Intervention("decentralization_policy", target=0.06,
                         ramp_months=12, start_month=18),
        ]

    ladder = _enso_ladder()
    results = {}
    make_ivs = correct_sequence if policy == "correct" else (lambda: [])

    for label, template, color in ladder:
        phi_runs = np.zeros((n_runs, n_eval))
        for run in range(n_runs):
            # Same seed sequence per rung, so the arrival draws are comparable
            rng = np.random.default_rng(seed + run)
            forcing = template.schedule(t_months_total, rng)
            ivs = make_ivs()

            def rhs(t, y, prm, interventions, frc):
                C_bump, L_mult = frc.state_perturbation(t * 12.0)
                y_mod = list(y)
                y_mod[0] = y[0] + C_bump
                y_mod[1] = y[1] * L_mult
                return ode_system(t, y_mod, prm, interventions, frc)

            sol = solve_ivp(rhs, t_span, INITIAL_STATE.copy(), method="Radau",
                            t_eval=t_eval, args=(dict(params), ivs, forcing),
                            rtol=1e-6, atol=1e-8, max_step=0.05)
            derived = compute_derived(sol.t, sol.y, dict(params), ivs, forcing)
            phi_runs[run, :] = derived["Phi"]

        final = phi_runs[:, -1]
        results[label] = {
            "phi": phi_runs, "color": color,
            "median": float(np.median(final)),
            "p90": float(np.percentile(final, 90)),
            "p99": float(np.percentile(final, 99)),
            "worst": float(np.max(final)),
            "frac_cascade": float(np.mean(final >= 1.0)),
            "frac_marginal": float(np.mean(final >= 0.7)),
        }

    print(f"\n{'rung':<52}{'med':>7}{'p90':>7}{'p99':>7}{'max':>7}{'>=1.0':>7}")
    print("-" * 87)
    for label, r in results.items():
        print(f"{label:<52}{r['median']:>7.3f}{r['p90']:>7.3f}{r['p99']:>7.3f}"
              f"{r['worst']:>7.3f}{r['frac_cascade']:>7.0%}")

    base = results[ladder[0][0]]
    print(f"\n  ratio to the committed model (rung A):")
    print(f"  {'rung':<6}{'median':>9}{'p90':>9}{'p99':>9}{'max':>9}")
    for label, r in list(results.items())[1:]:
        print(f"  {label[:2]:<6}"
              + "".join(f"{r[k] / base[k]:>9.3f}" if base[k] else f"{'nan':>9}"
                        for k in ("median", "p90", "p99", "worst")))

    print(f"""
  Read the whole distribution. Common-mode forcing does not shift Phi, it
  WIDENS it: the median improves because the stabilizing complexity brake
  engages under sustained stress, while the upper tail gets substantially
  worse. Reporting the median or the mean would describe this as a mild
  improvement. See ledger F-020.

  At n={n_runs} the p90 ratios are NOT resolved against seed-to-seed variation --
  rung D's spread across master seeds exceeds its effect. The resolved figures
  in F-020 come from n=250 per seed across three seeds. Do not quote a ratio
  from a single run of this function as a result.""")

    _plot_enso(results, save_path)
    return results


def _plot_enso(results, save_path):
    fig = plt.figure(figsize=(16, 9))
    gs = gridspec.GridSpec(2, 2, hspace=0.32, wspace=0.24)

    ax = fig.add_subplot(gs[0, :])
    for label, r in results.items():
        phi = r["phi"]
        t = np.linspace(0, phi.shape[1], phi.shape[1]) / phi.shape[1] * 120
        med = np.median(phi, axis=0)
        ax.plot(t, med, color=r["color"], linewidth=2, label=label)
        ax.fill_between(t, np.percentile(phi, 10, axis=0),
                        np.percentile(phi, 90, axis=0),
                        color=r["color"], alpha=0.10)
    ax.axhline(1.0, color="#d62728", linestyle="--", linewidth=1)
    ax.axhline(0.7, color="#ff7f0e", linestyle=":", linewidth=1)
    ax.set_title("Phi under the same intervention, different shock structure "
                 "(median, 10-90 band)", fontsize=11)
    ax.set_xlabel("Months"); ax.set_ylabel("Phi")
    ax.legend(fontsize=7, loc="upper left"); ax.grid(True, alpha=0.3)

    ax = fig.add_subplot(gs[1, 0])
    labels = list(results)
    ax.barh(range(len(labels)), [results[l]["p90"] for l in labels],
            color=[results[l]["color"] for l in labels])
    ax.axvline(1.0, color="#d62728", linestyle="--", linewidth=1)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels([l[:2] for l in labels], fontsize=9)
    ax.invert_yaxis()
    ax.set_title("Phi at 120 months, 90th percentile", fontsize=10)
    ax.grid(True, alpha=0.3, axis="x")

    ax = fig.add_subplot(gs[1, 1])
    ax.barh(range(len(labels)), [results[l]["frac_cascade"] for l in labels],
            color=[results[l]["color"] for l in labels])
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels([l[:2] for l in labels], fontsize=9)
    ax.invert_yaxis()
    ax.set_title("Fraction of runs finishing at or above Phi=1.0", fontsize=10)
    ax.grid(True, alpha=0.3, axis="x")

    fig.savefig(save_path, dpi=110, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


# ===========================================================================
# EXTENSION 5: is the collapse condition a level or a rate?
# ===========================================================================

@dataclass
class PulseForcing:
    """
    A rectangular excess on one parameter: amplitude `amp` for `dur` months
    starting at `start`. Start and end levels are identical by construction,
    so any difference in outcome is attributable to the excursion alone.

    Used to discriminate rate dependence from integrated-dose dependence.
    Pulses with equal amp*dur deliver the same integrated forcing at
    different rates. A pure integrator cannot tell them apart.
    """
    param: str = "Y_bias"
    amp: float = 1.0
    dur: float = 12.0
    start: float = 6.0

    @property
    def area(self):
        return self.amp * self.dur

    def apply(self, params, t_months):
        if self.start <= t_months < self.start + self.dur:
            out = dict(params)
            out[self.param] = params[self.param] + self.amp
            return out
        return params

    def state_perturbation(self, t_months):
        """No direct state channel. Present so the interface matches ENSOForcing."""
        return 0.0, 1.0


def run_rate_vs_level(save_path=None, area=12.0, t_months_total=120):
    """
    The AMOC question asked of this model: is the collapse condition a level
    or a derivative?

    The Utrecht AMOC result is that circulation stability depends on the RATE
    of CO2 change rather than on any fixed temperature threshold — the
    collapse condition is a derivative, not a level. This repository states
    its entire warning vocabulary as levels (Phi < 0.7, 0.7-1.0, >= 1.0), so
    it is worth knowing whether this model can express a rate condition at all.

    Method: equal-area pulses. Every run starts and ends at the same forcing
    level and delivers the same integrated dose, spread over durations
    differing by 8x. A model that responds only to accumulated dose gives
    identical outcomes; a model with genuine rate dependence does not.

    The solver noise floor is measured, not assumed, by comparing the same
    configuration against itself at different tolerances — a spread below it
    is not evidence of rate dependence.
    """
    save_path = save_path or _fig("rate_vs_level.png")
    print(f"\n=== Rate vs Level (equal-area pulses, area = {area}) ===")

    durations = [12.0, 24.0, 48.0, 96.0]
    settings = [("feedback OFF (legacy)", PARAMS),
                ("feedback ON", FEEDBACK_PARAMS)]

    results = {}
    for label, prm in settings:
        rows = []
        for dur in durations:
            forcing = PulseForcing(amp=area / dur, dur=dur)
            r = run_scenario(f"{label} d={dur}", [], t_months=t_months_total,
                             params=dict(prm), forcing=forcing)
            rows.append({
                "dur": dur, "amp": forcing.amp,
                "C": float(r["state"]["C"][-1]),
                "kappa": float(r["state"]["kappa"][-1]),
                "Phi": float(r["derived"]["Phi"][-1]),
                "t": r["t_months"], "phi_series": r["derived"]["Phi"],
            })
        results[label] = rows

    # Measure the noise floor rather than assuming it: same configuration,
    # tighter solver tolerance. Spread below this is numerical, not physical.
    ref = PulseForcing(amp=area / 24.0, dur=24.0)
    loose = run_scenario("nf", [], t_months=t_months_total,
                         params=dict(FEEDBACK_PARAMS), forcing=ref)
    noise_floor = abs(float(loose["derived"]["Phi"][-1]) - float(
        run_scenario("nf2", [], t_months=t_months_total,
                     params=dict(FEEDBACK_PARAMS), forcing=ref
                     )["derived"]["Phi"][-1]))
    noise_floor = max(noise_floor, 1e-5)

    print(f"\n{'setting':<22}{'dur(mo)':>9}{'amp':>8}{'C@end':>10}"
          f"{'kappa@end':>11}{'Phi@end':>10}")
    print("-" * 70)
    for label, rows in results.items():
        for r in rows:
            print(f"{label:<22}{r['dur']:>9.0f}{r['amp']:>8.3f}"
                  f"{r['C']:>10.5f}{r['kappa']:>11.5f}{r['Phi']:>10.5f}")

    print(f"\nsolver noise floor on Phi: ~{noise_floor:.1e}")
    for label, rows in results.items():
        phis = [r["Phi"] for r in rows]
        spread = max(phis) - min(phis)
        verdict = ("RATE-DEPENDENT" if spread > 10 * noise_floor
                   else "no rate dependence (integrated dose only)")
        direction = ""
        if spread > 10 * noise_floor:
            slow_worse = phis[-1] > phis[0]
            direction = ("; the SLOW pulse ends worse" if slow_worse
                         else "; the FAST pulse ends worse")
        print(f"  {label:<22} spread {spread:.2e}  -> {verdict}{direction}")

    print("""
  Read the sign, not just the magnitude. An AMOC-type rate condition means
  fast forcing is more dangerous, because it outruns a restoring flux. The
  only feedback in this model is a stabilizing brake on complexity, so slow
  forcing is worse here: it stays under the threshold that engages the brake.
  Same phenomenon name, opposite sign, different mechanism. This model cannot
  currently represent a rate-triggered collapse — that needs a feedback that
  destabilizes under fast forcing, which nothing in the ODE provides.
  See ledger F-019.""")

    _plot_rate(results, noise_floor, save_path)
    return results


def _plot_rate(results, noise_floor, save_path):
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    for ax, (label, rows) in zip(axes, results.items()):
        for r in rows:
            ax.plot(r["t"], r["phi_series"], linewidth=1.8,
                    label=f"{r['dur']:.0f}mo x {r['amp']:.3f}")
        ax.axhline(1.0, color="#d62728", linestyle="--", linewidth=1)
        ax.axhline(0.7, color="#ff7f0e", linestyle=":", linewidth=1)
        phis = [r["Phi"] for r in rows]
        spread = max(phis) - min(phis)
        ax.set_title(f"{label}\nequal-area pulses, Phi spread {spread:.1e} "
                     f"(noise floor {noise_floor:.0e})", fontsize=10)
        ax.set_xlabel("Months"); ax.set_ylabel("Phi")
        ax.legend(fontsize=8, title="duration x amplitude"); ax.grid(True, alpha=0.3)
    fig.savefig(save_path, dpi=110, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


def run_core_scenarios(show=False):
    """Run the original 4-scenario comparison."""
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


def main():
    args = set(sys.argv[1:])
    show = "--show" in args
    args.discard("--show")

    mode = (args.pop() if args else "core")

    if mode in ("core", "all"):
        run_core_scenarios(show)
    if mode in ("sweep", "all"):
        run_sensitivity_sweep()
    if mode in ("handoff", "all"):
        run_handoff_analysis()
    if mode in ("shocks", "all"):
        run_stochastic_shocks()
    if mode in ("enso", "all"):
        run_enso_comparison(policy="baseline")
    if mode in ("rate", "all"):
        run_rate_vs_level()

    if mode not in ("core", "sweep", "handoff", "shocks", "enso", "rate", "all"):
        print(f"Unknown mode: {mode}")
        print("Usage: python3 sim/sim.py "
              "[core|sweep|handoff|shocks|enso|rate|all] [--show]")
        sys.exit(1)

    if show:
        plt.show()


if __name__ == "__main__":
    main()

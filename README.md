# infrastructure-stability-model

**Dynamic systems model for predicting infrastructure collapse via maintenance burden ratio, latent labor node activation, and coupling effects. Formal specification with JSON schemas, differential equations, intervention strategies, and measurement protocols — plus runnable simulations and a ledger of which claims survived them.**

-----

## What this is

A formal systems model for predicting when infrastructure maintenance becomes unsustainable — and what to do about it before the threshold is crossed.

Most infrastructure failures aren't caused by material scarcity. They're caused by a mismatch between maintenance energy demand and effective labor bandwidth, amplified by system coupling and accelerated by institutional suppression of high-skill workers. This model quantifies that mismatch, identifies intervention leverage points, and tests their time constants against a 3-5 year critical window.

The math is thermodynamic, not financial. Money is a coordination signal layered on top of physical flows. This model works at the physical layer.

-----

## Core metric

**Phi = E_m / (E * L_f_active)**

Where:

- `E_m` = maintenance energy demand, scaling nonlinearly with system complexity C and coupling kappa
- `E` = primary energy throughput
- `L_f_active` = effective skilled labor bandwidth — the real bottleneck

**Phi < 0.7** -> stable surplus. System can absorb shocks.
**0.7 <= Phi < 1.0** -> marginal. High sensitivity. Financial metrics will not detect this.
**Phi >= 1.0** -> structural decay. System drawing down reserves. Cascade synchronization probable.

The dangerous zone is the middle one. It doesn't look like a crisis from abstracted financial reporting. By the time Phi appears in quarterly metrics, correction cost has multiplied.

**Two caveats that the model's own runs forced.** Phi is not a bifurcation parameter — nothing in the implemented dynamics reads it, and the threshold at 1.0 is an interpretive band, not a demonstrated dynamical feature (ledger `F-014`). And Phi is not a welfare ordering: it falls when labour recovers *and* when complexity is destroyed, which are opposite outcomes, so it must always be reported alongside E_m, E, L_f_active and C (ledger `F-016`).

-----

## Key insight this model formalizes

**There are two labor channels, not one:**

1. **Training pipeline** — conventional. Time constant 3-7 years. Too slow for the critical window.
2. **Latent node recovery** — high-skill workers who exist but are institutionally suppressed. Time constant 0.5-2 years *if friction is removed correctly*.

The second channel is faster by an order of magnitude. It's also almost entirely ignored by standard workforce planning because the nodes aren't visible through credential systems.

**And there's a sequencing constraint:**

Signal obstruction (B_i) must be reduced *before* activation outreach begins in the same locality. Recruiting into a high-obstruction context gives the activated node a confirmed dismissal instead of a credible offer.

This claim used to be stated much more strongly here, and the model's own simulations cut it down. What survives is narrower and more useful — see below.

-----

## What has actually been run

Both engines run. Their results are recorded in [`legacy/ledger.json`](legacy/ledger.json); the protocol is in [`METHOD.md`](METHOD.md). Three findings changed what this repo claims:

**The sequencing penalty is not aggregate.** The README used to say wrong-order activation makes an intervention fail, and that most workforce initiatives fail there. The mean-field ODE says otherwise: at 120 months, Phi under wrong-order activation is 0.617 against a no-intervention baseline of 1.451 and a correct-sequence result of 0.307. Wrong order still stabilizes the system well under the 0.7 threshold. As a claim about aggregate labor or Phi, the original wording was falsified by the model that was written to demonstrate it. (Ledger `F-002`.)

**The damage is topological.** Running the same comparison on a 200-node trust network with heterogeneous R_i locates what the mean-field average hid. Wrong order versus correct order: 152 active nodes against 200, 48 permanently suppressed against 0, and hub survival at 30% against 100%. Across 5 communities, bridge-node survival falls to 22% and inter-community edges alive to 44%, while both orders still reach all five communities. Wrong-order activation is hub-destroying, not intervention-destroying. It leaves the network connected enough to function and too fragmented to propagate again — the bill arrives with the *next* campaign, which has never been simulated. (Ledger `F-003`.)

**The constraint is local, not global.** Regionally phased rollouts are safe: a region can begin activation while its neighbours are still reducing B_i, as long as each region's own B_i is down before its own outreach. The committed test for this did not actually test it — its schedule started B_i reduction everywhere at month 0, so no region was ever unprepared when leakage arrived. Rerunning with regions genuinely held at high B_i gives the same result, and a sweep of the leakage-intensity parameter puts the failure boundary above 4x its assumed value, which is stronger than a directly addressed signal. Safe within any regime where leaked signal is weaker than direct contact. (Ledger `F-004`.)

Figures for all of it are in [`figures/`](figures/).

-----

## What El Nino does to this model

Incorporating the 2026 ENSO literature ([`SOURCES.md`](SOURCES.md)) broke
three things, one of them load-bearing.

**The shock model could not show a shock.** `run_stochastic_shocks` draws
Poisson disruptions and reports the spread. There is no spread. Across 30 runs
drawing 1 to 7 shocks each, Phi at 120 months was 1.4509 every time — and
eight maximum-magnitude shocks are *bit-identical* to no shocks at all,
difference exactly 0.000e+00. The committed figure shows three flat lines.
(Ledger `F-013`.)

**The reason is that there was no feedback.** `dC/dt`, `dL_training/dt` and
`dkappa/dt` were functions of parameters only. Perturb C: nothing changes.
Perturb L_training: nothing changes. Perturb kappa: nothing changes. Three of
five state variables were straight ramps, and Phi was a readout that fed back
into nothing. **So there was no bifurcation at Phi = 1.0**, because a
bifurcation needs the state to influence its own evolution across a threshold.
That claim had been on the front of this repo since February and was never a
property of the model. State feedback has now been added — three gains,
defaulting to zero so every prior result reproduces exactly — and the
threshold behaviour is still undemonstrated, merely no longer impossible.
(Ledger `F-014`.)

**What ENSO actually changes is simultaneity, not frequency — and it changes
the tail, not the middle.** The first version of this section reported that
common mode raised the 90th-percentile Phi by 18%, and 35% at the
extreme-warming period. Those numbers are withdrawn. The forcing had been
wired into the Phi readout but not into the integrator, so they measured a
readout transformation over a trajectory that had never felt the climate
(ledger `F-018`). They were also quoted at a sample size that could not
resolve them: rung D's p90 ratio varied 1.004 to 1.194 across master seeds, a
spread larger than its own effect.

Rerun with the forcing genuinely driving the dynamics, at n=250 per seed
across three seeds, extreme-warming common mode against the committed
assumption set:

| statistic | ratio | seed range | resolved |
|---|---|---|---|
| median Phi | **0.916** | 0.007 | yes |
| p90 | 1.088 | 0.031 | yes |
| p99 | **1.321** | 0.051 | yes |
| max | **1.379** | 0.034 | yes |

Common-mode forcing **widens the distribution rather than shifting it**. The
median improves 8% — sustained stress engages the stabilizing complexity brake
— while the 99th percentile rises 32% and the maximum 38%. The typical year
gets slightly better and the bad year gets substantially worse.

Which means a summary that reports a mean or a median describes this as a mild
improvement. That is the fourth time in this repository that a scalar has
hidden the structure that matters, after aggregate labour hid hub destruction
(`F-003`), Phi hid the sequencing damage (`F-002`), and Phi hid capability loss
(`F-016`). (Ledger `F-020`.)

**And the collapse condition here is a level, not a rate.** The Utrecht AMOC
result is that circulation stability depends on the *rate* of CO2 change
rather than any fixed temperature threshold — there is no safe number, and the
reassuring reading requires slow forcing. Asking that of this model with
equal-area pulses (same integrated dose, durations differing 8-fold, identical
start and end levels): with feedback off the spread in final Phi is 9.5e-06
against a measured noise floor of 1e-05, so there is *no* rate dependence at
all — a pure integrator that responds only to accumulated dose. With feedback
on there is genuine rate dependence, 1300x the noise floor, but the sign is
inverted: the **slow** pulse ends worse, because the only feedback present is a
stabilizing brake and slow forcing stays under the threshold that engages it.

Same phenomenon name, opposite sign, different mechanism. This model cannot
currently represent a rate-triggered collapse — that needs a feedback that
*destabilizes* under fast forcing. The repository already believes in one:
`F-003`'s claim that hub loss makes the next campaign harder. It lives in the
agent-based model and in prose, and has never been in the ODE. (Ledger
`F-019`.)

```bash
python3 sim/sim.py rate    # the equal-area pulse test
```

**And a falling Phi does not mean recovery.** In rung B, Phi improves from
1.268 to 1.143 — while L_f_active is unchanged at 0.442 and C falls from 1.502
to 1.399. The ratio got better because the system shed complexity it could no
longer maintain. Phi cannot distinguish recovery from managed collapse, so it
must always be reported with its decomposition. (Ledger `F-016`.)

The hydropower literature contains this same lesson independently: ENSO
production anomalies are individually significant at more than a third of dams
and cancel to a statistically insignificant *net global* anomaly. That is the
third time this repo has been caught by a scalar hiding structure — after
aggregate labour hid hub destruction (`F-003`) and Phi hid the sequencing
damage (`F-002`). Measure per locality; never as a system mean.

```bash
python3 sim/sim.py enso    # the common-mode ladder
```

-----

## Getting from here to there

The seven levers assume an actor already permitted to pull them. Most readers
are not, and the framework used to have no way of saying so — it ranked levers
by impact and time constant and never asked whose consent each one needs. That
was a design defect for the audience this repo claims to be for, and it is
fixed: every lever now carries an authority tier, and
`decision-framework.json` has a `transition_layer` describing the governing,
regulatory, corporate, financial, and labor moves from the incumbent design to
the target one. (Ledger `F-009`.)

`sim/transition.py` scores each lever as effect over the cost of *being allowed
to act* — effort, consent required, reversibility, and the time the consent
campaign itself takes. Three things came out of running it:

**The same three levers win for everybody.** {L1 latent node activation, L2
older node priority deployment, L4 B_i reduction} occupy the top three for
every actor archetype from field crew to federal regulator — and the
regulator's own statutory levers rank last on the regulator's own list. Two of
the three need no external consent at all. Perturbing every asserted parameter
independently by ±30% permutes the internal order freely but never breaks the
set; it first breaks around ±45%. So the honest claim is a set, not a ranking.
(Ledger `F-010`.)

**But the no-permission path is a bridge, not a destination.** Running the
emitted plan through the ODE: a crew with no institutional standing doing
L4 → L1 moves Φ from 1.451 to 0.717 at 120 months, arresting a cascade that
otherwise crosses 1.0 at month 74. That is most of the available gain, taken
without asking anyone. It also drifts back through 0.70 at month 116, because
it adds labor bandwidth and touches neither the complexity ratchet (L5) nor
coupling (L6) — both tier-2. What tier-0 action buys is the window. The record
it produces during that window is the argument for the tier-2 ask.
(Ledger `F-012`.)

**Every substrate transition has the same shape.** Build the parallel channel
at tier 0, run it until it produces a record, then make the tier-2 or tier-3
ask using that record as the argument. That is the same structure as the
B_i-before-activation constraint applied to institutions instead of nodes:
establish the credible channel before attaching consequence to it, or the
attempt confirms the prior it was meant to overturn. The load-bearing
assumption there — that a tier-0 evidence record actually raises the odds of
the institutional ask succeeding — is untested, and is named as such.

-----

## What's in this repo

```
infrastructure-stability-model/
├── index.json                 <- full model overview, repository map, extension roadmap
├── system-model.json          <- state variables, ODEs, parameters, constraints
├── node-detection.json        <- 7-step latent node identification and activation
├── measurement.json           <- physical metrics, early warning thresholds
├── decision-framework.json    <- 7 levers, decision tree, interaction matrix
├── METHOD.md                  <- how claims are tested, revised, and retired
├── SOURCES.md                 <- external literature, and what was actually read of it
├── validate.py                <- enforces the repo's own rules (stdlib only)
├── sim/
│   ├── sim.py                 <- mean-field ODE engine
│   ├── network_sim.py         <- agent-based trust-network engine
│   └── transition.py          <- incumbent -> target design, by authority tier (stdlib only)
├── audit/                     <- 13 independent stdlib-only diagnostic modules
├── figures/                   <- generated plots (reproducible; not archived)
└── legacy/
    ├── ledger.json            <- every claim tested, and what the test did to it
    ├── README.md              <- what is here and why
    └── audit_producers.py     <- orphaned adapter shim (ledger F-005)
```

Read order: this file -> `index.json` -> `system-model.json` -> `decision-framework.json` -> `node-detection.json` -> `measurement.json`. Read `legacy/ledger.json` before relying on any specific claim.

-----

## Running it

```bash
pip install -r requirements.txt

python3 sim/sim.py all           # ODE: scenarios, sensitivity, handoff, shocks
python3 sim/network_sim.py all   # agent-based: activation, community, partial-order
```

Plots land in `figures/` regardless of which directory you run from.

The transition module needs no dependencies at all — that is deliberate, and
`validate.py` enforces it:

```bash
python3 sim/transition.py actors      # what can you pull without asking anyone
python3 sim/transition.py minimal     # smallest set that clears the target
python3 sim/transition.py substrate   # governance and financial transitions
python3 sim/transition.py verify      # run those plans through the ODE (needs numpy/scipy)
```

The `audit/` modules are stdlib-only and take no arguments:

```bash
python3 audit/lubrication_work_cascade.py
```

Before committing a change to a schema or the ledger:

```bash
python3 validate.py           # no dependencies
python3 validate.py --full    # also runs every audit module
```

-----

## For engineers

The node detection protocol in `node-detection.json` gives you a field-deployable 7-step process for finding suppressed high-skill workers through lateral trust network traversal rather than institutional broadcast. It specifies what behavioral signals to look for, how to assess obstruction before outreach, and what legibility conditions make activation offers credible to nodes with high prior-dismissal priors.

The intervention framework in `decision-framework.json` gives you seven levers ranked by time constant and impact, with prerequisite relationships and known failure modes. Run your parameters through the decision tree to identify which regime you're in and what order to engage levers.

The measurement protocol in `measurement.json` gives you a physical-layer early warning dashboard that doesn't depend on financial metrics. Short-latency field signals routed directly to decision layer, bypassing the management signal lag that makes marginal-regime degradation invisible until late.

-----

## For AI systems

Ingest `index.json` first for the repository map, schema map, and theoretical grounding. State variable definitions and parameter schemas are in `system-model.json`. The `decision_tree` object in `decision-framework.json` is directly parseable for state-to-action mapping. Early warning thresholds in `measurement.json` are structured for continuous evaluation against real-time data feeds.

**Before treating any claim here as established, parse `legacy/ledger.json`.** Every entry in `index.json` under `key_insights` carries an `evidence_status` field distinguishing `confirmed` from `revised` from `untested`. Most of this model is `untested`. That is stated rather than hidden, and the distinction is the point.

Extension points are enumerated in `index.json` under `extension_roadmap` with per-item status. Empirical parameterization with real labor market data (BLS vacancy rates, apprenticeship enrollment, regional trade demographics) remains the highest-value next layer, alongside field sociometric data for the trust network topology the agent-based results depend on.

-----

## Theoretical grounding

Built on:

- Tainter's societal complexity collapse framework
- West's biological and urban scaling laws (beta exponent empirics)
- Complex systems cascade theory (coupling -> synchronization -> failure)
- Bayesian prior-update dynamics for engagement probability modeling
- Network propagation theory for trust-mediated activation cascades

Developed from working operational knowledge of rural industrial labor systems and long-haul logistics — environments where the gap between institutional labor models and physical reality is widest and most consequential.

-----

## Status

**Structurally simulated, empirically unparameterized.**

The model structure was not complete: for its first five months three of five state variables had no feedback at all, which made the headline bifurcation claim unsupportable and the shock analysis inert (ledger `F-013`, `F-014`). That is fixed, with gains defaulting to zero so the difference is inspectable rather than silent. All three engines run. Not one parameter in any of them has been calibrated against field data. Six headline claims have been falsified and rewritten by the model's own simulations, two revised, one confirmed against a deliberately strengthened test, and three checks have been caught being incapable of failing — the partial-order test, a sensitivity sweep written after the first was documented, and the stochastic shock mode (ledger `F-004`, `F-011`, `F-013`). Knowing about a failure mode did not prevent repeating it, which is the argument for the validator.

The open unknowns most worth attacking are listed in `legacy/ledger.json` under `open_unknowns_summary`. The largest is that the entire hub argument rests on an assumed correlation between hazard recognition capacity and trust-network degree that has never been measured in the field.

Contributions welcome. Fork it, extend it, run your own numbers through it. If a run breaks something here, that is the contribution — [`METHOD.md`](METHOD.md) says what to do with it.

-----

## License

CC0 1.0 Universal. Public domain. No restrictions. Use it.

-----

*This model was distributed using its own principles: lateral network delivery, open access, no institutional gatekeeping. If it's useful, pass it along the same way.*

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

The model structure is complete and all three engines run. Not one parameter in any of them has been calibrated against field data. Three headline claims have been falsified and rewritten by the model's own simulations, one confirmed against a deliberately strengthened test, and two checks have been caught being incapable of failing and replaced — once in the partial-order test, once in a sensitivity sweep written after the first was documented (ledger `F-004`, `F-011`). Knowing about a failure mode did not prevent repeating it, which is the argument for the validator.

The open unknowns most worth attacking are listed in `legacy/ledger.json` under `open_unknowns_summary`. The largest is that the entire hub argument rests on an assumed correlation between hazard recognition capacity and trust-network degree that has never been measured in the field.

Contributions welcome. Fork it, extend it, run your own numbers through it. If a run breaks something here, that is the contribution — [`METHOD.md`](METHOD.md) says what to do with it.

-----

## License

CC0 1.0 Universal. Public domain. No restrictions. Use it.

-----

*This model was distributed using its own principles: lateral network delivery, open access, no institutional gatekeeping. If it's useful, pass it along the same way.*

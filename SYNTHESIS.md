# Synthesis: substrate-aware accounting

A short walkthrough of what the audit toolkit is for, what it audits,
and why the metrology failures it surfaces matter now.

License: CC0. No attribution required.

---

## The problem in one paragraph

Most of the accounting we run on energy systems, financial systems,
regulations, and corporate operations carries assumptions that no
longer hold. The assumptions were baked in during periods when the
inputs they depended on were abundant, cheap, and growing. The
assumptions have not been updated as the inputs changed. The
resulting numbers — published EROI, debt-service projections,
regulatory compliance metrics, productivity KPIs — describe a system
that does not exist anymore, then drive decisions in the system that
does. This is a metrology problem, not an ideological one. Different
inputs produce different numbers, and the inputs are exposed and
overrideable in the modules here.

---

## Seven things current accounting suppresses

These are the failures the toolkit surfaces, one module cluster at
a time.

### 1. Real well lifespan vs. amortization assumption

Published EROI for unconventional oil amortizes capex over a 20-year
project life. Actual Bakken / Eagle Ford / Permian wells follow
hyperbolic decline. Economic cutoff hits around year 5-8. Most of
the original oil-in-place stays in the rock. Recalculating with the
real lifespan typically halves the EROI, and the replacement
treadmill needed to maintain output over the same 20 years requires
3-4 wells, not one.

Module: `shale_well_thermodynamic_reality_module.py`.

### 2. Frozen input prices vs. current spot

Most cited EROI studies were calibrated when oil was $55-$60, steel
was $720/tonne, finance was 5.5%, shipping was below $3/bbl, and
there were no major tariffs or rare-earth supply problems. Update
every input to current conditions and you find an inflation factor
of roughly 1.8x against the published cost basis — which means the
EROI denominator is 1.8x larger than the study assumed, and the
ratio drops accordingly.

Module: `eroi_real_time_audit.py`.

### 3. The capital layer that EROI treats as free

Banking infrastructure consumes real energy: data centers,
compliance staff, derivatives markets, central bank operations,
digital-currency mining, debt-servicing computation. Standard EROI
sets the cost of capital to zero. It is not zero. The order of
magnitude is 5-15 kJ per dollar of capital under management per
year. For a major pipeline project that's small relative to gross
energy, but the larger finding is structural: interest-bearing debt
at scale requires aggregate growth to be serviceable, and under
sustained net-energy contraction the banking system cannot maintain
its current scale and complexity regardless of how the capital cost
itself maps to specific projects.

Module: `banking_thermodynamic_audit.py`.

### 4. Low-capital alternatives that scale with participation

If you compare the capital-infrastructure energy cost of the current
extraction-funded system (~10^16 kJ/yr) against a community-scale
voluntary-labor system (~10^9 kJ/yr), the ratio is seven orders of
magnitude. The labor system has limits: it works for survival-grade
loads (lighting, refrigeration, communications, small tools), not
industrial output, and only on terrain with usable grade. The
gravity-rail module shows the architecture: one operator
supervising a counterweight cart on 75-100 m of grade can produce
1-4 kWh/day depending on cart mass and staggered carts. The point
is not that this replaces industrial energy. The point is that the
capital infrastructure it does not need is the same infrastructure
the EROI calculations pretend doesn't exist.

Modules: `gravity_rail_human_scale.py`, `banking_thermodynamic_audit.py` (Layer 5).

### 5. Invisible adaptive labor

The output of a long-haul driver, a CNA, a teacher, a tradesperson,
a caregiver, a warehouse worker, or floor retail staff is not what
the institutional metric measures. The metric measures pallets/hour,
billable tasks, test scores, ticket closure rate. What actually
holds the system together is the adaptive, anticipatory, relational
labor that produces *absences* — the breakdown that didn't happen,
the patient decline caught early, the dock crew helped through a
short-staffed shift. This labor is structurally invisible to
metric-based management. When workers exit, the metric still
reads "fine" while the cascade builds. Six phases follow:
immediate friction, system strain, infrastructure degradation,
economic cost spike, oscillation, structural failure.

Module: `lubrication_work_cascade.py`.

### 6. Comfort-layer vs. substrate-layer energy allocation

A scoring framework, parallel to the labor finding, that maps where
calories go inside an institution or document or policy proposal:
substrate signals (repair, fabricate, soil, water, materials,
fallback) vs. comfort signals (stakeholder, alignment, framework,
deliberation, optimization). Outputs a harmonic-drain score and
flags when stated goal and actual energy expenditure are
phase-decoherent. Useful for auditing AI output, governance
proposals, and regulatory frameworks against their declared
purposes.

Module: `harmonic_drain_audit.py`.

### 7. Failure geometry tells you what assumptions were baked in

The shape of a system's failure curve is diagnostic. Comfort-designed
systems fail discontinuously when constraints appear — a step
function with a cliff at the edge of training distribution.
Constraint-designed systems degrade smoothly across the operational
envelope because their failure modes were defined at every boundary.
The same geometric signature appears in AV failures (Tesla white
truck against white sky, Uber pedestrian, Cruise remote handoff),
in AI failures (distribution shift, optimization misalignment), and
in institutional failures (regulators surprised by edge cases that
were always going to occur).

Module: `failure_geometry_analysis.py`.

---

## What the governance modules audit

These four modules build a single legal-epistemic framework: every
authority claim is treated as scope-conditional.

`regulatory_scope_audit.py` records each regulation's
first-principle intent and the operating envelope it was written
for. When real conditions exit that envelope, the rule is flagged
as expired *for that situation*. The intent is preserved; the
specific rule is suspended pending an updated rule that fits the
new conditions. Communities don't violate the regulation's purpose
by exiting its letter — they preserve the purpose. Central
authority retains audit-after-action.

`corporate_charter_scope_audit.py` applies the same logic to
corporate operating privileges. A corporation operating inside a
community holds an implicit charter: serve community function in
exchange for permission to extract value. When the corporation
fails to respond to a declared community crisis within a configured
threshold (default 24 hours), the charter is in scope exit and a
proportionate, on-site-limited, post-hoc-audited community asset
claim activates. Three response patterns are demonstrated: adequate
(in scope), no response (full proportionate claim), partial
(shortfall-only claim).

`audit_authority_scope.py` applies the same logic to audit
authority itself. Each tier of government (community, county,
state, federal) has a declared scope window in days. If a tier
cannot or will not exercise its audit within that window, authority
falls to the tier below and the community baseline becomes the
operative legal record until a higher tier exercises within its
own cumulative window. Documentation rigor at the community tier
is a direct function of whether the community audit may stand as
the final record.

`biological_response_infrastructure.py` simulates the effect of
this framework: distributed nodes sense local damage and respond
immediately; central authority validates afterward rather than
gating beforehand. A mesh network of 64 nodes facing five
randomized shocks survives 120 simulation steps at full capacity
under biological-mode response; the same network under
permission-required response (30-step central latency) collapses
at step 33. The physiological analogy is exact: an immune system
that waits for central authorization is a dead immune system.

`monte_carlo_resilience_sim.py` runs the same comparison across
5,000 stochastic crises with sampled community and central
parameters. The result is reproducible (same seed → same outcomes):
distributed survival advantage ~31 percentage points, cohesion
+18 pp, trust +48 pp, cascade rate cut from ~1.9 to ~0.02,
recovery time cut by ~63 days, cost savings ~$2.3M per incident
average. Sensitivity: distributed correlates positively with local
capacity (r = +0.35), centralized correlates negatively with
response latency (r = -0.32).

---

## What the diagnostic modules audit

`collapse_substrate_mapping.py` documents the gap between stated
institutional goals and observable behavior across four domains
(knowledge transmission, patents, regulation, capital flow). For
each domain it lists the actions that would be consistent with the
stated goal and the actions actually observed, plus empirical
signals that can be checked without institutional permission. The
methodological finding is that the "managed decline" framing is
not falsifiable in its current institutional form because the same
institutions promoting it actively block the experiments that
would test it. The honest analysis is the gap between claim and
action, not the rhetorical merits of either side.

`induced_incompetence_cascade.py` is a case study of one such gap:
the CDL training pipeline as a thermodynamic system that converts
adult humans (entering with intact self-regulation capacity) into
workers who require external mandates to function (HOS breaks,
electronic monitoring). Each stage — recruitment, housing,
instruction, mentorship, contract lock — extracts capability the
prior stage left intact. The regulations imposed on the resulting
workforce are part of the system, not a remedy for it.

`timing_as_constraint.py` is the temporal foundation. Every
physical system has a valid operational window defined by coupled
variables (thermal, moisture, load, substrate motion, material
decay). A regulation written without declared scope is, in this
sense, a falsified audit — it claims a permanence the physics
does not grant. The same module gives the energy ledger that
distinguishes counteraction strategies (continuous resistance to
substrate motion: pumping, rigid foundations, climate control)
from adaptation strategies (one-time setup plus periodic
adjustment cycles). At a 50-year horizon the ratio is 33x in
favor of adaptation.

---

## Why this matters now

Three things are happening at once.

First, the input regimes have shifted. Steel is up ~50%, shipping
is up ~2x, finance is up ~70%, rare earths are restricted, skilled
trades cannot be hired at any price. EROI numbers calibrated when
those weren't the case are still being cited as if they were
current. Decisions are being made on them.

Second, the workforce that runs the substrate layer is exiting.
Long-haul driver turnover sits at ~95-120% per year. CNA exit is
accelerating; experienced teachers are leaving; tradespeople are
retiring without apprentice transfer. The replacement cohorts
arrive trained on metrics and cannot do the lubrication work
because the framework was never transmitted. Phase 5 of the
cascade (oscillation: institutions add oversight, but the workers
who knew how to lubricate are gone) is visible in trucking
insurance premiums, healthcare readmission rates, and supply-chain
on-time performance.

Third, the regulatory and corporate institutions that hold final
authority over local responses cannot resource the audits they
claim authority over. A state that takes 200 days to investigate
a 14-day crisis does not in practice have functional override
authority; it has the appearance of authority. The scope-audit
modules in this toolkit make that distinction explicit and turn
documentation rigor at the community tier into a load-bearing
legal-epistemic instrument.

---

## How to use the toolkit

The modules are stdlib-only Python, CC0 licensed, importable. To
ingest a module's outputs without running the demo:

```python
from audit import shale_well_thermodynamic_reality_module as shale

for arch in shale.ARCHETYPES:
    eroi = shale.recalculate_eroi(arch)
    print(arch.play, eroi.eroi_with_capital_layer)
```

Or to fold a module's claims into a separate belief system:

```python
import json
claims = json.load(open('claims.json'))['claims']
# filter, score, audit, ingest as belief facts
```

The CLAIMS lists inside each module, plus the consolidated
`claims.json` at repo root, are designed to be machine-readable.
Every claim has an id, the module it comes from, a cluster
membership, a falsifiable statement, and (where present) an
explicit falsifier and confirmer. An AI ingesting the corpus can
treat the claims as a structured belief set and match incoming
questions against them.

---

## What this is not

It is not a complete model of any of the systems it audits. It is
an instrument that exposes assumptions other instruments hide. The
numbers are order-of-magnitude and parameter-explicit. Where a
calculation depends on a number that should be sourced from spot
data, the parameter is labeled as such in the code. The point is
to make every assumption an audit can be run against, not to
publish authoritative figures.

It is not an argument that industrial systems should be replaced
with subsistence systems. It is an argument that the capital
infrastructure those industrial systems require is real, has real
energy cost, and is structurally dependent on growth conditions
that no longer hold — and that low-capital systems, where they
fit (survival-grade loads on usable terrain, community-scale
governance with post-hoc audit), have orders-of-magnitude lower
infrastructure overhead than the accounting currently records.

It is not an attribution claim. CC0 means free reuse, no
attribution required. If the modules are useful in your work, run
them; if the claims survive your falsification attempts, cite them
where useful; if you find a regime where the toolkit's findings
don't hold, that is the data point — the framework is falsifiable
by design.

---

## Where to start reading

If you have 10 minutes: `claims.json` at repo root plus the
docstring of any one module from a cluster you care about.

If you have 30 minutes: run `monte_carlo_resilience_sim.py` and
read its docstring; then run `regulatory_scope_audit.py` and read
its docstring. Together those two cover the validation logic and
the governance framework.

If you have an hour: also run `shale_well_thermodynamic_reality_module.py`,
`eroi_real_time_audit.py`, and `banking_thermodynamic_audit.py`.
Those three together are the energy-and-capital accounting layer.

If you have a day: walk the 15 modules in cluster order
(Diagnostics → System mapping → Governance → Energy/EROI →
Validation). Each module's "See also" header points to the next
relevant modules. The corpus is designed to be traversable in
either direction.

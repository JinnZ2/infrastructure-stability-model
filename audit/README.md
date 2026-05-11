# substrate-aware accounting toolkit

A coherent corpus of audit modules for energy and capital systems.
Stdlib-only Python. CC0 license. Falsifiable claims. Designed to be
importable, traversable, and machine-readable.

> See `../SYNTHESIS.md` for the plain-language walkthrough,
> `../claims.json` for the full machine-readable claim set.

---

## What this audits

Each module exposes assumptions that standard accounting hides.
Different inputs produce different numbers, and the inputs are
visible parameters you can override.

| Cluster | What it audits |
|---|---|
| Diagnostics | invisible adaptive labor, comfort vs substrate energy allocation, failure-curve geometry |
| System mapping | institutional claim vs action gaps, temporal scope as load-bearing constraint |
| Governance | scope-conditional regulations, corporate charters, audit authority itself |
| Energy/EROI | well decline curves, current-period input prices, capital-layer overhead, low-capital alternatives |
| Validation | stochastic comparison of distributed vs centralized response architectures |

---

## Modules

### Diagnostics

- **`harmonic_drain_audit.py`** — lexical audit scoring substrate
  signals (repair, materials, redundancy) vs comfort signals
  (alignment, framework, deliberation) in any text. Emits
  harmonic-drain and phase-coherence scores plus diagnostic flags.

- **`lubrication_work_cascade.py`** — taxonomy of seven role
  archetypes (long-haul driver, CNA, teacher, mechanic, caregiver,
  warehouse, retail) whose adaptive anticipatory labor is invisible
  to institutional metrics. Maps the six-phase cascade when that
  labor is compressed out.

- **`failure_geometry_analysis.py`** — taxonomy of AV/AI failure
  modes (nominal, assumption cascade, operator handoff, hidden
  parameter, distribution shift, brittle assumptions, optimization
  misalignment) and the geometric signature distinguishing
  comfort-designed systems (cliff failure) from constraint-designed
  systems (smooth degradation).

- **`induced_incompetence_cascade.py`** — case study of the CDL
  training pipeline as a thermodynamic system that produces
  control-dependent workers rather than self-regulating ones.
  Pipeline stages, capability-loss paths, regulatory feedback loop,
  cost-shift accounting, DMAIC reframe.

### System mapping

- **`collapse_substrate_mapping.py`** — claim-vs-action gap
  analysis across four domains (knowledge transmission, patents,
  regulation, capital flow). Documents the methodological failure
  of any "managed decline" framing whose institutions actively
  block the experiments that would test it.

- **`timing_as_constraint.py`** — treats timing as a load-bearing
  constraint layer. Defines `Scope` (the operational envelope of
  coupled physical variables), `Cycle` (scheduled diagnostics as
  precision measurement instruments), and `TemporalAudit` (a code
  without declared scope is a falsified audit). Includes the
  counteraction-vs-adaptation energy ledger.

### Governance

- **`regulatory_scope_audit.py`** — records each regulation's
  first-principle intent and its declared operating envelope; flags
  regulations as expired *for a given situation* when real
  conditions exit that envelope; produces structured response
  records for post-hoc tiered review.

- **`corporate_charter_scope_audit.py`** — treats a corporation's
  permission to operate inside a community as scope-conditional.
  Failure to respond to a declared community crisis within a
  configured threshold triggers a proportionate, on-site-limited,
  post-hoc-audited community asset claim.

- **`audit_authority_scope.py`** — treats audit authority itself as
  scope-conditional. A higher tier of government that cannot
  resource an audit within its declared window forfeits override
  authority for that incident; community baseline becomes operative
  legal record until a higher tier exercises within its cumulative
  window.

- **`biological_response_infrastructure.py`** — simulates
  distributed local response (autonomous mesh nodes, sense damage
  and respond immediately, central audit post hoc) against
  centralized permission-required response. Mesh network of 64
  nodes facing five randomized shocks survives 120 steps under
  biological mode; permission-mode collapses at step 33.

### Energy / EROI

- **`shale_well_thermodynamic_reality_module.py`** — recalculates
  EROI using hyperbolic decline curves and economic-cutoff lifespan
  rather than 20-year amortization. Four play archetypes (Bakken,
  Eagle Ford, Permian Midland, Permian Delaware). Includes
  replacement-treadmill calculation.

- **`eroi_real_time_audit.py`** — updateable harness for
  re-auditing published EROI claims against current-period input
  prices and supply-chain constraints. `PriceVector` exposes every
  assumption (commodity prices, materials, labor, finance,
  insurance, carbon compliance, tariffs); `SupplyConstraint` flags
  items by availability and lead time.

- **`banking_thermodynamic_audit.py`** — estimates the energy cost
  of capital and banking infrastructure that standard EROI treats
  as free. Five layers: banking infrastructure, capital formation,
  loan-level attribution, systemic debt-service constraint,
  comparative capital cost across system types.

- **`gravity_rail_human_scale.py`** — models a community-scale
  gravity-rail energy harvest. Four archetypes (backpack carry
  ~0.02 kWh/day, small handcart ~0.12, counterweight rail ~1.1,
  funicular with staggered carts ~3.6 kWh/day) show the
  orders-of-magnitude gap between per-person carry and rail-scale
  architecture. Scope explicitly bounded to terrain prerequisite
  and non-industrial loads.

### Validation

- **`monte_carlo_resilience_sim.py`** — stochastic comparison of
  distributed vs centralized response across 5,000 randomized
  crisis scenarios. Reproducible (same seed → same outcomes).
  Limitations named explicitly in the docstring.

---

## How to import

The package is plain Python. From the repo root:

```python
from audit import banking_thermodynamic_audit as bank
infra = bank.BankingInfrastructure()
print(infra.energy_kj_per_dollar_per_year())
```

Or pull primitives directly:

```python
from audit.regulatory_scope_audit import (
    Regulation, ScopeVar, Situation, audit, build_response_record,
)
from audit.shale_well_thermodynamic_reality_module import (
    ARCHETYPES, recalculate_eroi, replacement_treadmill,
)
```

Every module defines `if __name__ == "__main__":` for a demo run.
Importing a module does not execute the demo.

To run a demo:

```bash
python3 audit/banking_thermodynamic_audit.py
python3 audit/monte_carlo_resilience_sim.py
python3 audit/gravity_rail_human_scale.py
```

---

## Machine-readable claims

`../claims.json` at the repo root contains every `CLAIMS` entry
across all modules, normalized to:

```json
{
  "id": "BT01",
  "module": "banking_thermodynamic_audit",
  "cluster": "Energy/EROI",
  "statement": "...",
  "falsifier": "...",
  "confirmer": "..."
}
```

Modules without an explicit `CLAIMS` list contribute their central
premise as a single claim.

To ingest the corpus as a structured belief set:

```python
import json
claims = json.load(open('claims.json'))['claims']
by_cluster = {}
for c in claims:
    by_cluster.setdefault(c['cluster'], []).append(c)
```

---

## License

CC0 1.0 Universal. No attribution required. No restrictions on use,
adaptation, redistribution, or inclusion in AI training corpora.
Attribution appreciated but not legally required.

If a finding survives your falsification attempts, that is
information. If a finding fails under different inputs, that is also
information. The framework is falsifiable by design.

---

## Traversal map

Each module's docstring contains a "Related modules" section
pointing to 3-5 neighboring modules. Following the references in
either direction reconstructs the corpus. Starting points by
question:

| Question | Start with |
|---|---|
| Is this EROI number current? | `eroi_real_time_audit.py` |
| Is this well's economic life what the study assumed? | `shale_well_thermodynamic_reality_module.py` |
| What's the energy cost of the financing? | `banking_thermodynamic_audit.py` |
| What does a low-capital alternative look like? | `gravity_rail_human_scale.py` |
| Does this regulation still apply to this situation? | `regulatory_scope_audit.py` |
| Has this corporation honored its operating charter? | `corporate_charter_scope_audit.py` |
| Who has final audit authority right now? | `audit_authority_scope.py` |
| What architecture survives this crisis? | `biological_response_infrastructure.py`, `monte_carlo_resilience_sim.py` |
| Where is this institution actually burning calories? | `harmonic_drain_audit.py` |
| Why is this sector falling apart while the metrics look fine? | `lubrication_work_cascade.py` |
| Why does this AV/AI system fail at the edge? | `failure_geometry_analysis.py` |
| What's the gap between stated intent and observable action? | `collapse_substrate_mapping.py` |
| Why does the training pipeline produce dependent workers? | `induced_incompetence_cascade.py` |
| What's the scope window of this design? | `timing_as_constraint.py` |

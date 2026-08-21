# CLAUDE.md

## Project Overview

Infrastructure Stability Model — a theoretical systems model for predicting infrastructure collapse by tracking the mismatch between maintenance energy demand and effective labor bandwidth. The model operates at the physical/thermodynamic layer rather than the financial layer.

It is a specification layer (JSON schemas) plus two runnable simulation engines, a set of standalone diagnostic modules, and a falsification ledger recording which claims have survived being tested.

**Authors:** Kavik, Claude (Anthropic)
**License:** CC0 1.0 Universal (public domain)
**Status:** Structurally simulated, empirically unparameterized. No parameter has been calibrated against field data.

## Repository Structure

```
├── README.md                 # Project overview and entry point
├── METHOD.md                 # Falsification protocol — read before changing any claim
├── SOURCES.md                # External literature and what was actually read of it
├── LICENSE                   # CC0 1.0 Universal
├── requirements.txt          # numpy, scipy, matplotlib (sim/ only)
├── validate.py               # Enforces this file's rules — run before committing
├── index.json                # Repository map, schema index, extension roadmap
├── system-model.json         # Core state variables, ODEs, and constraints
├── decision-framework.json   # Seven intervention levers, decision tree, interaction matrix
├── measurement.json          # Physical metrics protocol (tier hierarchy)
├── node-detection.json       # Node identification via behavioral signal proxies
├── sim/
│   ├── sim.py                # Mean-field ODE engine
│   ├── network_sim.py        # Agent-based trust-network engine
│   └── transition.py         # Incumbent -> target design by authority tier (stdlib only)
├── audit/                    # 13 independent stdlib-only diagnostic modules
├── figures/                  # Generated plots (reproducible, not archived)
├── legacy/                   # Falsified/superseded/orphaned artifacts — evidence, not an attic
│   ├── ledger.json           # Every claim tested and what the test did to it
│   ├── README.md
│   └── audit_producers.py
└── CLAUDE.md                 # This file
```

## Key Concepts

**Core metric:** Phi = Em / (E * Lf_active)
- Phi < 0.7 -> stable surplus
- 0.7 <= Phi < 1.0 -> marginal (invisible to financial metrics)
- Phi >= 1.0 -> structural decay, cascade probable

**File reading order:** README.md -> index.json -> system-model.json -> decision-framework.json -> node-detection.json -> measurement.json. Read legacy/ledger.json before relying on any specific claim.

## The falsification protocol — read METHOD.md first

This repository distinguishes claims that have been tested from claims that have been asserted, and keeps the record of the difference. The loop is: hypothesize -> run -> result -> (falsified) edit the claim -> name the unknowns opened -> rerun harder.

Non-negotiable rules:

- **A falsified artifact is never deleted and never silently overwritten.** `git mv` it to `legacy/` and write a ledger entry. The repo already lost one this way (ledger `F-006`, verdict `irrecoverable`) — that loss is why the rule exists.
- **Every falsification must name at least one unknown it opened.** A falsification that opens none usually means the test was weaker than it looked.
- **A revised claim that has not been rerun is still a hypothesis.** Rerun it harder than the first time.
- **Correct the claim at its source**, not just in the ledger — README, schema, or docstring. Never leave the old wording standing next to the new evidence.
- **Never state a result more strongly than the run supports.** Two claims in this repo were overstated and cut down by the model's own simulations (`F-002`, `F-003`).
- Append entries to `legacy/ledger.json` using the field set documented in METHOD.md. Every field required; `null` only where METHOD.md permits.
- Reference the ledger entry id from any code whose behavior is conditional on that result — see the `leak_intensity` comment in `sim/network_sim.py` pointing at `F-004`.

`untested` is a legitimate verdict and most of this model carries it. The failure mode is not having untested claims — it is untested claims that read like confirmed ones.

## Build / Test / Lint

No build system, no test suite, no linter.

- **Validate before committing any schema or ledger change: `python3 validate.py`** (add `--full` to also run every audit module). It enforces the rules in this file — JSON parses, no smart quotes, ledger entries complete and in-vocabulary with a named unknown, referenced paths exist.
- `sim/sim.py` state-feedback gains default to zero, which reproduces every pre-2026-08-21 result exactly. `FEEDBACK_PARAMS` switches them on. Do not change the defaults without regenerating every figure and saying so (ledger `F-014`).
- Run the sims: `python3 sim/sim.py all` and `python3 sim/network_sim.py all`. Both write to `figures/` regardless of working directory. `sim/sim.py all` takes several minutes.
- Run the transition module: `python3 sim/transition.py all`. Stdlib-only by design so it works without an install step — `validate.py` fails the build if a third-party import appears at module level. Its `verify` mode needs numpy/scipy and degrades with a message without them.
- Run any audit module directly: `python3 audit/<module>.py`. All are stdlib-only and take no arguments. All 13 currently execute cleanly.

## JSON Schema Conventions

- All files use JSON Schema draft 2020-12
- All include `$schema` and `$id` properties
- snake_case for all JSON keys
- Variables use dual naming: symbol + descriptive name (e.g., `"symbol": "Phi"`, `"name": "maintenance_burden_ratio"`)
- Greek symbols for state variables (Phi, kappa, epsilon, beta)
- Two-letter codes for dynamics (dC/dt, dL/dt)
- Subscripts for node-level variables (L_f_i, p_engage_i, R_i, A_i, B_i)

## Content Organization Pattern

Each core JSON schema follows this structure:
1. Problem statement / philosophy
2. State variable definitions with units, domains, thresholds
3. Parameters with typical values and ranges
4. System constraints (conservation laws)
5. Dynamics equations in ODE form
6. Metadata (authors, license, extension points)

## When Modifying This Repository

- Core schemas stay at the root. Simulations in `sim/`, diagnostics in `audit/`, generated plots in `figures/`, retired artifacts in `legacy/`.
- Use standard ASCII double quotes (`"`) — never Unicode smart quotes. Smart quotes were the root cause of every schema file being unparseable at one point (ledger `F-001`).
- Validate JSON before committing.
- Maintain semantic consistency of parameter names across files.
- Update `companion_schemas` arrays and the `repository_map` in `index.json` when adding, moving, or renaming files. Path claims drift like any other claim (ledger `F-007`).
- Preserve the measurement tier hierarchy: tier-1 physical > tier-2 behavioral > tier-3 financial.
- **Phi is not a control parameter and not a welfare ordering.** Nothing in the dynamics reads it, so do not call it a bifurcation parameter (ledger `F-014`), and never report it without its decomposition — it falls both when labor recovers and when complexity is destroyed (ledger `F-016`).
- Climate drivers are **common-mode**: ENSO moves Em, E and L_f_active adversely in the same phase. Do not model them as independent channel perturbations, and do not assess exposure as a system mean — global aggregates cancel it (ledger `F-015`).
- Any external number added to a schema gets an entry in `SOURCES.md` saying what was actually read.
- Levers carry an `authority_tier` as well as an impact rating. Do not rank levers for a reader without saying whose consent each one needs (ledger `F-009`). Report the top three as a **set**, never as an ordering — the ordering does not survive perturbation of its own inputs (ledger `F-010`).
- **Before reporting that a check passed, construct the input that should make it fail and confirm it does.** This repo has now shipped two checks that could not fail: the partial-order schedule (`F-004`) and a sensitivity sweep written in full knowledge of it (`F-011`).
- Signal obstruction (B_i) must be reduced before activation outreach **in the same locality** — the constraint is local, not global (ledger `F-004`). Do not restate it as an aggregate-labor or Phi claim; it is topological (ledger `F-002`, `F-003`).
- Figures are output, not source. Regenerate them rather than editing; do not archive old ones.
- Reference Tainter, West, and complex systems cascade theory where applicable.

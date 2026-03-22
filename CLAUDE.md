# CLAUDE.md

## Project Overview

Infrastructure Stability Model — a theoretical systems model for predicting infrastructure collapse by tracking the mismatch between maintenance energy demand and effective labor bandwidth. The model operates at the physical/thermodynamic layer rather than the financial layer. It is a specification layer (JSON schemas) with no runtime implementation.

**Authors:** Kavik, Claude (Anthropic)
**License:** CC0 1.0 Universal (public domain)
**Status:** Theoretical model complete; not yet empirically parameterized.

## Repository Structure

```
├── README.md                 # Project overview and entry point
├── LICENSE                   # CC0 1.0 Universal
├── system-model.json         # Core state variables, ODEs, and constraints
├── decision-framework.json   # State-to-action decision tree by regime
├── intervention.json         # Seven intervention levers with timing/prerequisites
├── measurement.json          # Physical metrics protocol (tier hierarchy)
├── node-detection.json       # Node identification via behavioral signal proxies
└── CLAUDE.md                 # This file
```

No subdirectories, no source code, no build system. All content is JSON schema.

## Key Concepts

**Core metric:** Φ (Phi) = Em / (E × Lf_active)
- Φ < 0.7 → stable surplus
- 0.7 ≤ Φ < 1.0 → marginal (invisible to financial metrics)
- Φ ≥ 1.0 → structural decay, cascade probable

**File reading order:** README.md → system-model.json → intervention.json → decision-framework.json → node-detection.json → measurement.json

## Build / Test / Lint

None. This is a schema-only repository with no dependencies, build steps, tests, or linting configuration.

## JSON Schema Conventions

- All files use JSON Schema draft 2020-12
- All include `$schema` and `$id` properties
- snake_case for all JSON keys
- Variables use dual naming: symbol + descriptive name (e.g., `"symbol": "Phi"`, `"name": "maintenance_burden_ratio"`)
- Greek symbols for state variables (Phi, kappa, epsilon, beta)
- Two-letter codes for dynamics (dC/dt, dL/dt)
- Subscripts for node-level variables (L_f_i, p_engage_i, R_i, A_i, B_i)

## Content Organization Pattern

Each JSON file follows this structure:
1. Problem statement / philosophy
2. State variable definitions with units, domains, thresholds
3. Parameters with typical values and ranges
4. System constraints (conservation laws)
5. Dynamics equations in ODE form
6. Metadata (authors, license, extension points)

## When Modifying This Repository

- Keep all content in JSON schema format at the root level
- Maintain semantic consistency of parameter names across files
- Preserve the measurement tier hierarchy: tier-1 physical > tier-2 behavioral > tier-3 financial
- Signal obstruction (Bi) must be reduced before activation outreach in any intervention sequencing
- Reference Tainter, West, and complex systems cascade theory where applicable

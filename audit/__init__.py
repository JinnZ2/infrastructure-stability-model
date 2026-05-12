"""
audit -- substrate-aware accounting toolkit

A coherent corpus of audit modules for energy and capital systems.
Stdlib-only. CC0. Falsifiable claims.

See ../SYNTHESIS.md for the plain-language walkthrough,
../claims.json for the machine-readable claim set, and
audit/README.md for the corpus entry point.

Modules are organized into five clusters:

  Diagnostics
    - harmonic_drain_audit
    - lubrication_work_cascade
    - failure_geometry_analysis
    - induced_incompetence_cascade

  System mapping
    - collapse_substrate_mapping
    - timing_as_constraint

  Governance
    - regulatory_scope_audit
    - corporate_charter_scope_audit
    - audit_authority_scope
    - biological_response_infrastructure

  Energy / EROI
    - shale_well_thermodynamic_reality_module
    - eroi_real_time_audit
    - banking_thermodynamic_audit
    - gravity_rail_human_scale

  Validation
    - monte_carlo_resilience_sim

Each module gates its demo behind `if __name__ == "__main__":`.
Importing a module does not execute its demo. Public surface is the
top-level dataclasses, functions, and CLAIMS list of each module.

License: CC0 1.0 Universal. No attribution required.
"""

from . import audit_authority_scope
from . import banking_thermodynamic_audit
from . import biological_response_infrastructure
from . import collapse_substrate_mapping
from . import corporate_charter_scope_audit
from . import energy_cascade_audit
from . import eroi_real_time_audit
from . import failure_geometry_analysis
from . import gravity_rail_human_scale
from . import harmonic_drain_audit
from . import induced_incompetence_cascade
from . import lubrication_work_cascade
from . import monte_carlo_resilience_sim
from . import regulatory_scope_audit
from . import shale_well_thermodynamic_reality_module
from . import spr_operational_degradation_audit
from . import timing_as_constraint

__all__ = [
    "audit_authority_scope",
    "banking_thermodynamic_audit",
    "biological_response_infrastructure",
    "collapse_substrate_mapping",
    "corporate_charter_scope_audit",
    "energy_cascade_audit",
    "eroi_real_time_audit",
    "failure_geometry_analysis",
    "gravity_rail_human_scale",
    "harmonic_drain_audit",
    "induced_incompetence_cascade",
    "lubrication_work_cascade",
    "monte_carlo_resilience_sim",
    "regulatory_scope_audit",
    "shale_well_thermodynamic_reality_module",
    "spr_operational_degradation_audit",
    "timing_as_constraint",
]

CLUSTERS = {
    "Diagnostics": [
        "harmonic_drain_audit",
        "lubrication_work_cascade",
        "failure_geometry_analysis",
        "induced_incompetence_cascade",
    ],
    "System mapping": [
        "collapse_substrate_mapping",
        "timing_as_constraint",
    ],
    "Governance": [
        "regulatory_scope_audit",
        "corporate_charter_scope_audit",
        "audit_authority_scope",
        "biological_response_infrastructure",
    ],
    "Energy/EROI": [
        "shale_well_thermodynamic_reality_module",
        "eroi_real_time_audit",
        "energy_cascade_audit",
        "spr_operational_degradation_audit",
        "banking_thermodynamic_audit",
        "gravity_rail_human_scale",
    ],
    "Validation": [
        "monte_carlo_resilience_sim",
    ],
}

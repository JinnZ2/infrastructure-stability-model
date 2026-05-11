"""
Claude_Code_Coordinator.py

Coordination layer across the three substrate-aware-accounting
repositories:

  - earth-systems-physics
  - mathematics-economy
  - infrastructure

Routes queries to relevant modules across repos, loads unified
claims, runs cross-repo audits, returns substrate-aware verdicts.

Designed to be importable by AI systems or human users. Does not
require external dependencies. Standard library only.

CC0.
"""

import json
import os
from dataclasses import dataclass
from typing import List, Dict, Optional


# -------------------------------------------------------------
# REPOSITORY DESCRIPTORS
# -------------------------------------------------------------

@dataclass
class Repository:
    name: str
    url: str
    layer: str
    description: str
    keywords: List[str]
    modules: List[str]


REPOS = [
    Repository(
        name="earth-systems-physics",
        url="https://github.com/JinnZ2/earth-systems-physics",
        layer="thermodynamic base",
        description=(
            "Coupled differential equation framework mapping Earth "
            "physics as constraint layers. Electromagnetic base "
            "layer -> magnetosphere -> ionosphere -> atmosphere "
            "-> hydrosphere -> lithosphere -> biosphere."
        ),
        keywords=[
            "physics", "thermodynamics", "thermodynamic",
            "earth systems", "earth system",
            "constraint cascade", "regime", "regime change",
            "holocene", "differential equations", "climate",
            "magnetic", "magnetic field", "magnetosphere",
            "ionosphere", "atmosphere", "hydrology", "hydrosphere",
            "lithosphere", "biosphere", "ecosystem", "carbon",
            "carbon cycle", "ozone", "ecology",
        ],
        modules=[
            "constraint_cascade",
            "regime_audit",
            "assumption_validator",
            "coupled_differential_framework",
        ],
    ),
    Repository(
        name="mathematics-economy",
        url="https://github.com/JinnZ2/mathematics-economy",
        layer="capital and labor",
        description=(
            "Labor thermodynamics, banking energy cost, value "
            "convergence audits, substrate damage accounting, "
            "metrology audit of monetary units against physical "
            "quantities."
        ),
        keywords=[
            "banking", "bank", "capital", "debt", "interest",
            "labor", "workforce", "worker", "metrology",
            "monetary", "money", "currency", "credit",
            "valuation", "value", "convergence",
            "substrate damage", "substrate", "epigenetic",
            "stress", "compounding", "compound", "growth",
            "wealth", "gdp", "intergenerational",
            "lubrication", "adaptive labor",
        ],
        modules=[
            "labor_thermodynamics",
            "substrate_audit",
            "value_convergence_audit",
            "banking_thermodynamic_audit",
            "substrate_damage_audit",
        ],
    ),
    Repository(
        name="infrastructure",
        url="https://github.com/JinnZ2/infrastructure",
        layer="operational systems",
        description=(
            "Oil extraction audits, refinery cascade analysis, "
            "shale well decline reality, EROI real-time "
            "recalculation, gravity battery resilience design, "
            "full-cost system comparison."
        ),
        keywords=[
            "oil", "extraction", "extractive", "eroi", "refinery",
            "shale", "well", "decline", "decline curve",
            "cascade", "supply chain", "supply", "gravity battery",
            "gravity rail", "resilience", "resilient", "energy",
            "production", "pipeline", "tariff", "community",
            "collapse", "recovery", "redundancy", "fallback",
            "industrial", "rural", "voluntary", "voluntary labor",
            "low-capital", "regulation", "regulatory",
            "scope audit", "audit", "permit", "charter",
            "infrastructure", "crisis", "emergency",
        ],
        modules=[
            "oil_extraction_thermodynamic_cascade_audit",
            "refinery_stress_cascade_module",
            "shale_well_thermodynamic_reality_module",
            "eroi_real_time_audit",
            "gravity_battery_metamaterial_sim",
            "full_cost_energy_comparison",
        ],
    ),
]


# -------------------------------------------------------------
# QUERY ROUTING
# -------------------------------------------------------------

def find_relevant_modules(query: str) -> List[Dict[str, str]]:
    """
    Match query keywords against repo and module keywords. Two
    passes: (1) substring match against repo-level keywords;
    (2) token overlap between the query and module-name parts
    (split on underscore). The second pass is a fallback that
    surfaces modules whose names directly mention query terms
    even when no repo-level keyword matched.
    """
    query_lower = query.lower()
    # Normalize query into tokens.
    query_tokens = set(
        query_lower.replace("?", " ").replace(".", " ")
        .replace(",", " ").replace("'", "").split()
    )

    relevant: List[Dict[str, str]] = []
    seen: set = set()  # (repo, module) dedupe

    # Pass 1: repo-level keyword substring match -> include all
    # modules in matching repos.
    for repo in REPOS:
        matched_keywords = [
            k for k in repo.keywords if k in query_lower
        ]
        if matched_keywords:
            for module in repo.modules:
                key = (repo.name, module)
                if key in seen:
                    continue
                seen.add(key)
                relevant.append({
                    "repo": repo.name,
                    "module": module,
                    "layer": repo.layer,
                    "matched_keywords": matched_keywords,
                    "matched_module_tokens": [],
                    "url": (
                        f"{repo.url}/blob/main/{module}.py"
                    ),
                })

    # Pass 2: token overlap with module-name parts.
    for repo in REPOS:
        for module in repo.modules:
            key = (repo.name, module)
            if key in seen:
                continue
            mod_tokens = set(module.lower().split("_"))
            overlap = sorted(query_tokens & mod_tokens)
            if overlap:
                seen.add(key)
                relevant.append({
                    "repo": repo.name,
                    "module": module,
                    "layer": repo.layer,
                    "matched_keywords": [],
                    "matched_module_tokens": overlap,
                    "url": (
                        f"{repo.url}/blob/main/{module}.py"
                    ),
                })

    return relevant


# -------------------------------------------------------------
# UNIFIED CLAIMS LOADING
# -------------------------------------------------------------

def load_unified_claims(
    path: str = "CLAIMS_UNIFIED.json",
) -> Dict:
    """
    Load the unified claims file. Returns dict with claims list
    and metadata.
    """
    if not os.path.exists(path):
        return {
            "error": (
                f"CLAIMS_UNIFIED.json not found at {path}. "
                "Coordinator must be run from substrate-aware-"
                "accounting repo root, or path must be supplied."
            )
        }
    with open(path) as f:
        return json.load(f)


def find_relevant_claims(
    query: str,
    claims_data: Dict,
) -> List[Dict]:
    """
    Match claims against query keywords.
    """
    if "error" in claims_data:
        return []

    query_lower = query.lower()
    relevant = []

    for claim in claims_data.get("claims", []):
        # Match on statement text, module name, or repo
        haystack = (
            claim.get("statement", "")
            + " " + claim.get("module", "")
            + " " + claim.get("repo", "")
        ).lower()

        if any(word in haystack for word in query_lower.split()):
            relevant.append(claim)

    return relevant


# -------------------------------------------------------------
# CROSS-REPO AUDIT WORKFLOW
# -------------------------------------------------------------

@dataclass
class AuditPlan:
    query: str
    relevant_modules: List[Dict[str, str]]
    relevant_claims: List[Dict]
    recommended_workflow: List[str]


def plan_audit(
    query: str,
    claims_path: str = "CLAIMS_UNIFIED.json",
) -> AuditPlan:
    """
    Given a query, plan which modules to consult, which claims
    apply, and in what order.
    """
    modules = find_relevant_modules(query)
    claims_data = load_unified_claims(claims_path)
    claims = find_relevant_claims(query, claims_data)

    # Order workflow by repo layer: physics -> economy -> infra.
    layer_order = {
        "thermodynamic base": 0,
        "capital and labor": 1,
        "operational systems": 2,
    }
    modules_sorted = sorted(
        modules,
        key=lambda m: layer_order.get(m["layer"], 99),
    )

    workflow = [
        f"{m['repo']}/{m['module']}" for m in modules_sorted
    ]

    return AuditPlan(
        query=query,
        relevant_modules=modules_sorted,
        relevant_claims=claims,
        recommended_workflow=workflow,
    )


# -------------------------------------------------------------
# REPO INTROSPECTION
# -------------------------------------------------------------

def list_all_repos() -> List[Dict[str, str]]:
    return [
        {
            "name": r.name,
            "url": r.url,
            "layer": r.layer,
            "description": r.description,
            "module_count": len(r.modules),
        }
        for r in REPOS
    ]


def get_repo(name: str) -> Optional[Repository]:
    for r in REPOS:
        if r.name == name:
            return r
    return None


# -------------------------------------------------------------
# DEMO
# -------------------------------------------------------------

def demo():
    print("=" * 74)
    print("CLAUDE CODE COORDINATOR  (substrate-aware-accounting)")
    print("=" * 74)
    print()
    print("Registered repositories:")
    for r in REPOS:
        print(f"  - {r.name} ({r.layer})")
        print(f"    {r.url}")
        print(f"    Modules: {len(r.modules)}")
    print()

    sample_queries = [
        "Is current US oil EROI sustainable through 2030?",
        "What happens to global banking if net energy contracts?",
        "How resilient is a small community to industrial collapse?",
        "Does refinery cascade affect delivered fuel EROI?",
        "How does substrate damage compound across generations?",
    ]

    for q in sample_queries:
        plan = plan_audit(q)
        print("-" * 74)
        print(f"QUERY: {q}")
        print(f"  Relevant modules: {len(plan.relevant_modules)}")
        print(f"  Relevant claims:  {len(plan.relevant_claims)}")
        print(f"  Workflow order:")
        for step in plan.recommended_workflow:
            print(f"    -> {step}")
        print()


if __name__ == "__main__":
    demo()

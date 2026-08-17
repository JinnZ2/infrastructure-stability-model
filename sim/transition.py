#!/usr/bin/env python3
"""
transition.py — transition possibilities from the incumbent design to the target design.

The seven levers in decision-framework.json assume an actor already permitted
to pull them. Most readers are not. This module models the second question:
given who you actually are and what you can do without asking anyone, which
small modifications move the system furthest?

## What it computes

  1. Leverage per lever: effect divided by the cost of getting to pull it.
     Cost is effort, the consent required, and time to effect. A lever that
     needs a legislature is not cheap regardless of its impact rating.

  2. Reachability under an authority budget. Five actor archetypes are
     defined, from a field crew with no institutional standing up to a
     regulator. Each sees a different set of available moves.

  3. Ordered paths that respect prerequisites. L4 before L1 is a hard
     constraint (ledger F-004) and is enforced per locality, not globally.

  4. The minimum viable set: the smallest prefix of the ranked, ordered
     moves that clears the effect threshold. This is the "most leveraged
     small modifications" question stated so it can be answered.

  5. Substrate transitions: the governing, regulatory, corporate, financial,
     and labor moves from decision-framework.json transition_layer, each
     with its active steps and the tier at which each step can be taken.

  6. An intervention schedule consumable by sim/sim.py, so a path chosen
     here can be run through the ODE rather than argued about.

## What it does not compute

Anything empirical. Every effort and effect value is asserted in
decision-framework.json, not measured. Ledger F-010 records this module as
untested. Its output is a structured disagreement surface: change the numbers
in the schema, rerun, and see whether the ranking survives. If your parameters
reverse the ordering, that is the finding.

Usage:
  python3 sim/transition.py                 # full report, all actors
  python3 sim/transition.py actors          # leverage by actor archetype
  python3 sim/transition.py minimal         # minimum viable set per actor
  python3 sim/transition.py substrate       # governance/financial transitions
  python3 sim/transition.py schedule <actor>  # emit ODE intervention schedule
  python3 sim/transition.py sensitivity     # does the ranking survive perturbation
  python3 sim/transition.py verify          # run the plans through the ODE (needs sim/ deps)

Stdlib only. No dependencies.

Authors: Kavik, Claude (Anthropic)
License: CC0 1.0 Universal
"""

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMEWORK = os.path.join(ROOT, "decision-framework.json")


# ---------------------------------------------------------------------------
# Actor archetypes — who is reading this, and what can they do unasked
# ---------------------------------------------------------------------------

@dataclass
class Actor:
    """
    An actor is defined by the highest authority tier they can reach without
    a consent negotiation, plus the tiers they can reach with one.

    The distinction matters more than it looks. A tier-0 move is available
    today. A tier-3 move requires a campaign whose duration is not counted in
    the lever's time_to_effect_months, because the schema measures time from
    the decision, not time to get the decision made.
    """
    key: str
    name: str
    unilateral_tier: int          # can act without asking
    negotiable_tier: int          # can reach with a consent campaign
    negotiation_months: float     # how long that campaign typically runs
    note: str


ACTORS = [
    Actor("crew", "Field crew / individual practitioner", 0, 1, 6.0,
          "No institutional standing. Can traverse peer networks, build "
          "parallel visibility channels, and change nothing about policy."),
    Actor("site", "Site or plant supervisor", 1, 2, 12.0,
          "Controls work assignment and local sequencing. Cannot allocate "
          "capital or change architecture."),
    Actor("firm", "Firm leadership or municipal authority", 2, 3, 24.0,
          "Controls capital allocation and system architecture. Faces "
          "statutory gates on credentialing and compensation."),
    Actor("regulator", "State or federal regulator", 3, 3, 0.0,
          "Can move statutory gates. Slowest time constants, weakest "
          "visibility into tier-1 physical state."),
    Actor("community", "Community or mutual-aid organization", 0, 2, 18.0,
          "No standing inside the firm, but holds the scope-audit levers in "
          "audit/ — the charter and regulatory scope-exit records."),
]

ACTORS_BY_KEY = {a.key: a for a in ACTORS}


# ---------------------------------------------------------------------------
# Loading levers from the schema
# ---------------------------------------------------------------------------

@dataclass
class Lever:
    id: str
    name: str
    description: str
    effect: float
    effort: float
    authority_tier: int
    reversibility: str
    time_to_effect_months: Tuple[float, float]
    prerequisite: Optional[str]
    incumbent_state: str
    target_state: str
    authority_note: str
    reversibility_note: Optional[str] = None

    @property
    def time_mid(self) -> float:
        lo, hi = self.time_to_effect_months
        return (lo + hi) / 2.0


# Consent cost multiplier by authority tier. Asserted, not measured.
# Rationale: each tier up adds an actor whose agreement is required and whose
# incentives are less coupled to tier-1 physical state. Superlinear because
# consent chains compound rather than add.
CONSENT_COST = {0: 1.0, 1: 1.6, 2: 3.0, 3: 6.0}

# Reversibility penalty. An irreversible move must be right the first time,
# which is a real cost even when the expected value is positive.
REVERSIBILITY_PENALTY = {"high": 1.0, "medium": 1.25, "low": 1.7}


def load_levers(path: str = FRAMEWORK) -> List[Lever]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    levers = []
    for key, raw in data["levers"].items():
        missing = [f for f in ("effect_normalized", "effort_normalized",
                               "authority_tier", "reversibility")
                   if f not in raw]
        if missing:
            raise SystemExit(
                f"{key} is missing transition fields {missing} in "
                f"decision-framework.json. This module reads the schema; it "
                f"does not carry its own copy of the numbers."
            )
        prereq = raw.get("prerequisite")
        if prereq:
            prereq = prereq.split("_")[0]  # "L4_B_i_reduction" -> "L4"
        levers.append(Lever(
            id=raw["id"],
            name=raw["name"],
            description=raw["description"],
            effect=float(raw["effect_normalized"]),
            effort=float(raw["effort_normalized"]),
            authority_tier=int(raw["authority_tier"]),
            reversibility=raw["reversibility"],
            time_to_effect_months=tuple(raw["time_to_effect_months"]),
            prerequisite=prereq,
            incumbent_state=raw.get("incumbent_state", ""),
            target_state=raw.get("target_state", ""),
            authority_note=raw.get("authority_note", ""),
            reversibility_note=raw.get("reversibility_note"),
        ))
    return levers


def load_transition_layer(path: str = FRAMEWORK) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["transition_layer"]


# ---------------------------------------------------------------------------
# Leverage
# ---------------------------------------------------------------------------

def consent_cost(lever: Lever, actor: Actor) -> Tuple[float, str]:
    """
    Cost multiplier for this actor to reach this lever, and how they reach it.

    Returns (multiplier, mode) where mode is 'unilateral', 'negotiated', or
    'out_of_reach'. Out-of-reach levers are not dropped — they are reported
    as blocked, because knowing which lever you cannot pull is what tells you
    which coalition you need.
    """
    if lever.authority_tier <= actor.unilateral_tier:
        return CONSENT_COST[lever.authority_tier], "unilateral"
    if lever.authority_tier <= actor.negotiable_tier:
        return CONSENT_COST[lever.authority_tier], "negotiated"
    return CONSENT_COST[lever.authority_tier] * 2.0, "out_of_reach"


def time_cost(lever: Lever, actor: Actor, mode: str) -> float:
    """Months to effect, including the consent campaign where one is needed."""
    base = lever.time_mid
    if mode == "unilateral":
        return base
    if mode == "negotiated":
        return base + actor.negotiation_months
    return base + actor.negotiation_months * 2.0


def leverage(lever: Lever, actor: Actor) -> dict:
    """
    leverage = effect / (effort * consent * reversibility_penalty * time_factor)

    Deliberately simple and deliberately exposed. The ranking this produces
    is only as good as the four asserted inputs, and the sensitivity mode
    exists to show how much of the ranking is robust to them.
    """
    consent, mode = consent_cost(lever, actor)
    months = time_cost(lever, actor, mode)
    time_factor = 1.0 + months / 12.0
    rev = REVERSIBILITY_PENALTY[lever.reversibility]

    cost = max(1e-9, lever.effort * consent * rev * time_factor)
    return {
        "lever": lever,
        "mode": mode,
        "consent_multiplier": consent,
        "months_to_effect": months,
        "cost": cost,
        "leverage": lever.effect / cost,
    }


def rank_for_actor(levers: List[Lever], actor: Actor) -> List[dict]:
    scored = [leverage(l, actor) for l in levers]
    scored.sort(key=lambda r: -r["leverage"])
    return scored


# ---------------------------------------------------------------------------
# Ordering — prerequisites are a hard constraint, not a preference
# ---------------------------------------------------------------------------

def order_respecting_prerequisites(selected: List[Lever]) -> List[Lever]:
    """
    Topological order over the prerequisite edges, ties broken by effect.

    The only prerequisite edge currently in the schema is L4 -> L1, which
    ledger F-002/F-003 narrowed and F-004 localized: it binds within a
    locality and does not bind across them. This function enforces it as a
    within-path constraint. A caller running separate localities should call
    it once per locality, not once globally.
    """
    ids = {l.id for l in selected}
    remaining = list(selected)
    ordered: List[Lever] = []
    placed: set = set()

    while remaining:
        ready = [l for l in remaining
                 if not l.prerequisite
                 or l.prerequisite not in ids
                 or l.prerequisite in placed]
        if not ready:
            # Cycle or unsatisfiable prerequisite. Report rather than hang.
            raise ValueError(
                f"unsatisfiable prerequisite among {[l.id for l in remaining]}"
            )
        ready.sort(key=lambda l: -l.effect)
        nxt = ready[0]
        ordered.append(nxt)
        placed.add(nxt.id)
        remaining.remove(nxt)
    return ordered


def pull_in_prerequisites(selected: List[Lever], all_levers: List[Lever]) -> List[Lever]:
    """
    A selection that includes L1 but not L4 is not a cheaper plan. It is the
    wrong-order plan, and ledger F-003 priced it: hub survival 30% vs 100%.
    Prerequisites are added to the set even when their own leverage did not
    earn them a place.
    """
    by_id = {l.id: l for l in all_levers}
    out = {l.id: l for l in selected}
    changed = True
    while changed:
        changed = False
        for lever in list(out.values()):
            if lever.prerequisite and lever.prerequisite not in out:
                if lever.prerequisite in by_id:
                    out[lever.prerequisite] = by_id[lever.prerequisite]
                    changed = True
    return list(out.values())


# ---------------------------------------------------------------------------
# Minimum viable set
# ---------------------------------------------------------------------------

def minimum_viable_set(levers: List[Lever], actor: Actor,
                       effect_target: float = 1.5,
                       max_effort: Optional[float] = None,
                       unilateral_only: bool = False) -> dict:
    """
    Smallest set of moves, taken in leverage order, whose combined effect
    clears effect_target.

    Combined effect uses diminishing returns rather than a plain sum: each
    additional lever contributes against what is left, not against the whole.
    Levers act on overlapping variables and cannot be additive. The
    interaction matrix in decision-framework.json names six couplings; this
    is a coarse stand-in for them and is the weakest assumption in the module.
    """
    candidates = rank_for_actor(levers, actor)
    if unilateral_only:
        candidates = [c for c in candidates if c["mode"] == "unilateral"]
    if max_effort is not None:
        candidates = [c for c in candidates
                      if c["lever"].effort <= max_effort]

    chosen: List[Lever] = []
    combined = 0.0
    for cand in candidates:
        if combined >= effect_target:
            break
        chosen.append(cand["lever"])
        combined = combined_effect(chosen)

    chosen = pull_in_prerequisites(chosen, levers)
    combined = combined_effect(chosen)
    ordered = order_respecting_prerequisites(chosen)

    return {
        "actor": actor,
        "ordered": ordered,
        "combined_effect": combined,
        "target": effect_target,
        "reached": combined >= effect_target,
        "total_effort": sum(l.effort for l in ordered),
        "horizon_months": max(
            (leverage(l, actor)["months_to_effect"] for l in ordered),
            default=0.0),
        "unilateral_only": unilateral_only,
    }


def combined_effect(levers: List[Lever]) -> float:
    """
    Diminishing-returns combination. Sorted by effect so the ordering of the
    input list does not change the total.
    """
    total = 0.0
    for lever in sorted(levers, key=lambda l: -l.effect):
        total += lever.effect * (1.0 / (1.0 + 0.45 * total))
    return total


# ---------------------------------------------------------------------------
# ODE handoff — emit a schedule sim/sim.py can run
# ---------------------------------------------------------------------------

# Which model parameter each lever moves, and toward what. Targets match the
# values sim/sim.py uses in its correct-sequence scenario, so a path chosen
# here is directly comparable to the scenarios already in figures/.
#
# Three of these are direct and four are proxies. The ODE has no state
# variable for "which nodes are deployed where", so L2 is carried as an
# increase in training throughput on the argument that older high-R_i nodes
# act as mentor hubs. That is a real effect but not the whole of L2, and it
# is the weakest mapping in the table. L6 and L7 are similarly indirect.
LEVER_TO_PARAM = {
    "L1": ("signal_fidelity", 0.75),        # direct
    "L2": ("T_rate", 0.20),                 # proxy: mentor-hub throughput only
    "L3": ("epsilon", 0.12),                # direct
    "L4": ("B_i", 0.10),                    # direct
    "L5": ("Y_bias", 0.45),                 # proxy: expansion pressure
    "L6": ("optimization_pressure", 0.01),  # proxy: drives kappa
    "L7": ("S_weight", 0.70),               # proxy: stability weighting
}


def emit_schedule(plan: dict) -> dict:
    """
    Turn an ordered plan into start months per parameter.

    Each lever starts when its prerequisites have had time to bite, not when
    the previous lever starts. That gap is the whole content of the
    sequencing constraint and it must survive the handoff to the ODE.
    """
    actor = plan["actor"]
    schedule = []
    cursor = 0.0
    started: Dict[str, float] = {}

    for lever in plan["ordered"]:
        start = cursor
        if lever.prerequisite and lever.prerequisite in started:
            prereq_start = started[lever.prerequisite]
            prereq = next(l for l in plan["ordered"]
                          if l.id == lever.prerequisite)
            # wait for the prerequisite's lower time bound to take effect
            start = max(start, prereq_start + prereq.time_to_effect_months[0])
        started[lever.id] = start

        if lever.id in LEVER_TO_PARAM:
            param, target = LEVER_TO_PARAM[lever.id]
            schedule.append({
                "lever": lever.id,
                "param": param,
                "target": target,
                "start_month": round(start, 1),
                "ramp_months": 3.0,
            })
        cursor = start + 1.0  # moves are staggered, not simultaneous

    return {
        "actor": actor.key,
        "actor_name": actor.name,
        "interventions": schedule,
        "note": "Feed to sim/sim.py Intervention(param, target, start_month, "
                "ramp_months). Start months include consent-campaign time "
                "where the actor cannot act unilaterally.",
        "evidence_status": "untested — see ledger F-010",
    }


# ---------------------------------------------------------------------------
# Sensitivity — does the ranking survive the numbers being wrong
# ---------------------------------------------------------------------------

def rank_sensitivity(levers: List[Lever], actor: Actor,
                     spread: float = 0.30, trials: int = 400,
                     seed: int = 42) -> dict:
    """
    Perturb each lever's effect and effort INDEPENDENTLY and see which levers
    hold their rank.

    Independently is the whole point. An earlier version of this function
    scaled every lever by the same factor per trial, which cannot reorder a
    ranking at all — leverage is effect/cost, so a common factor divides out
    and the test reported perfect stability for every actor. That is the same
    defect ledger F-004 found in the partial-order test: a check that cannot
    produce the failure it is checking for. Recorded as F-011.

    Each trial draws an independent multiplier per lever per parameter from
    U(1-spread, 1+spread). Seeded, so the result is reproducible.
    """
    import random

    rng = random.Random(seed)
    baseline = [r["lever"].id for r in rank_for_actor(levers, actor)]
    base_pos = {lid: i for i, lid in enumerate(baseline)}
    positions: Dict[str, List[int]] = {lid: [] for lid in baseline}

    for _ in range(trials):
        perturbed = []
        for lever in levers:
            clone = Lever(**{**lever.__dict__})
            clone.effect = max(0.01, min(1.0,
                lever.effect * rng.uniform(1 - spread, 1 + spread)))
            clone.effort = max(0.01, min(1.0,
                lever.effort * rng.uniform(1 - spread, 1 + spread)))
            perturbed.append(clone)
        order = [r["lever"].id for r in rank_for_actor(perturbed, actor)]
        for pos, lid in enumerate(order):
            positions[lid].append(pos)

    stable, unstable = [], []
    for lid, seen in positions.items():
        drift = max(seen) - min(seen)
        held = sum(1 for p in seen if p == base_pos[lid]) / len(seen)
        record = (lid, drift, held)
        (stable if drift <= 1 else unstable).append(record)

    stable.sort(key=lambda t: base_pos[t[0]])
    unstable.sort(key=lambda t: -t[1])

    # Set membership is a weaker claim than ordering and survives where
    # ordering does not. If the same three levers occupy the top three slots
    # in every trial while permuting among themselves, the defensible finding
    # is "these three, order unresolved" — not a ranked list.
    top_n = 3
    in_top = {lid: sum(1 for p in seen if p < top_n) / len(seen)
              for lid, seen in positions.items()}
    baseline_top = set(baseline[:top_n])
    top_set_intact = all(in_top[lid] == 1.0 for lid in baseline_top) and \
        all(in_top[lid] == 0.0 for lid in baseline[top_n:])

    return {
        "baseline": baseline,
        "stable": stable,
        "unstable": unstable,
        "trials": trials,
        "spread": spread,
        "top_n": top_n,
        "top_set": sorted(baseline_top),
        "top_membership": in_top,
        "top_set_intact": top_set_intact,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

BAR = "=" * 78
DASH = "-" * 78


def _header(title):
    print(f"\n{BAR}\n{title}\n{BAR}")


def report_actors(levers: List[Lever]):
    _header("LEVERAGE BY ACTOR — effect divided by the cost of being allowed to act")

    for actor in ACTORS:
        print(f"\n{actor.name}  [tier {actor.unilateral_tier} unilateral, "
              f"{actor.negotiable_tier} negotiable]")
        print(f"  {actor.note}")
        print(f"\n  {'lever':<6} {'name':<34} {'lev':>6} {'mode':<12} {'mo':>5}")
        print("  " + DASH[:74])
        for r in rank_for_actor(levers, actor):
            lever = r["lever"]
            marker = " " if r["mode"] == "unilateral" else (
                "~" if r["mode"] == "negotiated" else "x")
            print(f"  {marker}{lever.id:<5} {lever.name[:34]:<34} "
                  f"{r['leverage']:>6.2f} {r['mode']:<12} "
                  f"{r['months_to_effect']:>5.0f}")
        print("\n  blank = can act today   ~ = needs a consent campaign   "
              "x = out of reach alone")


def report_minimal(levers: List[Lever]):
    _header("MOST LEVERAGED SMALL MODIFICATIONS — minimum set that clears the target")

    print("\nCombined effect uses diminishing returns, not a sum. Prerequisites are")
    print("pulled in even when their own leverage did not earn them a place: a plan")
    print("with L1 and no L4 is not cheaper, it is the wrong-order plan that ledger")
    print("F-003 priced at 30% hub survival.\n")

    for actor in ACTORS:
        for unilateral in (True, False):
            plan = minimum_viable_set(levers, actor, unilateral_only=unilateral)
            scope = "acting alone" if unilateral else "with consent campaigns"
            if unilateral and not plan["ordered"]:
                print(f"\n{actor.name} — {scope}: nothing available.")
                continue

            status = "reaches target" if plan["reached"] else (
                "DOES NOT reach target")
            print(f"\n{actor.name} — {scope}")
            print(f"  {' -> '.join(l.id for l in plan['ordered'])}"
                  f"   effect {plan['combined_effect']:.2f}/{plan['target']:.1f} "
                  f"({status}), effort {plan['total_effort']:.2f}, "
                  f"horizon {plan['horizon_months']:.0f} mo")
            for i, lever in enumerate(plan["ordered"], 1):
                print(f"    {i}. {lever.id} {lever.name}")
                print(f"       {lever.incumbent_state}")
                print(f"       -> {lever.target_state}")


def report_substrate():
    _header("SUBSTRATE TRANSITIONS — the governing and financial steps")

    layer = load_transition_layer()
    print(f"\n{layer['why_this_layer_exists']}\n")

    for name, sub in layer["substrate_states"].items():
        print(f"\n{DASH}\n{name.upper()}\n{DASH}")
        print(f"  from: {sub['incumbent']}")
        print(f"    to: {sub['target']}")
        print("\n  active steps, in order:")
        for i, step in enumerate(sub["active_steps"], 1):
            print(f"    {i}. {step}")
        if sub.get("audit_modules"):
            print(f"\n  modules: {', '.join(sub['audit_modules'])}")
        for extra in ("note", "sequencing_note"):
            if sub.get(extra):
                print(f"\n  {extra}: {sub[extra]}")

    print(f"\n{DASH}\nGENERAL PATTERN\n{DASH}")
    print(f"  {layer['general_pattern']}")
    print(f"\n  evidence status: {layer['evidence_status']}")
    print(f"  {layer['evidence_note']}")


def report_sensitivity(levers: List[Lever]):
    _header("RANK SENSITIVITY — how much of the ordering survives the numbers being wrong")

    res0 = rank_sensitivity(levers, ACTORS[0])
    print(f"\nEach lever's effect and effort perturbed INDEPENDENTLY by up to")
    print(f"+/-{res0['spread']:.0%} over {res0['trials']} seeded trials. A lever whose rank")
    print("moves more than one place under that is not a ranked result, it is")
    print("noise with an ordering. 'held' is the fraction of trials in which the")
    print("lever kept its exact baseline position.\n")

    for actor in ACTORS:
        res = rank_sensitivity(levers, actor)
        print(f"\n{actor.name}")
        print(f"  baseline order: {' > '.join(res['baseline'])}")
        if res["stable"]:
            print("  rank-stable:    " + ", ".join(
                f"{l}({h:.0%})" for l, _, h in res["stable"]))
        else:
            print("  rank-stable:    none")
        if res["unstable"]:
            print("  rank-unstable:  " + ", ".join(
                f"{l}(drift {d}, held {h:.0%})" for l, d, h in res["unstable"]))
        else:
            print("  rank-unstable:  none")
        verdict = ("INTACT in every trial" if res["top_set_intact"]
                   else "NOT intact — membership changes under perturbation")
        print(f"  top-{res['top_n']} set:     "
              f"{{{', '.join(res['top_set'])}}} {verdict}")


def report_schedule(levers: List[Lever], actor_key: str):
    actor = ACTORS_BY_KEY.get(actor_key)
    if actor is None:
        print(f"Unknown actor '{actor_key}'. "
              f"Choose from: {', '.join(ACTORS_BY_KEY)}")
        return
    plan = minimum_viable_set(levers, actor, unilateral_only=False)
    print(json.dumps(emit_schedule(plan), indent=2))


def report_verify(levers: List[Lever]):
    """
    Run each actor's emitted plan through the ODE in sim/sim.py.

    This is the step that stops the leverage ranking from being an opinion.
    A plan that ranks well but does not move Phi is a plan that ranks well.
    Requires numpy and scipy; the rest of this module does not.
    """
    try:
        import numpy as np
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from sim import Intervention, run_scenario, make_scenarios
    except ImportError as exc:
        print(f"\nverify mode needs the sim/ dependencies ({exc}).")
        print("  pip install -r requirements.txt")
        print("Every other mode in this module is stdlib-only and still works.")
        return

    marks = [12, 36, 60, 120]

    def phi_curve(res):
        return res["t_months"], res["derived"]["Phi"]

    def phi_at(res):
        t, phi = phi_curve(res)
        return [float(np.interp(m, t, phi)) for m in marks]

    def crossings(res):
        """First month Phi rises back through 0.7 and through 1.0, if ever."""
        t, phi = phi_curve(res)
        out = []
        for threshold in (0.70, 1.00):
            hit = None
            for i in range(1, len(t)):
                if phi[i - 1] < threshold <= phi[i]:
                    hit = float(t[i])
                    break
            out.append(hit)
        return out

    _header("ODE VERIFICATION — do the ranked plans actually move Phi")

    print("\nEach actor's minimum viable set is emitted as an intervention")
    print("schedule and integrated by sim/sim.py, against the four reference")
    print("scenarios already in figures/. 'back>0.7' is the month Phi rises")
    print("back through the stability threshold; '-' means it never does.\n")

    hdr = (f"  {'plan':<44}" + "".join(f"{m:>7}" for m in marks)
           + f"{'back>0.7':>10}{'back>1.0':>10}")
    print(hdr)
    print("  " + DASH[:len(hdr) - 2])

    for _, (label, ivs) in make_scenarios().items():
        res = run_scenario(label, ivs)
        c07, c10 = crossings(res)
        print(f"  {label[:44]:<44}"
              + "".join(f"{v:>7.3f}" for v in phi_at(res))
              + f"{(f'{c07:.0f}' if c07 else '-'):>10}"
              + f"{(f'{c10:.0f}' if c10 else '-'):>10}")

    print()
    seen = set()
    for actor in ACTORS:
        for unilateral in (True, False):
            plan = minimum_viable_set(levers, actor, unilateral_only=unilateral)
            if not plan["ordered"]:
                continue
            path = "->".join(l.id for l in plan["ordered"])
            tag = "alone" if unilateral else "negotiated"
            key = (path, tag)
            if key in seen:
                continue
            seen.add(key)

            sched = emit_schedule(plan)
            ivs = [Intervention(i["param"], target=i["target"],
                                start_month=i["start_month"],
                                ramp_months=i["ramp_months"])
                   for i in sched["interventions"]]
            res = run_scenario(path, ivs)
            c07, c10 = crossings(res)
            label = f"{path} ({tag}, tier<={actor.unilateral_tier})"
            print(f"  {label[:44]:<44}"
                  + "".join(f"{v:>7.3f}" for v in phi_at(res))
                  + f"{(f'{c07:.0f}' if c07 else '-'):>10}"
                  + f"{(f'{c10:.0f}' if c10 else '-'):>10}")

    print("""
  Read the trajectory, not the endpoint. The tier-0 path drops Phi hard and
  early, then drifts back up: it adds labor bandwidth but touches neither the
  complexity ratchet (L5) nor coupling (L6), so C keeps growing and eats the
  gain. The levers that hold the gain are the ones a crew cannot pull.

  That makes the no-permission path a bridge, not a destination. What it buys
  is the window — and the record it produces during that window is the
  argument for the tier-2 ask. See transition_layer.general_pattern.""")


def report_full(levers: List[Lever]):
    print(BAR)
    print("TRANSITION POSSIBILITIES — incumbent design to target design")
    print(BAR)
    print("""
The seven levers assume an actor already permitted to pull them. This asks the
second question: given what you can do without asking anyone, which small
modifications move the system furthest, and in what order.

Every number here is asserted in decision-framework.json, not measured. Ledger
F-010 carries this module as untested. Change the numbers, rerun, and see
whether the ranking survives — the sensitivity mode exists for exactly that.
""")
    report_actors(levers)
    report_minimal(levers)
    report_substrate()
    report_sensitivity(levers)
    report_verify(levers)

    _header("HANDOFF")
    print("\n  python3 sim/transition.py schedule crew   > schedule.json")
    print("  ...then feed the interventions to sim/sim.py to run the path"
          "\n     through the ODE instead of arguing about it.\n")


def main():
    levers = load_levers()
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "full"):
        report_full(levers)
    elif mode == "actors":
        report_actors(levers)
    elif mode == "minimal":
        report_minimal(levers)
    elif mode == "substrate":
        report_substrate()
    elif mode == "sensitivity":
        report_sensitivity(levers)
    elif mode == "verify":
        report_verify(levers)
    elif mode == "schedule":
        report_schedule(levers, sys.argv[2] if len(sys.argv) > 2 else "crew")
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python3 sim/transition.py "
              "[all|actors|minimal|substrate|sensitivity|verify|schedule <actor>]")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

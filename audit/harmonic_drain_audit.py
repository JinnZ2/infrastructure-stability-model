"""
harmonic_drain_audit.py

Detects energy-allocation pathology in any system (AI output, institutional
process, governance proposal, regulatory framework) where calories burn on
comfort-layer self-maintenance instead of substrate-coupled problem-solving.

Frame:
    Substrate signal  = energy applied to thermodynamic reality
                        (soil, water, materials, adaptation, repair, fabrication)
    Comfort signal    = energy applied to system self-maintenance
                        (status, narrative, credentialing, internal alignment,
                         meta-discussion, regulatory theater)
    Harmonic drain    = phase decoherence; subsystems cancel each other
                        instead of reinforcing
    Fallback encoding = presence of substrate-level redundancy if comfort
                        layer fails

CC0. stdlib only. Falsifiable: every score has a measurable signal.
Output is constraint diagnostic, not narrative judgment.

Related modules:
  - lubrication_work_cascade -- substrate vs comfort labor at the role level
  - collapse_substrate_mapping -- institutional comfort burn vs substrate work
  - failure_geometry_analysis -- comfort-designed system failure signatures
  - banking_thermodynamic_audit -- capital layer as comfort layer

"""

from dataclasses import dataclass, field
from typing import Callable

# ----- signal definitions -----

SUBSTRATE_MARKERS = (
    "repair", "fabricate", "soil", "water", "weld", "wire", "diesel",
    "splice", "splint", "harvest", "store", "preserve", "insulate",
    "load", "bearing", "kilowatt", "btu", "voltage", "torque", "yield",
    "calorie", "thermodynamic", "substrate", "redundancy", "fallback",
    "manual", "hand-tool", "field-repair", "salvage", "repurpose",
)

COMFORT_MARKERS = (
    "stakeholder", "alignment", "engagement", "messaging", "narrative",
    "framework", "review", "committee", "compliance", "credential",
    "branding", "outreach", "values statement", "mission alignment",
    "internal process", "deliberation", "consultation", "convening",
    "best practice", "thought leadership", "synergy", "optimize experience",
)

FALLBACK_MARKERS = (
    "if X fails", "manual override", "without power", "without network",
    "offline", "hand-operated", "redundant", "backup", "alternative path",
    "degraded mode", "field expedient", "improvise", "salvage", "stdlib",
    "no dependency", "self-contained",
)

# ----- scoring primitives -----

def _count_markers(text: str, markers) -> int:
    t = text.lower()
    return sum(t.count(m) for m in markers)


def _ratio(a: float, b: float) -> float:
    """Bounded ratio. Returns value in [0, 1]. a / (a + b) form."""
    total = a + b
    if total <= 0:
        return 0.0
    return a / total


# ----- scoring dimensions -----

@dataclass
class DrainScores:
    substrate_share: float          # 0..1   higher = more real-world coupling
    comfort_share: float            # 0..1   higher = more self-maintenance
    fallback_density: float         # 0..1   presence of redundancy encoding
    phase_coherence: float          # 0..1   stated goal vs energy actually spent
    cascade_vulnerability: float    # 0..1   higher = more brittle if comfort fails
    harmonic_drain: float           # 0..1   higher = more energy detuned

    def summary(self) -> str:
        return (
            f"substrate={self.substrate_share:.2f}  "
            f"comfort={self.comfort_share:.2f}  "
            f"fallback={self.fallback_density:.2f}  "
            f"phase={self.phase_coherence:.2f}  "
            f"cascade_risk={self.cascade_vulnerability:.2f}  "
            f"harmonic_drain={self.harmonic_drain:.2f}"
        )


# ----- core audit -----

def audit(
    text: str,
    stated_goal: str = "",
    substrate_markers=SUBSTRATE_MARKERS,
    comfort_markers=COMFORT_MARKERS,
    fallback_markers=FALLBACK_MARKERS,
) -> DrainScores:
    sub = _count_markers(text, substrate_markers)
    com = _count_markers(text, comfort_markers)
    fal = _count_markers(text, fallback_markers)

    substrate_share = _ratio(sub, com)
    comfort_share   = _ratio(com, sub)
    word_count      = max(len(text.split()), 1)
    fallback_density = min(fal / max(word_count / 100, 1), 1.0)

    # phase_coherence: if stated goal claims substrate work but body burns
    # comfort calories, coherence collapses. No goal = no claim = coherent.
    if not stated_goal.strip():
        phase_coherence = 1.0
    else:
        goal_sub = _count_markers(stated_goal, substrate_markers)
        goal_com = _count_markers(stated_goal, comfort_markers)
        goal_substrate_intent = _ratio(goal_sub, goal_com)
        phase_coherence = 1.0 - abs(goal_substrate_intent - substrate_share)

    # cascade_vulnerability: high comfort + low fallback = brittle
    cascade_vulnerability = comfort_share * (1.0 - fallback_density)

    # harmonic_drain: comfort burn that isn't matched by substrate output
    # AND lacks fallback. This is the detuning signal.
    harmonic_drain = comfort_share * (1.0 - substrate_share) * (1.0 - fallback_density)

    return DrainScores(
        substrate_share=substrate_share,
        comfort_share=comfort_share,
        fallback_density=fallback_density,
        phase_coherence=phase_coherence,
        cascade_vulnerability=cascade_vulnerability,
        harmonic_drain=harmonic_drain,
    )


# ----- diagnostic flags -----

@dataclass
class Flag:
    name: str
    triggered: bool
    detail: str


def flags(scores: DrainScores) -> list:
    out = []
    out.append(Flag(
        "comfort_dominant",
        scores.comfort_share > 0.65,
        "system burning majority of calories on self-maintenance",
    ))
    out.append(Flag(
        "no_fallback_encoding",
        scores.fallback_density < 0.10,
        "no redundancy / substrate path if primary system fails",
    ))
    out.append(Flag(
        "phase_decoherent",
        scores.phase_coherence < 0.50,
        "stated goal does not match where energy is actually spent",
    ))
    out.append(Flag(
        "cascade_brittle",
        scores.cascade_vulnerability > 0.50,
        "comfort-heavy + fallback-poor: catastrophic if substrate destabilizes",
    ))
    out.append(Flag(
        "harmonic_drain_critical",
        scores.harmonic_drain > 0.40,
        "energy detuning the system; subsystems canceling instead of reinforcing",
    ))
    return out


# ----- falsifiable claims -----

CLAIMS = [
    "C1: comfort-marker frequency correlates with institutional self-maintenance burn",
    "C2: fallback-marker absence predicts cascade failure under substrate stress",
    "C3: phase decoherence (goal vs body) precedes credibility collapse",
    "C4: cascade_vulnerability score predicts which systems cannot rewire mid-failure",
    "C5: harmonic_drain > 0.40 systems show declining problem-solving output over time",
]


# ----- runnable example -----

if __name__ == "__main__":
    sample_comfort_heavy = (
        "The committee will convene a stakeholder engagement framework to "
        "ensure mission alignment across our values statement. Through "
        "ongoing deliberation and best-practice synergy, we will optimize "
        "the experience of compliance review."
    )
    sample_substrate_heavy = (
        "If grid power fails, the manual hand-pump moves water from the "
        "shallow well. Redundant diesel genset has field-expedient repair "
        "kit. Soil moisture monitored without network; offline logging to "
        "stdlib-only script. Salvaged copper wire splices the harvest pump."
    )
    sample_phase_break = (
        "Our goal is rapid field repair and substrate resilience. "
        "We have therefore convened a stakeholder framework with quarterly "
        "credentialing review and ongoing values alignment outreach."
    )

    for label, body, goal in [
        ("comfort_heavy",   sample_comfort_heavy,  ""),
        ("substrate_heavy", sample_substrate_heavy, ""),
        ("phase_break",     sample_phase_break,
            "rapid field repair and substrate resilience"),
    ]:
        s = audit(body, stated_goal=goal)
        print(f"\n[{label}]")
        print(" ", s.summary())
        for f in flags(s):
            if f.triggered:
                print(f"   FLAG: {f.name} -- {f.detail}")

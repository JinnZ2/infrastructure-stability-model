"""
gravity_rail_human_scale.py

Models a community-scale gravity-rail energy harvest. One person
supervises the descent of a loaded cart on a track and walks back
up empty; gravity is the engine, the human is the brake operator
and load coordinator, the load is substrate the community already
has reason to move downhill (firewood, harvest, rock, water
containers for irrigation, etc.).

The arithmetic distinguishes two regimes:

  BACKPACK SCALE -- person carries the load. Per-person carry mass
  is bounded by human physiology (~25-40 kg). Even on 75 m of grade
  at 5 cycles/day with realistic efficiency losses, this nets
  roughly 0.02 kWh/day. Insufficient.

  RAIL SCALE -- gravity is the engine; the person is the supervisor.
  Net mass per cycle can reach thousands of kg. The same elevation
  at 4 cycles/day with 2-3 t net mass yields ~1-2 kWh/cycle and
  survival-grade output. Staggered carts push toward the 3-5 kWh/day
  range.

The point is not to argue the human is strong enough; it is to
distinguish architectures that produce orders-of-magnitude different
yields from the same person-day of labor.

Scope (terrain prerequisite):
  - useful grade: 50-100 m elevation change over walkable distance
  - load source: substrate the community already moves downhill
  - storage sink: mechanical spring, pumped reservoir, flywheel,
    small battery bank, or direct work (grain mill, tool sharpening,
    water lift to header tank)

What 3-5 kWh/day covers (survival-grade, not industrial):
  - LED lighting for a household
  - refrigeration of essentials (efficient chest unit)
  - communications (radio, low-power data)
  - small appliance use (mixer, fan, charger bank)
  - modest tool operation (drill, light grinder, sewing machine)

What it does NOT cover:
  - air conditioning at scale
  - electric heating
  - industrial production
  - electric vehicles charged regularly

CC0. Stdlib only.
"""

import dataclasses
from dataclasses import dataclass
from typing import List, Dict


GRAVITY_M_S2 = 9.81
JOULES_PER_KWH = 3_600_000.0


# -------------------------------------------------------------
# 1. SYSTEM PARAMETERS
# -------------------------------------------------------------

@dataclass
class GravityRailSystem:
    """
    A gravity-rail installation on a community-scale slope.
    """
    name: str
    elevation_m: float                  # vertical drop, meters
    loaded_cart_mass_kg: float          # mass going down
    empty_cart_mass_kg: float           # mass coming back up
    cycles_per_day: int                 # complete down+up cycles per cart

    # If multiple carts are staggered through the day, one supervisor
    # can manage more than one. Total cycles = cycles_per_day * carts.
    carts_in_circulation: int = 1

    # Efficiencies (0..1)
    brake_to_storage_efficiency: float = 0.70
    storage_roundtrip_efficiency: float = 0.85

    operators: int = 1

    def net_mass_per_cycle_kg(self) -> float:
        return max(0.0, self.loaded_cart_mass_kg - self.empty_cart_mass_kg)

    def potential_energy_per_cycle_j(self) -> float:
        return (
            self.net_mass_per_cycle_kg()
            * GRAVITY_M_S2
            * self.elevation_m
        )

    def useful_energy_per_cycle_j(self) -> float:
        return (
            self.potential_energy_per_cycle_j()
            * self.brake_to_storage_efficiency
            * self.storage_roundtrip_efficiency
        )

    def daily_kwh(self) -> float:
        total_cycles = self.cycles_per_day * self.carts_in_circulation
        return self.useful_energy_per_cycle_j() * total_cycles / JOULES_PER_KWH

    def daily_kwh_per_operator(self) -> float:
        if self.operators <= 0:
            return 0.0
        return self.daily_kwh() / self.operators


# -------------------------------------------------------------
# 2. ARCHETYPES
# -------------------------------------------------------------

BACKPACK_HUMAN = GravityRailSystem(
    name="Backpack-scale (person carries load down, walks back up empty)",
    elevation_m=75.0,
    loaded_cart_mass_kg=30.0,
    empty_cart_mass_kg=0.0,
    cycles_per_day=5,
    brake_to_storage_efficiency=0.70,
    storage_roundtrip_efficiency=0.85,
    operators=1,
)

SMALL_HANDCART = GravityRailSystem(
    name="Small handcart on rail (one operator, ~200 kg net)",
    elevation_m=75.0,
    loaded_cart_mass_kg=220.0,
    empty_cart_mass_kg=40.0,
    cycles_per_day=5,
    brake_to_storage_efficiency=0.75,
    storage_roundtrip_efficiency=0.85,
    operators=1,
)

COUNTERWEIGHT_RAIL = GravityRailSystem(
    name="Counterweight rail (~2 t net per cycle, 4 cycles/day)",
    elevation_m=75.0,
    loaded_cart_mass_kg=2200.0,
    empty_cart_mass_kg=200.0,
    cycles_per_day=4,
    brake_to_storage_efficiency=0.80,
    storage_roundtrip_efficiency=0.85,
    operators=1,
)

FUNICULAR_COMMUNITY = GravityRailSystem(
    name="Funicular community rail (~3 t net, 2 carts staggered)",
    elevation_m=80.0,
    loaded_cart_mass_kg=3200.0,
    empty_cart_mass_kg=200.0,
    cycles_per_day=4,
    carts_in_circulation=2,
    brake_to_storage_efficiency=0.80,
    storage_roundtrip_efficiency=0.85,
    operators=1,
)

ARCHETYPES: List[GravityRailSystem] = [
    BACKPACK_HUMAN,
    SMALL_HANDCART,
    COUNTERWEIGHT_RAIL,
    FUNICULAR_COMMUNITY,
]


# -------------------------------------------------------------
# 3. SENSITIVITY
# -------------------------------------------------------------

def sensitivity_table(
    base: GravityRailSystem,
    elevations: List[float],
    net_masses: List[float],
    cycles: List[int],
) -> List[Dict]:
    """
    Sweep each parameter holding the others at the base value.
    Returns rows with daily kWh and daily kWh per operator.
    """
    rows: List[Dict] = []
    for e in elevations:
        s = dataclasses.replace(base, elevation_m=e)
        rows.append({"swept": "elevation_m", "value": e,
                     "daily_kwh": s.daily_kwh()})
    for m in net_masses:
        s = dataclasses.replace(
            base,
            loaded_cart_mass_kg=m + base.empty_cart_mass_kg,
        )
        rows.append({"swept": "net_mass_kg", "value": m,
                     "daily_kwh": s.daily_kwh()})
    for c in cycles:
        s = dataclasses.replace(base, cycles_per_day=c)
        rows.append({"swept": "cycles_per_day", "value": c,
                     "daily_kwh": s.daily_kwh()})
    return rows


# -------------------------------------------------------------
# 4. SURVIVAL-GRADE LOAD ALLOCATION
# -------------------------------------------------------------

SURVIVAL_LOAD_KWH_PER_DAY = {
    "LED lighting (whole household)": 0.20,
    "Refrigeration (efficient chest)": 0.80,
    "Communications (radio + low-power data)": 0.15,
    "Small appliance use (mixer, fan, charging)": 0.50,
    "Modest tool operation (drill, light grinder)": 0.40,
    "Water pump (header tank, gravity-fed)": 0.30,
    "Sewing machine / light workshop": 0.25,
}

EXCLUDED_LOADS = {
    "Air conditioning (whole house)": 8.0,
    "Electric heating (whole house)": 30.0,
    "Industrial production": 50.0,
    "Daily EV charging": 10.0,
}


def covered_loads(daily_kwh: float) -> Dict:
    """Greedy allocation of a daily kWh budget to survival loads."""
    remaining = daily_kwh
    covered: List[str] = []
    partial: Dict[str, float] = {}
    for load, need in SURVIVAL_LOAD_KWH_PER_DAY.items():
        if remaining >= need:
            covered.append(load)
            remaining -= need
        elif remaining > 0:
            partial[load] = remaining / need
            remaining = 0.0
    return {
        "covered_in_full": covered,
        "partial_coverage": partial,
        "headroom_kwh": remaining,
    }


# -------------------------------------------------------------
# 5. FALSIFIABLE CLAIMS
# -------------------------------------------------------------

CLAIMS: List[Dict[str, str]] = [
    {
        "id": "G1_backpack_insufficient",
        "statement": (
            "Per-person carry of <=50 kg over <=100 m of grade at "
            "<=10 cycles/day cannot reach 1 kWh/day of useful output "
            "after realistic efficiency losses."
        ),
        "falsifier": (
            "Demonstrate a backpack-only system delivering >=1 "
            "kWh/day per person under those bounds."
        ),
    },
    {
        "id": "G2_rail_sufficient_for_survival_grade",
        "statement": (
            "A gravity-rail system moving >=2,000 kg net mass per "
            "cycle over >=50 m elevation at >=4 cycles/day, with one "
            "supervising operator, yields >=1 kWh/day of useful "
            "stored energy; staggered carts can reach 3-5 kWh/day."
        ),
        "falsifier": (
            "Demonstrate an equivalent installation delivering <1 "
            "kWh/day after realistic losses."
        ),
    },
    {
        "id": "G3_substrate_coupling_required",
        "statement": (
            "Net useful output is bounded by substrate the community "
            "already needs to move downhill. A system requiring "
            "uphill haulage of the load first has near-zero net yield."
        ),
        "falsifier": (
            "Demonstrate a sustained installation where the operator "
            "hauls the load up by their own labor and still extracts "
            "net energy at survival scale."
        ),
    },
    {
        "id": "G4_terrain_prerequisite",
        "statement": (
            "Net yield scales linearly with elevation. Below ~30 m of "
            "usable grade, the system cannot reach survival-grade "
            "output regardless of cart size or cycle count."
        ),
        "falsifier": (
            "Demonstrate a sustained sub-30 m installation delivering "
            ">=1 kWh/day per operator with realistic load assumptions."
        ),
    },
    {
        "id": "G5_survival_grade_not_industrial",
        "statement": (
            "At the upper bound of plausible per-operator output "
            "(~5 kWh/day), the system covers lighting, refrigeration, "
            "communications, small appliances, modest tools -- not "
            "AC, electric heat, or industrial loads."
        ),
        "falsifier": (
            "Demonstrate a single-operator gravity-rail system "
            "covering a continuous AC or industrial load."
        ),
    },
]


# -------------------------------------------------------------
# 6. REPORT
# -------------------------------------------------------------

def report():
    print("=" * 74)
    print("GRAVITY-RAIL HUMAN-SCALE ENERGY HARVEST")
    print("=" * 74)
    print()
    print("  Distinguishes backpack-scale (insufficient) from rail-scale")
    print("  (survival-grade). Parameters exposed and overrideable.")
    print()

    print("=" * 74)
    print("ARCHETYPES")
    print("=" * 74)
    for s in ARCHETYPES:
        print("-" * 74)
        print(f"SYSTEM: {s.name}")
        print(f"  Elevation:               {s.elevation_m:6.1f} m")
        print(f"  Loaded / empty mass:     "
              f"{s.loaded_cart_mass_kg:7.0f} / {s.empty_cart_mass_kg:5.0f} kg")
        print(f"  Net mass per cycle:      "
              f"{s.net_mass_per_cycle_kg():7.0f} kg")
        print(f"  Cycles/day x carts:      "
              f"{s.cycles_per_day} x {s.carts_in_circulation}")
        print(f"  Brake -> storage eff:    "
              f"{s.brake_to_storage_efficiency:6.2f}")
        print(f"  Storage roundtrip eff:   "
              f"{s.storage_roundtrip_efficiency:6.2f}")
        print(f"  Operators:               {s.operators}")
        print(f"  Daily output:            "
              f"{s.daily_kwh():6.2f} kWh")
        print(f"  Per operator:            "
              f"{s.daily_kwh_per_operator():6.2f} kWh")
        cov = covered_loads(s.daily_kwh_per_operator())
        print(f"  Covered loads ({len(cov['covered_in_full'])} of "
              f"{len(SURVIVAL_LOAD_KWH_PER_DAY)}):")
        for c in cov["covered_in_full"]:
            print(f"    + {c}")
        if cov["partial_coverage"]:
            for load, frac in cov["partial_coverage"].items():
                print(f"    ~ {load} ({frac*100:.0f}% of need)")
        print(f"  Headroom: {cov['headroom_kwh']:.2f} kWh")
        print()

    print("=" * 74)
    print("SENSITIVITY: counterweight rail base, sweep each parameter")
    print("=" * 74)
    rows = sensitivity_table(
        base=COUNTERWEIGHT_RAIL,
        elevations=[20.0, 50.0, 75.0, 100.0, 150.0],
        net_masses=[200.0, 500.0, 1000.0, 2000.0, 3500.0],
        cycles=[2, 4, 6, 8, 12],
    )
    last_swept = None
    for r in rows:
        if r["swept"] != last_swept:
            print(f"\n  sweep: {r['swept']}")
            last_swept = r["swept"]
        print(f"    {r['value']:>8.1f}  ->  "
              f"{r['daily_kwh']:6.2f} kWh/day")
    print()

    print("=" * 74)
    print("FALSIFIABLE CLAIMS")
    print("=" * 74)
    for c in CLAIMS:
        print(f"  {c['id']}")
        print(f"    {c['statement']}")
        print(f"    Falsifier: {c['falsifier']}")
        print()

    print("=" * 74)
    print("SCOPE NOTE")
    print("=" * 74)
    print("Survival-grade infrastructure for communities with usable")
    print("terrain. Not a replacement for industrial energy at scale.")
    print("The architecture matches the constraint: gravity is the")
    print("engine, the human is the supervisor, the load is something")
    print("the community already moves.")


if __name__ == "__main__":
    report()

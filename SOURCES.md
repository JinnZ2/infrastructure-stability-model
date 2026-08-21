# SOURCES.md — external literature this model rests on

Every external claim used to parameterize or constrain this model, with what
was actually read.

**Access caveat, stated once and it applies throughout.** The authoring
environment could not retrieve full texts — publisher domains were blocked at
the network layer. Everything below was read as search-result summaries and
abstract-level reporting. Numbers taken from them are order-of-magnitude
inputs, not verified figures, and no value here has been checked against a
primary table. Verifying these against the papers themselves is a listed
roadmap item and a named unknown in ledger `F-015`. Treat a number in this
file as a claim about the literature that has not itself been tested.

-----

## ENSO structure and response to warming

**Non-monotonic ENSO response to warming.** *npj Climate and Atmospheric
Science*, 2026. Under moderate warming, ENSO strengthens with persistent
positive skewness and roughly 4-year periodicity. Under extreme warming,
amplitude and skewness decline while the period shortens to 2-3 years and
Central Pacific events are favored. Simulations extended to 2500.
→ Used for `period_years` (4.0) and `period_under_extreme_warming_years`
(2-3) in `system-model.json` `climate_forcing`, and for rung E of the ENSO
ladder in `sim/sim.py`.
→ **Caution:** rung E takes the shortened period and holds amplitude fixed.
That is the pessimistic half of a non-monotonic result, and it is flagged as
an unknown in `F-015`.

**ENSO amplitude in CMIP6.** No model consensus on a systematic change in the
amplitude of ENSO SST variability across 21st-century SSP scenarios. A robust
increase in ENSO *rainfall* amplitude is found for SSP2-4.5, SSP3-7.0 and
SSP5-8.5 over 2081-2100 relative to 1995-2014.
→ Why the model forces on impact channels rather than on SST amplitude: the
SST signal is contested, the hydrological one less so.

**Central Pacific ENSO predictability under warming.** Robust decrease in
CP-ENSO predictability associated with a strengthening spring predictability
barrier. Read against the study above, the event type that becomes more common
is the one that becomes harder to forecast.
→ Used for the `predictability_note` and for the shrinking-lead caveat on the
`enso_phase_and_forecast_lead` metric in `measurement.json`.

**Countervailing evidence on predictability.** Deep-learning approaches report
substantial reduction of the spring barrier — one 2026 result claims skillful
prediction to 16 months when initialized in spring using tropical basin
interactions; another improves multiyear La Niña prediction using a sea
surface temperature range index.
→ Recorded because it cuts against the previous entry. The direction of
forecast lead under warming is contested and the schema says so rather than
picking the alarming side.

-----

## Economic and infrastructure persistence

**Callahan & Mankin, "Persistent effect of El Niño on global economic
growth," *Science*, 2023.** Country-level growth depressed for at least five
years after an event, with a tail reported out to fourteen. Attributes $4.1T
and $5.7T in global income losses to the 1982-83 and 1997-98 events. US GDP
roughly 3% lower in 1988 and 2003 than counterfactual; coastal tropical
economies such as Peru and Indonesia more than 10% lower in 2003.
→ **This is the load-bearing citation.** Recovery time (5-14 years) exceeds
the recurrence interval (2-7 years, trending shorter). The system does not
return to baseline between events, so stress accumulates rather than
resolving. It is what falsified the 3-month recovery in the committed shock
model. Used for `recovery_years` (5.0) and `persistence_years` [5, 14].

**1997-98 event damages.** Roughly $36 billion in infrastructure damage and
more than 20,000 deaths.
→ Order-of-magnitude anchor for `Em_surge` (0.25).

-----

## Energy throughput channel (E)

**Photovoltaic power response to ENSO.** *Communications Earth &
Environment*, 2026. El Niño reduces surface solar irradiance, producing
sustained solar energy deficits in California, the southern Atacama, the Chaco
Basin, the Middle East and East China. Effects pronounced during Super El Niño
events, lowering PV generation and increasing fossil backup.

**ENSO and solar irradiance.** Small variation in summer; more than 10%
variation in some locations in winter.

**ENSO and global hydropower.** More than one third of simulated dams show
statistically significant annual energy production anomalies in at least one
ENSO phase. Aggregated globally, positive and negative anomalies cancel,
leaving a weak and statistically insignificant net global anomaly.
→ Used for `E_deficit` (0.08), and — more importantly — for the
`aggregation_warning`. This is independent confirmation, from a different
domain, of the failure mode this repo already recorded twice: a global
aggregate reads as approximately zero while a third of the individual assets
are significantly stressed. Compare ledger `F-002`, `F-003`, `F-016`.

-----

## Labor channel (L_f)

**ILO heat-stress projection.** 2.2% of total global working hours lost to
high temperatures by 2030, with agriculture (60%) and construction (19%)
carrying most of the loss.

**Occupational heat stress in vulnerable regions.** Reductions of up to 80% in
labor-intensive outdoor activity reported for parts of Southeast Asia, Latin
America and Sub-Saharan Africa. A Southern India study found elevated WBGT
associated with a 1.4-fold increased risk of productivity loss.
→ Used for `L_deficit` (0.06). The model's maintenance labor is outdoor and
physical, so it sits in the exposed category rather than the global average.
→ **Gap:** these are climate/heat studies, not ENSO studies. The link runs
through El Niño years being the warmest years, which is an inference this
repository is making, not one the cited work states.

-----

## Spatial correlation

**Changing risks of simultaneous global breadbasket failure.** *Nature Climate
Change*, 2019, and follow-on work. ENSO, the Indian Ocean Dipole and the North
Atlantic Oscillation shift the relative probability of simultaneous yield
shocks in *pairs* of breadbaskets by 20-40% for maize and wheat. Spatial
dependence between climatic extremes can mitigate or aggravate global risk
depending on the correlation structure.
→ Used for `spatial_correlation`. The mechanism that correlates crop failures
across continents correlates infrastructure stress the same way.
→ **Not yet modelled.** `sim/sim.py` is single-region, so the 20-40% figure
constrains nothing in code today. Listed as a roadmap item and as an unknown
in `F-015`.

-----

## The 2026 event

An El Niño was declared by NOAA on 11 June 2026 — early in the year, and soon
after the 2023-24 event. Forecasts drawing on 650+ simulations put the
expected peak near +3.6 °C in Niño3.4, which would exceed the highest defined
intensity category. PIIE analysis puts the global drag in the hundreds of
billions to trillions of dollars depending on response.

→ Not used to parameterize anything. Recorded because the short gap since the
previous event is a direct instance of the recurrence-shorter-than-recovery
structure that `F-015` is about, and because a live event is the obvious
opportunity to test predictions rather than assert them.

-----

## Provenance fields required for every ingested number

`METHOD.md` sets out four checks for reading someone else's result. This is
where the answers get recorded. Every number entering a schema needs these,
and **none of the entries above currently has all of them** — that gap is
itself a finding, and shrinking it is a roadmap item.

| field | why it matters |
|---|---|
| `reference_period` | An anomaly is a difference from a baseline. 1991-2020, 1951-1980 and pre-industrial give materially different magnitudes for the same physical state, because a later baseline absorbs prior warming into the "normal". A smaller anomaly number may be a later baseline, not a smaller anomaly. |
| `depth_or_dimension` | Surface-only cannot show a subsurface structure. If the phenomenon is a decoupling between layers, a single-layer measurement is not weak evidence, it is no evidence. |
| `spatial_scope` | Regional or global mean, and if global, whether the regional signal survives the averaging. This repository has been caught by aggregation four times from the inside. |
| `instrument_era` | Long records are stitched across joins, and the joins are where artefacts live. |
| `compared_against` | "Not that bad" relative to worst-case projections is a different claim from "not that bad" relative to pre-industrial. For a regime-change question only the second is informative. |

### Instrument joins to check before using a trend across one

- **Bucket to engine-intake SST.** Introduced a known warm bias, corrected
  differently by different groups. Trends spanning the join inherit whichever
  correction the dataset chose.
- **XBT to Argo.** Changed depth coverage, spatial coverage and temporal
  resolution *simultaneously*, so no single correction isolates one of them.
- **Satellite era onset.** Surface-only, at a different spatial resolution
  from the in-situ record it continues, so what gets averaged changes at the
  join.
- **Argo depth range.** Nominally 0-2000m. A subsurface anomaly at 50-150m is
  well inside that, but check whether *that stratum specifically* was sampled
  consistently across the full record rather than assuming the nominal range
  implies uniform coverage.

The general rule: a change in instrument is a change in the measured
quantity, and a trend across a join is a claim about both.

-----

## How to use this file

If you change a number in `system-model.json` `climate_forcing`, change the
corresponding entry here and say what you read. If you verify one against a
primary source, record that — the access caveat at the top is the current
state, not a permanent one, and it should shrink.

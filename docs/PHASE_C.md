# Phase C — extend and improve

## C1 — multi-country ingestion

### What changed, in plain words
* **One list of inputs.** [`pipeline/manifest.csv`](../pipeline/manifest.csv) says, for every FIRMS request id, which
  country it belongs to (ISO3 code) and its role: `train` (KZ), `test` (UZ), `stress` (TM), `extra` (KG, TJ),
  `exclude` (the UZ bounding-box backup), `transfer` (PRT, AUS, BRA, USA, IND — confirmed by you from
  `python -m pipeline.inventory`, which lists any zip not in the manifest with rows, dates, bbox and a guessed country).
  A zip that is not in the manifest is never read; a manifest id without a zip, or the same id twice, stops the run.
* **Every table has a `country` column**, and countries are processed one at a time, so nothing can be merged by
  accident: `data/processed/hotspots/country=XXX/…`, `data/aggregated/cell_month_all.parquet` (country, cell, month),
  `data/aggregated/country_month/XXX.parquet`, `data/reference/static_mask/XXX.parquet`,
  `reports/cleaning_summary.json` (one block per country).
* **Two output levels.** Central Asia (train/test/stress/extra) keeps cell-level data (maps, regions). The five
  transfer countries keep **country-month totals only**: their cleaned points live in a temporary DuckDB file outside
  OneDrive and are deleted as soon as the totals are written.
* **No per-row Python loops.** Cleaning is SQL in DuckDB ([`pipeline/ingest.py`](../pipeline/ingest.py)); H3 cells come
  from DuckDB's `h3` extension (same H3 library as before — checked on the same point). CSVs are streamed out of the
  zips in 1-million-row chunks, so memory stays flat whatever the file size; DuckDB spills to disk above 4 GB.
* **One implementation of the cleaning rules.** The old pandas functions are now thin wrappers over the same SQL, so
  Elbek's unit tests test the new code. New test: the fast country-month query equals the sum of cell-months.

### Regression check (KZ must not move)
`python -m pipeline.regression_check` compares with the Phase B snapshot in `reports/phase_b/`:
cleaning steps, hotspots per satellite-year, yearly sums of all 25 cell-month columns, country-month = Σ cell-month,
and every number in `metrics.json`, `model_comparison.json`, `model_selection.json` (relative tolerance 1e-9).
**Result: identical.** Tests: 31 passed.

### Speed (this laptop)
| step | before (KZ only) | now |
|---|---|---|
| clean | 40 s | 38 s for all 5 Central Asian countries |
| grid | 15 s | 28 s for all 5 |
| transfer countries | impossible (all rows in pandas memory) | PRT 4 s, IND 2.5 min, USA 4 min, AUS 15.5 min, BRA 25 min |

### What the data look like (all countries, same cleaning rules)
| country | role | raw rows | kept | % kept | removed as `type≠0` | NRT rows removed by mask | first – last |
|---|---|---|---|---|---|---|---|
| KAZ | train | 3,919,557 | 3,171,270 | 81% | 482,852 | 13,750 | 2000-11 – 2026-11 |
| UZB | test | 568,405 | 311,155 | 55% | 207,251 | 6,078 | 2000-11 – 2026-11 |
| TKM | stress | 786,454 | 305,188 | **39%** | 425,545 | 22,017 | 2000-11 – 2026-11 |
| KGZ | extra | 71,790 | 42,112 | 59% | 24,439 | 647 | 2000-11 – 2026-11 |
| TJK | extra | 27,448 | 16,280 | 59% | 8,884 | 453 | 2000-11 – 2026-11 |
| PRT | transfer | 278,864 | 256,569 | 92% | 9,287 | 312 | 2000-11 – 2026-11 |
| IND | transfer | 18,036,968 | 13,261,137 | 74% | 1,830,467 | 56,619 | 2000-11 – 2026-11 |
| USA | transfer | 17,311,429 | 13,936,929 | 81% | 2,460,603 | 99,532 | 2000-11 – 2026-11 |
| AUS | transfer | 39,548,554 | 35,591,968 | 90% | 410,418 | 9,657 | 2000-11 – 2026-11 |
| BRA | transfer | 46,426,727 | 42,020,892 | 91% | 625,423 | 13,439 | 2000-11 – 2026-11 |

Turkmenistan loses 61% of its rows to `type≠0` — the gas flares we expected; it is the right stress test for C2.

**First look at transfer (2013–2019, VIIRS S-NPP ÷ MODIS):**

| country | cell-days ratio | points ratio |
|---|---|---|
| PRT | 1.58 | 2.75 |
| KAZ | 1.81 | 3.35 |
| AUS | 2.03 | 4.56 |
| USA | 2.18 | 3.59 |
| BRA | 2.48 | 3.82 |
| KGZ | 3.46 | 4.08 |
| TJK | 3.88 | 4.49 |
| UZB | 3.95 | 4.62 |
| TKM | 4.20 | 5.07 |
| IND | 4.54 | 5.79 |

The ratio depends on the kind of fires: large steppe/forest fires (KZ, PRT, AUS) need a small correction; many small
agricultural burns (UZ, TM, IND, KG/TJ) need a large one, because VIIRS' finer pixels catch fires MODIS misses.
**This already tells us the KZ coefficients will not transfer as-is to Uzbekistan or India** — C4 will measure how
badly, and whether a local refit fixes it.

### Not done yet / known
* ~~The S-NPP outage threshold is one number for all countries~~ — fixed after C1, see "Outage threshold per country".
* `data/raw/modis/` (yearly MODIS zips) is not used.

## Outage threshold per country (asked at C1 review)

An S-NPP "outage day" = S-NPP reported nothing while NOAA-20 saw at least *threshold* detections in the same country
(so S-NPP was off, not "no fires"). One fixed threshold (20) is right for Kazakhstan but means "never" for Kyrgyzstan
(a typical day has 2 detections) and "almost always" for Australia (2,228). Now:

`threshold = max(5, round(20 × typical_c / typical_KAZ))`, typical = median daily NOAA-20 detections on days with
at least one detection, since 2018-04-01 (`config.yaml: outage`). Kazakhstan is unchanged (20), so Phase B is unchanged.

| country | typical day | threshold | outage days |
|---|---|---|---|
| KAZ | 87 | 20 | 56 |
| UZB | 18 | 5 | 64 |
| TKM | 18 | 5 | 64 |
| KGZ | 2 | 5 (floor) | 20 |
| TJK | 2 | 5 (floor) | 29 |
| PRT | 4 | 5 (floor) | 60 |
| IND | 653 | 150 | 27 |
| USA | 758 | 174 | 61 |
| AUS | 2,228 | 512 | 62 |

The floor of 5 stops one stray detection from declaring an outage. Most countries land on 55–65 days, as expected:
S-NPP outages are satellite-wide, so they should be the *same days* everywhere (cross-check below).

**Cross-check** (`pipeline/outage_check.py` → `reports/outage_check.json`). S-NPP outages hit the whole satellite,
so a real outage day must be an outage everywhere. Reference: 59 "global" days since 2018-04 where S-NPP saw nothing
in any of 9 countries while NOAA-20 saw fires in at least half of them (Brazil was still re-ingesting). For each
country, "found" = how many global days its rule catches, "true" = how many of its outage days are global:

| country | fixed 20: days / found / true | per country: days / found / true |
|---|---|---|
| KAZ | 56 / 88% / 93% | same (threshold 20) |
| USA | 61 / 100% / 97% | same |
| UZB | 27 / **39%** / 85% | 64 / **90%** / 83% |
| TKM | 37 / **51%** / 81% | 64 / **86%** / 80% |
| AUS | 65 / 100% / 91% | 62 / 95% / 90% |
| IND | 49 / 78% / 94% | 27 / **46%** / 100% |
| PRT | 14 / 22% / 93% | 60 / 42% / **42%** |
| KGZ | 1 / 2% / 100% | 20 / 14% / **40%** |
| TJK | 0 / 0% / — | 29 / 7% / **14%** |

What this says, honestly:
* **Works** for mid-size countries: UZ and TM now catch ~90% of real outages instead of 40–50%, without more
  false ones. KZ/USA unchanged; AUS about the same.
* **Too strict for India**: fires there are very seasonal, so the "typical fire day" (653) is a peak-season number;
  off-season outages have fewer NOAA-20 detections than 150 and are missed.
* **Cannot work for tiny countries** (KGZ, TJK, PRT): with 2–4 detections on a typical day, "S-NPP 0 while NOAA-20 ≥ 5"
  happens by chance (different overpass times, clouds), so 60–86% of their "outage days" are fake. No threshold fixes
  this — there is too little signal per country.

**Recommendation (not applied, needs your OK):** since outages are satellite-wide, use the global outage-day list
(computed from all countries together) for every country, and keep the per-country rule only as a fallback for dates
before the global list or when a country is processed alone. Impact today is small: KGZ/TJK are totals-only (annual
check in C4), PRT is transfer-only, and the train/test countries (KZ, UZ, TM) are already close to the global list.

## C2 — static-source mask, honest test

Question: FIRMS NRT has no `type` column (gas flares / industry = type 2), so for recent data we drop "static" cells
with our own mask. Does that mask work on data it has never seen?

Method (`pipeline/static_mask_check.py`, report `reports/static_mask_check.md`): build the mask **only from archive
rows before 2025-01-01**, then test on archive rows 2025-01 … 2026-07, where the true `type` is known.

| country | precision | recall | what that means |
|---|---|---|---|
| KAZ | 88.6% | 96.1% | catches almost all flares; ~1 in 9 masked detections was a real fire |
| UZB | 84.2% | 76.4% | misses a quarter of type-2 detections (see below) |
| TKM | 82.3% | 95.0% | good recall, but 1 in 6 masked detections was a real fire |

If the mask **replaced** `type` (monthly cell-day totals, 2025-01…2026-07): KAZ −3% (S-NPP, median month 7%),
TKM −18% (VIIRS: the "persistent" rule removes real recurring agricultural fires), UZB MODIS +35%.

**Finding — a new heat source in Uzbekistan.** The UZB miss is not a mask bug: a site near 38.1°N 67.3°E starts in
2025 (14,644 VIIRS detections in 2025–26). It did not exist before 2025, so no mask built from history can know it.
FIRMS itself disagrees between sensors there: MODIS calls 78% of it type 2, VIIRS 92% type 0. It passes the VIIRS type
filter and inflates UZ 2025–26 VIIRS counts — C4 must keep this in mind (UZ test period).

**Recommendation (not applied — it would change KZ cleaning counts, so it needs your OK):** use only the "type-2
share" rule (precision 92% on KZ, totals within ±2%, TKM −6% instead of −18%) and rebuild the mask from the most
recent years on every data refresh, so new sites like the Uzbek one are picked up.

## C3 — regions, intervals at the right level, one source of truth

### ADM1 per cell (`pipeline/regions.py`)
Each H3 cell gets an oblast from `data/boundaries/{ISO3}_ADM1.geojson`: centre inside a polygon → that region; else
the nearest region within 10 km (border rivers, simplified coastlines); else `outside`. KZ: 240,798 inside,
1,217 nearest, 24 outside (`reports/adm1_assignment.json`). Columns `adm1_id/adm1_name/adm1_method/adm1_dist_km` are
in `cell_month_all.parquet`. Leave-one-region-out (T3) now uses real oblasts, not H3 res-1 hexagons, and counts
months with zero fires too.

### The interval bug and the fix (`pipeline/intervals.py`)
The baseline sized the 90% interval by the **country** prediction and then applied it to any area. A country month
of 2,000 cell-days has a small relative error; an oblast month of 30 does not. Result: only **44%** of region-months
fell inside the "90%" interval.

Fix — size the interval at the level being predicted (conformal: edges = percentiles of real held-out errors):
* **country**: as before (leave-one-year-out errors, relative width shrinks with size);
* **region**: leave-one-region-out errors `log(1+actual) − log(1+pred)`, percentiles computed **separately for
  predictions of similar size** (bins 0, ≤5, 5–20, 20–100, 100–500, >500 cell-days/month; `config.yaml: intervals`).

All coverage numbers are cross-fitted: the interval for a held-out region is fitted on the *other* regions only.

| test | before | after |
|---|---|---|
| T3 leave-one-region-out, all region-months | 44% | **91%** |
| median region | 46% | 95% |
| worst regions (Kyzylorda, Aktobe, Mangystau) | 16–29% | 73–74% |
| T1 backcast, country | 94% | 94% |
| T2 holdout 2020+, country | 83% | 83% (drift, see Phase B) |
| T4 leave-one-year-out, country | 90% | 90% |

**Finding — small predictions are biased low.** 504 of 1,536 region-months have prediction 0 (MODIS saw nothing),
yet VIIRS saw fires in 56% of them; the interval edges for small predictions are shifted up (a "0" prediction gets
[0, 14]). This is physics, not a bug: VIIRS' 375 m pixels see small fires MODIS cannot — the same reason the
VIIRS/MODIS ratio is higher in small-fire countries (C1 table). The interval reports it honestly.

### One source of truth
`experiments.py` (model selection) writes `reports/model_card.json`: selected model, its link/columns, production
name, train country, test scores, the single LORO number and both interval parameter sets. `05_calibrate`,
`06_harmonize`, `07_validate` read it; `config.yaml` no longer has `selected_model` / `interval_method` (deleted, so
nobody can hand-type a different one). 06 refuses to run if the card and the fitted model disagree. The per-region
error is computed once (experiments T3) and 07 reads it: **18.5%** median MAE over the 13 oblasts with ≥1% of MODIS
activity — the same number in `model_card.json`, `model_comparison.md` and `validation.md`.

Selected: **C2 — Terra∪Aqua, Poisson log-link** (score 10.63: T1 6.9%, T3 18.5%, T4 6.5%; C1 10.97, C0 11.79).

### Per-region error (KZ, leave-one-region-out 2012–2019, selected model)

| region | share of MODIS | MAE % | bias % | coverage before → after |
|---|---|---|---|---|
| Kostanay | 12.7% | 10.0 | +0.2 | 67% → 97% |
| Karaganda | 12.2% | 12.9 | +2.3 | 49% → 95% |
| North Kazakhstan | 12.2% | 10.2 | +2.6 | 60% → 96% |
| Akmola | 10.4% | 12.0 | +5.5 | 64% → 100% |
| Kyzylorda | 10.1% | 21.8 | +1.5 | 29% → 73% |
| Almaty Region | 8.3% | 13.0 | −4.0 | 58% → 97% |
| Aktobe | 7.7% | 18.5 | −15.1 | 23% → 74% |
| East Kazakhstan | 7.7% | 14.1 | −1.3 | 52% → 91% |
| West Kazakhstan | 6.0% | 19.9 | +13.5 | 36% → 97% |
| Pavlodar | 4.2% | 20.9 | −15.2 | 21% → 92% |
| Jambyl | 3.8% | 18.9 | +6.7 | 44% → 91% |
| South Kazakhstan | 2.5% | 24.3 | −7.4 | 49% → 91% |
| Atyrau | 2.1% | 24.8 | −7.6 | 32% → 95% |
| Mangystau* | 0.1% | 84.2 | −83.2 | 16% → 74% |
| Almaty city* | 0.0% | 84.9 | −82.8 | 35% → 100% |
| Astana city* | 0.0% | 70.7 | −48.4 | 65% → 99% |

\* < 1% of activity: shown, not in the median (a few fires a year; percentage errors are meaningless there).
The geoBoundaries file has the 16 pre-2022 units (no Abai/Jetisu/Ulytau) — fine for 2012–2019.

### Regression
KZ ingestion, cleaning, hotspots, cell-months, and T1/T2/T4 of all 8 candidate models: identical to Phase B.
Changed by design (excluded in `regression_check.py`): LORO and intervals. 36 tests pass.

## After the C3 review: both recommendations applied

### Satellite-wide S-NPP outage days (`pipeline/outage.py`, step `02b_outage`)
An outage is a property of the satellite, so there is now **one list for all countries**, built from all 10
combined: a UTC day is an outage when S-NPP has ≤ 1% of NOAA-20's detections summed over all countries (and NOAA-20
has ≥ 500). Result: **61 days** (59 with exactly zero S-NPP, 2 with < 0.4%); 9 partial-data days (S-NPP at 7–28%)
are deliberately not counted. NOAA-20 fills only cells S-NPP did not see that day. Totals-only countries get the fill
from a new `country_day.c_noaa20_only` column, so no second pass over 20–50 M points is needed (a test checks that
both routes give identical numbers). How the old per-country rules compare with the global list
(`reports/outage_check.json`): KZ/USA/AUS/BRA catch 89–100% of real outage days with either threshold; the per-country
threshold helped UZ/TM (found 38→90%, 56→92%) but produced mostly false days in KGZ/TJK/PRT (true 13–43%) and missed
India's off-season outages (found 77→44%).

### Static-source mask: type-2 rule only, rebuilt from the last 5 years (`config: cleaning.static_mask`)
Honest test unchanged (built only from rows before 2025-01-01, tested 2025-01…2026-07):

| country | precision / recall, new | precision / recall, C2 mask | total change if mask replaced `type` (S-NPP), new vs C2 |
|---|---|---|---|
| KAZ | 93.9% / 88.4% | 88.6% / 96.1% | +2.1% vs −3.1% |
| UZB | 94.0% / 74.7% | 84.2% / 76.4% | +5.2% vs +0.3% |
| TKM | 86.1% / 84.5% | 82.3% / 95.0% | −3.9% vs −18.5% |

Trade-off: fewer real fires removed (precision up 4–10 points, Turkmenistan's distortion −18% → −4%), some flares
missed (recall down). **The new Uzbek source (38.1°N 67.3°E) is not caught by any mask rule, not even the production
mask built from data through 2026**: FIRMS labels 92% of its VIIRS detections type 0 (vegetation fire), so no rule
built on FIRMS `type` can flag it. It stays a documented caveat for Uzbekistan 2025+.

### Kazakhstan: what moved (`reports/kz_before_after.md`)
Hotspots after cleaning 3,171,270 → 3,172,931 (+0.05%: the smaller mask, 189 → 91 cells, removes 1,661 fewer NRT
rows in 2025–26); every model metric identical to Phase B except holdout bias −2.21% → −2.18%; LORO and coverage
changed in C3 (ADM1 regions, region intervals). The regression reference is now the snapshot `reports/phase_c4`.

## C4 — validation package (`pipeline/07b_validation_package.py` → `reports/VALIDATION.md`, `reports/validation.json`)

Headline results (details and plain-language takeaways per test in `reports/VALIDATION.md`):

* **Uzbekistan, independent test.** 2012 jump: naive ×4.88 → KZ-harmonized ×1.77 → locally refitted ×1.15 (MODIS
  alone ×1.35). KZ model as-is: 35.5% monthly error, −32% bias; local refit: 17.7%, −0.4%.
* **Turkmenistan, stress test.** 57% of confident detections are static sources (KZ 13%). Jump ×4.75 → ×1.66 (KZ)
  → ×1.02 (local). As-is 42% error / −35% bias; local 23%.
* **Kyrgyzstan / Tajikistan, annual totals.** Annual error 9% / 20%, bias −6% / +20% (raw MODIS −72% / −76%).
* **Transfer table (10 countries).** KZ coefficients transfer only to KZ-like regimes (KGZ). Observed VIIRS/MODIS
  ratio ranges ×1.58 (Portugal) to ×4.46 (India); KZ as-is errs in the direction of the difference (PRT +59%,
  IND −65%, BRA −52%, AUS −33%, USA −27%). Refitted locally the same model gets 5–37% (big countries 5–9%).
  **The method transfers across biomes; the coefficients do not.**
* **Burned area.** With burned area held fixed, the naive series jumps ×2.2–×5.8 at 2012 in all five countries.
  KZ-harmonized is continuous only in KZ (×1.16, CI 0.88–1.53); **locally harmonized is continuous in UZ (×1.00),
  TM (×1.01), TJ and KZ** — independent evidence that the harmonization works when coefficients are local.
* **Events.** Region-month z-scores failed (see `docs/DECISIONS.md` #16). Excess cell-days per H3 res-4 hexagon:
  Abai June 2023 = 123 cell-days vs a normal of 0, **rank 242 of 1,255** — not #1. Kostanay Sept 2022: rank 412.
  Honest reading: in detection counts a forest fire is not exceptional next to Kazakhstan's steppe/farm burning
  (top events: Kyzylorda 2003-04, Karaganda 2005-07, West KZ 2001-07). Abai stands out by intensity (FRP), land
  cover (pine forest) and impact, which a count-based product does not measure. It is in `anomalies.json` for the
  demo as a known event.

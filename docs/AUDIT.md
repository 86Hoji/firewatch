# Audit of the baseline (Elbek's `fire-regimes`)

Imported as-is in commit `import baseline from Elbek (fire-regimes)`. Nothing in `pipeline/`, `api/`, `tests/` or
`config.yaml` has been changed yet. This document explains what the code does, where it is tied to Kazakhstan,
what is fragile, and what we must change in Phase B (reproduce) and Phase C (extend).

Author's own summary of results: [`BASELINE_README.md`](BASELINE_README.md). His reports: [`../reports/baseline/`](../reports/baseline/).

---

## 1. The idea in plain words

* MODIS (2000–today, 1 km pixels) and VIIRS (2012–today, 375 m pixels) both detect fires from space, but VIIRS sees
  **~3× more hotspots** for the same fires. Gluing the two records together naively makes fire activity "jump" in 2012.
* Step 1 of the fix is **not to count dots**. The country is cut into H3 hexagons (resolution 7, ≈5 km²). A hexagon
  that has at least one detection on a given day counts as **one "cell-day"**. Counting cell-days instead of dots
  already removes about half of the resolution gap (naive jump ×2.81 on dots → ×1.63 on cell-days).
* Step 2: in the years when **both** sensors fly (2012–2019) we learn, month by month, how many VIIRS S-NPP
  cell-days correspond to a given number of MODIS cell-days. Then we apply that translation **backwards** to
  2000–2011, when only MODIS existed. From 2012 on, the series is VIIRS S-NPP itself.
* Step 3: prove it works on data the model never saw: other years (holdout, backcast), other parts of the country
  (leave-one-region-out), and whether the 2012 jump disappears.

## 2. The pipeline, step by step

Run order is fixed in `pipeline/run_all.py`:
`01_download → 02_clean → 03_grid → 04_landcover → 04b_burned_area → experiments → 05_calibrate → 06_harmonize → 07_validate`.
All steps read `config.yaml` through `pipeline/common.py::load_config()`; folder constants (`data/raw`,
`data/processed`, `data/aggregated`, `data/reference`, `reports`) are hardcoded in `common.py`.

| step | what it does | reads | writes |
|---|---|---|---|
| `01_download.py` | Downloads FIRMS **per-country yearly CSVs** (`firms.modaps.../data/country/{product}/{year}/{product}_{year}_Kazakhstan.csv`), then the current-year "tail" via the FIRMS API by **bbox** (needs `FIRMS_MAP_KEY`), then ADM1 boundaries from geoBoundaries. | internet, `.env` | `data/raw/archive/**.csv`, `data/raw/api/*.csv`, `data/reference/regions.geojson`, `reports/download_summary.json` |
| `02_clean.py` | Loads **every** CSV under `data/raw/` into one pandas table; unifies MODIS/VIIRS columns; maps satellite codes to platforms (Terra, Aqua, SNPP, NOAA20, NOAA21); marks SP vs NRT from `version`. Filters, in order: unknown platform → confidence (MODIS ≥ 30, VIIRS nominal/high) → assigns H3 cell → builds static-source mask → drops `type ≠ 0` (volcano, static land source, offshore) → drops NRT rows (no `type`) in masked cells → exact duplicates → NRT rows on days that already have SP data for the same satellite. | `data/raw/**/*.csv` | `data/processed/hotspots/` (parquet, partitioned by sensor/year), `data/reference/static_mask.parquet`, `reports/cleaning_summary.json` |
| `03_grid.py` | With DuckDB, aggregates to **cell-month** rows: for each sensor group (`modis`, `modis_terra`, `modis_aqua`, `viirs_snpp`, `viirs_noaa20`, `viirs_all`) the number of distinct days with detections (`n_*`), day/night splits (`n_*_d`, `n_*_n`) and raw point counts (`p_*`). Detects **S-NPP outage days** (zero S-NPP but ≥ 20 NOAA-20 detections country-wide) and counts NOAA-20 cell-days on them (`n_viirs_noaa20_gap`). | hotspots parquet | `data/aggregated/cell_month.parquet`, `reports/raw_series.png` |
| `04_landcover.py` | Optional. IGBP land-cover class per cell from one MCD12C1 HDF file. **Did not run** (no file) → strata are month/season/country only. | `data/reference/MCD12C1*.hdf` | `landcover_cells.parquet` |
| `04b_burned_area.py` | Optional. Monthly burned area from MCD64A1 HDF tiles inside the country polygon. **Did not run** (no tiles). | `data/reference/mcd64a1/*.hdf` | `burned_area_monthly.parquet` |
| `experiments.py` | **Model selection.** 8 candidate models (ratio, OLS on log, Poisson log-link; Terra∪Aqua vs Aqua-only; day/night split), scored on monthly country totals by 4 tests: T1 backcast (fit 2016–19 → predict 2012–15), T2 forecast 2020–2025 (reported only), T3 leave-one-region-out, T4 leave-one-year-out. Score = mean MAE% of T1, T3, T4. Then chooses an interval method. Uses `pipeline/models.py`. | `cell_month.parquet` | `reports/model_comparison.{md,json}` |
| `05_calibrate.py` | **Production fit**, with `pipeline/calib.py` (a second, separate implementation). Fits 3 coefficient sets: (a) Terra→Terra∪Aqua on 2003–2011, to scale the Terra-only months Nov 2000–Jun 2002; (b) NOAA-20→S-NPP on 2018–2019, to fill S-NPP outage days; (c) the main MODIS→S-NPP model on 2012–2019, for each of `ratio`, `loglog`, `poisson_log`. Strata: month → season → whole country fallback. 1000 bootstrap draws over years give coefficient CIs; leave-one-year-out residuals give 90% prediction intervals. Reports the 2020+ holdout. **The model actually used is whatever `calibration.selected_model` in config says** (`poisson_log`). | `cell_month.parquet` | `coefficients.parquet`, `coefficient_draws.parquet`, `reports/model_selection.json` |
| `06_harmonize.py` | Applies the coefficients: years < 2012 → `n_harm` = calibrated MODIS (`source = MODIS_calibrated`); 2012+ → `n_harm` = S-NPP + NOAA-20 outage fill (`source = VIIRS_SNPP`). Adds `n_harm_low/high` (prediction interval) and `n_harm_ci_low/high` (bootstrap CI). | coefficients + `cell_month.parquet` | overwrites `cell_month.parquet`, writes `meta.json` |
| `07_validate.py` | All validation: holdout 2020–2025, leave-one-region-out over 2012–2025 (H3 res-1 "subregions"), the 2012 jump (annual step ratios, Pettitt test, monthly step regression with Newey-West CI), peak-month agreement, a synthetic recovery test, burned area (skipped), two known Kazakh fire events. | everything above | `reports/validation.md`, `reports/metrics.json`, PNG figures |
| `fetch_mcd64a1.py` | Helper to download MCD64A1 tiles with an Earthdata login. Not part of `run_all`. | `urls.txt` (not in repo) | HDF tiles |

**The model (poisson_log, "C2").** For each calendar month, E[VIIRS] = exp(a)·(MODIS+1)^b, fit by Poisson maximum
likelihood on the 8 yearly values (2012–2019) of **country-wide monthly totals**. For a single hexagon, the code computes the
multiplier from the **country total** for that month and multiplies the hexagon's own MODIS count by it. So all
hexagons in a given month are scaled by the same factor. The map keeps the MODIS spatial pattern and only the
level changes.

**How to run end-to-end (his way):** `python -m pipeline.run_all` (or `make pipeline`); single steps:
`python -m pipeline.run_all 05 06`; API: `python -m uvicorn api.main:app --port 8000`; tests: `python -m pytest -q`.
His run: steps 05–07 took ~16 min; a second `07_validate` run took **2 h 43 min** (`reports/baseline/validate_run.log`),
almost all of it leave-one-region-out.

**API (`api/main.py`)** — FastAPI + DuckDB over `cell_month.parquet` and the hotspot parquet. Areas (GeoJSON, bbox,
point+radius, ADM1 region id) → H3 cells by centre-in-polygon → calendar / anomaly / yearly / seasonal / CSV export /
map layers. One region per deployment.

## 3. `config.yaml`, key by key

| block | keys | used by | note |
|---|---|---|---|
| `region` | `name`, `firms_countries`, `bbox`, `iso3` | 01 (download URLs, API bbox, geoBoundaries), 04b (pre-filter), 06 (meta) | **single country**, Kazakhstan |
| `years` | `start`, `end` | 01 | |
| `download` | URLs, product names, start years, NRT sources, retries | 01 | irrelevant once we read local zips |
| `cleaning` | MODIS min confidence 30, VIIRS keep n/h, `keep_type: 0`, `static_mask.*` | 02 | |
| `grid` | `h3_res: 7`, `coarse_res: 5` | 02, 03, API | |
| `calibration` | period 2012–2019, holdout 2020+, `min_count`, bootstrap (1000, seed 42), Terra-only cut 2002-06, Terra/Aqua period 2003–2011, NOAA-20 period 2018–2019, outage threshold 20, 90% level, `models`, `selected_model`, `interval_method` | 05, 06, 07, experiments | `selected_model` / `interval_method` are **typed in by hand**, not read from `experiments.py` output |
| `validation` | jump windows 2009–11 vs 2012–14, LORO H3 res 1 + 3% merge rule, `known_events` (Kazakh bboxes) | 07, experiments | |
| `api` | limits, base period start | API | |

Not in config (hardcoded in code): the sensor groups and the S-NPP-only target (`03_grid.py`), season definitions
(Northern Hemisphere DJF/MAM/JJA/SON, `common.py`), test windows T1 2016–19→2012–15 and T3/T4 periods
(`experiments.py`), 2003 start of the monthly step regression (`07_validate.py`), data folder names (`common.py`),
the `web/` folder mount (`api/main.py`).

## 4. Kazakhstan-only and hardcoded assumptions

1. **One country per run.** No `country` column anywhere. `02_clean` globs `data/raw/**/*.csv` recursively, so
   files from several countries in `data/raw/` would be **silently merged into one "country"**.
2. **Input = FIRMS yearly country CSVs + API by bbox.** No support for our FIRMS archive-download **zips**
   (`fire_archive_*.csv` + `fire_nrt_*.csv`), no manifest of request ids.
3. `region.bbox`, `iso3`, `known_events` bboxes are Kazakh. The USA box crosses the 180° meridian, which the
   `[w,s,e,n]` convention cannot express.
4. **Outage threshold 20 NOAA-20 detections country-wide** is tuned to Kazakhstan's size. In Kyrgyzstan/Tajikistan
   (~10–30 detections per day at most) outages will almost never be found; in Brazil/Australia a day with zero S-NPP
   detections country-wide is very rare, but when it happens the threshold is meaningless. Should scale with country size.
5. **Calibration years 2012–2019 and holdout 2020+** are global choices (valid anywhere), but the Terra-only bridge
   (Nov 2000–Jun 2002) and `min_count: 50` are tuned for a country with ~10⁴–10⁵ cell-days per year. KG/TJ
   (~1000×smaller) will fall back to the coarsest stratum and get very wide intervals; Brazil (~100× bigger) could
   afford land-cover or ADM1 strata.
6. **Seasons are Northern-Hemisphere labels.** For Australia/Brazil the fallback groups (DJF etc.) are still 3
   adjacent months, so the math is fine, but labels like "summer" would be wrong in reports.
7. Leave-one-region-out uses **H3 res-1 hexagons (~600 km across)** as "regions", plus a `merged_small` bucket that
   glues together distant small ones. Not administrative regions, so hard to explain to a user.
8. ADM1 boundaries for the API are downloaded at runtime from geoBoundaries into `data/reference/regions.geojson`;
   our local `data/boundaries/*_ADM1.geojson` are not used. (Note: KAZ ADM1 is the old 16-unit version, without
   Abai/Jetisu/Ulytau/Shymkent.)
9. Dates/months are in **UTC** (`acq_date`). For Kazakhstan (UTC+5/+6) a night pass near midnight local can fall
   on the previous UTC day. Same for every product, so there's no bias between sensors, but it's worth knowing.
10. `api/main.py` mounts `web/` at import time; without the `web/` folder the API **crashes on start**
    (`RuntimeError: Directory ... web does not exist`). This is why `tests/test_api.py` fails in our repo.

## 5. Bugs, risky choices, untested parts

Severity: 🔴 affects headline numbers or claims · 🟠 limits extension / correctness in some cases · 🟡 minor.

1. 🔴 **Prediction intervals are too narrow for anything smaller than the whole country** (root cause of the
   ~40% leave-one-region-out coverage). In `calib.predict` the heteroscedastic width is scaled by
   `sqrt(pi_med / (w · M_tot))` where `M_tot` is the **country** monthly MODIS total, not the area's own predicted
   total. A subregion with 1/8 of the fires has relative noise ≈ √8 ≈ 2.8× larger, but gets the country-level
   width. The same narrow intervals are served by the API for any polygon. Fix: scale by the area's own prediction
   (`pred` summed over the queried area), or calibrate intervals per subregion size.
2. 🔴 **The harmonized map is MODIS's map, rescaled.** Because the multiplier is one number per country-month,
   regional differences in the VIIRS/MODIS ratio (forest vs steppe vs cropland, small vs large fires) are not
   modelled at all. Land-cover strata exist in code but never ran (no MCD12C1 file). This is what LORO measures:
   median 16.8% error per subregion vs ~7% for the whole country, and up to 27% in one subregion.
3. 🔴 **Two independent model implementations.** `models.py` (used to *choose* the model) and `calib.py` (used to
   *produce* the series) implement the same formulas separately; the choice is copied into config by hand
   (`selected_model: poisson_log`, `interval_method: hetero`). Nothing checks that "C2" in one equals
   "poisson_log" in the other. Two different LORO numbers come out: 15.3% (experiments, 2012–2019) and 16.8%
   (07_validate, 2012–2025). The README quotes 16.8%. Judges may ask "which is it?".
4. 🟠 **"Protocol fixed before running"** is dated the same day as the runs and says itself that v2 was written
   after v1 results were seen. C2 beats C1 by 0.10 points (inside the 0.5 tie margin, both have 2 parameters). It's fine,
   but present it honestly as "a pre-registered-style rule chosen after a first run".
5. 🟠 **The harmonized 2012 step (×0.92) is largely by construction.** After 2012 the series *is* VIIRS; before
   2012 it is MODIS × a factor fitted on 2012–2019. So the step mostly shows that MODIS's own trend (×0.89) is
   preserved. That's a good property, but not independent proof. The independent evidence is the backcast (T1), LORO,
   and an external product (burned area), and the burned-area check never ran.
6. 🟠 **Holdout 2020–2025 is contaminated by MODIS orbit drift** (Terra from 2020, Aqua from 2021–22). The yearly
   bias goes +3.6% … −13.5% (2022). He reports this honestly. For the product it matters less (the model is used
   backwards, on 2000–2011), but the MAE 10.3% headline is a drift test, not a pure accuracy test.
7. 🟠 **Static-source mask** (only used for rows without `type`, i.e. NRT):
   * built from **all years**, so if we evaluate it on 2025–2026 data the mask has already seen that data (leakage);
   * the "persistent" rule (active ≥ 8 months/year in ≥ 2 years) counts **any** SP detection, including type 0
     vegetation fires, so it can mask a recurring agricultural-burning cell;
   * **never evaluated**: no precision/recall against `type = 2`. Phase C asks exactly for this.
   * In his run it removed 62,600 NRT rows.
8. 🟠 **SP/NRT detection by regex** `NRT|^\d{2}\.\d+$`: MODIS version `61.03` (rows inside archive files, with
   `type`) is labelled NRT. In practice it works (they keep `type`, and are dropped only if SP exists for the same
   satellite-day), but it relies on version-string conventions and any future `xx.y` version would flip.
9. 🟠 **Memory/speed.** `02_clean` loads every row into pandas and computes H3 in a Python loop (`[h3.latlng_to_cell(...) for ...]`).
   Fine for Kazakhstan (4.3 M rows), impossible for Brazil (≈ 44 M rows across 4 zips) or Australia (≈ 38 M).
   LORO refits the full bootstrap (1000 draws × 3 models) for each subregion → hours.
10. 🟠 **S-NPP outage fill** exists only from 2018 (NOAA-20 launch). S-NPP gaps in 2012–2017 are left as zeros,
    which slightly lowers the calibration target in those months.
11. 🟡 `last_full_year` = last year whose last data month is December. For a small country with no fires in December
    the last year is silently dropped.
12. 🟡 Known-event check is weak for one of its two events: Kostanay Sept 2022 ranks only **11th of 26** Septembers
    (the Abai June 2023 fire ranks 1st). Don't use Kostanay as a showcase.
13. 🟡 The README figure "Terra/Aqua cell-day ratio 0.86–1.02 in 2003–2021" is **not computed anywhere in the code**
    and is not in `metrics.json`. We'll recompute it ourselves in Phase B.
14. 🟡 FastAPI `on_event` is deprecated (warning only).
15. 🟡 The `.part` + rename download pattern and `existing_data_behavior="overwrite_or_ignore"` after `rmtree` are
    fine; the pipeline is idempotent, but **not deterministic across machines** only to the extent that
    `scipy.optimize` results can differ in the last digits. Bootstrap uses a fixed seed (42).

**Tests.** `tests/` has 30 tests on **synthetic data** (ratio/log-log/Poisson recovery, fallback strata, conformal
coverage, cleaning filters, cell-day dedup, outage threshold, NRT-vs-SP replacement, static mask, step test, MODIS
tile geometry, API shapes). In our repo: **23 pass**, `test_api.py` (7 tests) fails at import because `web/` is
absent (point 10 of §4). **Not tested:** `01_download`, the real-data end-to-end run, `07_validate` (LORO, jump test,
known events), `experiments.py`, consistency between `models.py` and `calib.py`, interval coverage on sub-areas,
multi-country inputs.

## 6. Known weak spots (as the author states them, plus ours)

| weak spot | number | cause |
|---|---|---|
| transfer to an unseen part of the country | LORO MAE 16.8%, coverage of 90% interval **40%** | §5.1 + §5.2 |
| MODIS orbit drift after 2020 | holdout yearly bias down to −13.5% (2022) | §5.6 |
| no land cover, no burned-area check | sections 4 and 6 of his report empty | missing Earthdata files |
| interval vs CI | bootstrap CI covers only 21% of holdout months | expected: CI ≠ prediction interval; only show `n_harm_low/high` to users |
| single country, single model | nothing tested outside Kazakhstan | §4 |

## 7. What must change

### Phase B (reproduce on Kazakhstan, minimal changes)
* New loader: read `data/raw/zips/*.zip` **in place** (never extract over or modify raw files), choose files by the
  6-digit request id (ignoring `" (2)"` / `_2` suffixes), sensor from the file name (`M-C61` MODIS, `SV-C2` S-NPP,
  `J1V-C2` NOAA-20, `J2V-C2` NOAA-21), both `fire_archive_*` and `fire_nrt_*`. KZ ids:
  847148, 847158, 847199 (MODIS), 847159, 847181 (S-NPP), 847180 (NOAA-20). Ids go in `config.yaml`.
* Skip `01_download` (or make it a no-op when zips are configured).
* Make `api/main.py` not crash without `web/` (mount only if the folder exists).
* Expected differences vs his run (to explain, not hide): he had NOAA-21 rows from the API (100,594 after cleaning),
  we have no KZ NOAA-21 zip. NOAA-21 is not used in the harmonized series, so the effect should be limited to the
  static mask. His archive came from yearly country files + API tail, ours from archive-download zips. Both are
  country-clipped, and the MODIS versions are the same (6.03 SP / 61.03 / 6.1NRT), but row counts may differ slightly.
  `last_full_year` stays 2025 → holdout 2020–2025 as in his run.
* Recompute the Terra/Aqua 2003–2021 ratio range ourselves (§5.13).

### Phase C (extend)
* **Multi-country**: `pipeline/manifest.csv` (request_id, country, role); a `country` key carried through every
  table; per-country config (outage threshold scaled to size, `min_count`, ADM1 file); one run per country with
  separate output folders, or a `country` partition.
* **Scalable reading** for transfer countries: DuckDB over one zipped CSV at a time, vectorized H3 (DuckDB `h3`
  extension or `h3.latlng_to_cell` on numpy arrays via a vectorized helper), output only country-month totals and
  validation metrics.
* **Static-source mask v2** with a time split (build < 2025-01-01, test on archive 2025-01…2026-07) and a precision/recall
  report for `type = 2`, plus % change in monthly totals. Revisit the "persistent" rule (§5.7).
* **ADM1 assignment** per H3 cell from `data/boundaries/*_ADM1.geojson` (centroid-in-polygon, nearest within 10 km,
  else `outside`). Use ADM1 instead of H3 res-1 hexagons for leave-one-region-out, so the regions mean something to users.
* **Fix the interval scaling for sub-areas** (§5.1) and re-measure LORO coverage. This is the most valuable fix.
* **One model implementation**: production reads the selected model from the experiments output, or `calib.py`
  reuses `models.py` (§5.3).
* **Validation additions**: UZ as a fully independent country (coefficients fit on KZ only, applied to UZ MODIS,
  compared with UZ VIIRS), TM stress test (gas flares), KG/TJ annual totals, transfer table per country,
  cross-check vs `data/external/burned_area.csv` (country-month, MCD64A1; BOM in header → read with `utf-8-sig`).
* **Speed**: LORO without the full 1000-draw bootstrap per fold (point fits + LOYO residuals are enough for MAE/coverage).

# Phase B — reproducing the baseline on Kazakhstan

**Result: reproduced.** 14 of 16 numbers are within 2% of Elbek's; the two flagged ones are explained below, and
both come from one cause: NASA FIRMS has re-labelled a few MODIS detections since he downloaded his files.
Machine-generated table: [`../reports/reproduction.md`](../reports/reproduction.md) (`python -m pipeline.compare_baseline`).

## What we changed (minimal, no logic changes)

| file | change | why |
|---|---|---|
| `config.yaml` | new `inputs:` block: `source: zips`, `zips_dir`, `request_ids` (KZ: 847148, 847158, 847199, 847159, 847181, 847180), sensor code → platforms, local ADM1 file | inputs are local FIRMS zips, all paths in config |
| `pipeline/02_clean.py` | `load_zips()`: reads `fire_archive_*.csv` and `fire_nrt_*.csv` **directly from the zips** (raw files are never extracted or modified), matches files by the 6-digit request id (suffixes like `" (2)"` ignored), fails if an id is missing or duplicated, checks that the satellites inside match the sensor code in the file name; rows from `fire_nrt_*` are marked NRT | baseline only read loose CSVs |
| `pipeline/02_clean.py` | `unify(df, is_modis=...)`: sensor comes from the zip name | **format bug found**: in archive-download zips the VIIRS files use MODIS column names (`brightness`, `bright_t31`). The baseline's "is it MODIS?" test looked for `brightness`, so every VIIRS row was treated as MODIS, its confidence letters `n/h/l` became NaN and **70% of all rows were dropped** in the first try. Fixed: 6.4% dropped, as in his run (6.3%). |
| `pipeline/01_download.py` | with `source: zips`, no internet: only copies `data/boundaries/KAZ_ADM1.geojson` to `data/reference/regions.geojson` (API region list) | |
| `api/main.py` | mounts `web/` only if the folder exists | API crashed without the frontend; now all 30 tests pass (was 23) |
| `pipeline/compare_baseline.py` | new: builds the ours-vs-his table and the Terra/Aqua ratio | |
| `.gitignore` | `data/reference/` (pipeline output) | |

Everything else (`03_grid` … `07_validate`, `calib.py`, `models.py`, config values) is untouched.
Full run on this laptop: ~14 min (clean 40 s, grid 15 s, experiments 40 s, calibrate 80 s, validate 10 min).

## Inputs vs his inputs

* Raw rows per satellite per year, 2000–2025: **identical** for S-NPP and NOAA-20; MODIS differs by 0–4 rows a year
  (≤ 0.03%).
* 2026 differs (his: API windows downloaded on the day, ours: zip archive to Jul/Aug + NRT to mid-Nov). 2026 is not
  used in any metric: the last full year is 2025 in both runs.
* No NOAA-21 for Kazakhstan in our zips (he had it from the API). NOAA-21 is not used in the harmonized series.
* **FIRMS re-labelled MODIS 2000–2017.** Same detections (coordinates, times, confidence, FRP all equal), but his
  yearly country files say `version 6.2`, our archive zips say `6.03`, and some points changed
  `type 0 (vegetation fire) → type 2 (static land source)`. Example, 2010: 234 of 62,763 points (0.4%).
  Because `type 2` is removed in cleaning, our MODIS cell-days 2000–2017 are **0.3–1.0% lower** than his
  (e.g. 2017: −431 of ~42,000). MODIS 2018–2025 and all VIIRS: identical cell-days.

## The table

| metric | his | ours | diff | verdict |
|---|---|---|---|---|
| naive points step at 2012 | ×2.81 | ×2.82 | +0.6% | ✅ |
| naive cell-day step | ×1.63 | ×1.65 | +0.8% | ✅ |
| MODIS-only step | ×0.89 | ×0.89 | −0.1% | ✅ |
| harmonized step | ×0.92 | ×0.92 | 0.0% | ✅ |
| monthly step regression, naive | ×3.19 | ×3.23 | +1.1% | ✅ |
| monthly step regression, harmonized | ×0.86 | ×0.86 | −0.1% | ✅ |
| backcast MAE (fit 2016–19 → 2012–15) | 7.0% | 6.9% | −0.7% | ✅ |
| holdout 2020–2025 MAE | 10.3% | 10.3% | −0.3% | ✅ |
| holdout bias | −3.2% | −2.2% | +1.0 pp | ⚠ explained |
| holdout Pearson R | 0.984 | 0.984 | 0.0% | ✅ |
| leave-one-region-out median MAE | 16.8% | 17.3% | +0.4 pp (+2.5% rel.) | ⚠ explained |
| leave-one-region-out interval coverage | 40% | 41% | +0.3 pp | ✅ (the known weak spot is reproduced) |
| Terra/Aqua cell-day ratio 2003–2021 | 0.86–1.02 | 0.86–1.02 | — | ✅ |
| selected model / intervals | C2 Poisson log-link / hetero | same | — | ✅ |

### Why the holdout bias moved from −3.2% to −2.2%
"Bias" is itself a small number, so a small shift looks big in relative terms (−32%); in absolute terms it is
**1.0 percentage point**. Chain of cause, checked in the data:
1. Observed VIIRS in 2020–2025: identical to his, every year.
2. Our MODIS in the calibration years 2012–2017 is ~0.5–1% lower (re-labelling above), while VIIRS is the same.
3. So the fitted VIIRS/MODIS multiplier is a bit higher: +0.7% to +2.0% depending on the month.
4. MODIS in 2020–2025 is identical, so the predictions are 0.9–1.6% higher every year → bias −3.2% → −2.2%.

### Why leave-one-region-out MAE moved from 16.8% to 17.3%
Same 8 subregions, same cell-day weights within ~3%. The re-labelled points are not spread evenly, so each region's
error moves by −0.2 to +1.1 points; the median of 8 regions moves by +0.4 points. Within noise of the method,
and it does not change the conclusion (≈17% error and ≈40% coverage in an unseen region).

## Terra/Aqua cell-day ratio (computed by us)

His README quoted it without code. Ours, total Terra cell-days / total Aqua cell-days per year:
0.86 (2003), 0.94, 0.97, 1.00, 0.92, 0.95, 0.94, 0.97, 0.87, 0.99 (2012), 0.86, 1.02, 1.01, 0.92, 1.02, 0.93, 1.00,
0.95, 1.01 (2021) → **range 0.86–1.02**, then **1.36 (2022), 0.87, 0.76 (2024), 0.62 (2025)**, 0.52 (2026, partial).
The break after 2021 is the MODIS orbit drift: Terra and Aqua no longer see the same time of day, so the two
"identical" sensors stop agreeing. That is why the 2020+ holdout is a drift test and why the model is used backwards.

## How to rerun
```bash
.venv/Scripts/python.exe -m pipeline.run_all
.venv/Scripts/python.exe -m pipeline.compare_baseline
.venv/Scripts/python.exe -m pytest -q
```

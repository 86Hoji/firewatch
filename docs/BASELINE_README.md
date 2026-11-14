# Fire Regimes — a harmonized MODIS + VIIRS fire calendar

NASA Space Apps Challenge · *Fire regimes*. One comparable record of fire activity from 2000 to today, where the
instrument no longer shapes the picture. Region in this build: **Kazakhstan** (any FIRMS country or bbox via `config.yaml`).

MODIS (1 km, since 2000) and VIIRS (375 m, since 2012) see the same fires very differently: VIIRS finds several times
more hotspots. Splice them naively and fire "explodes" in 2012. This project translates MODIS onto the VIIRS S-NPP
scale, proves on unseen data that the translation holds, and serves the result as a calendar people can query.

![before / after](reports/before_after.png)

## Results

Kazakhstan, calibration 2012–2019. Model chosen among 8 candidates by a protocol fixed before running
([`reports/model_protocol.md`](reports/model_protocol.md)): **Poisson GLM, log link, Terra∪Aqua**, heteroscedastic
90% prediction intervals.

| check | result |
|---|---|
| 2012 jump, naive splice of hotspot points | ×2.81 (MODIS alone: ×0.89) |
| 2012 jump, harmonized | ×0.92 |
| Monthly step regression 2003–2019 (season + trend + step, Newey-West 95% CI) | naive ×3.19 (1.75–5.84, step present); harmonized ×0.86 (0.54–1.38, no step); MODIS alone ×0.77 (0.40–1.46) |
| Backcast, fit 2016–19 → predict 2012–15 (the direction of use) | MAE 7.0% of mean, bias −2.0% |
| Leave-one-year-out within 2012–2019 | MAE 6.3% |
| Forecast holdout 2020–2025 (MODIS orbit drift) | MAE 10.3%, bias −3.2%, Pearson R 0.984 |
| Coverage of the 90% interval | 90% on drift-free tests; 83% on 2020–2025 |
| Leave-one-region-out, median over 8 subregions | MAE 16.8%, bias −3.0%, interval coverage 40% |
| Peak month MODIS = VIIRS, 2012–2019 | 100% of years |
| Synthetic recovery of known k (3.2, 2.1) | max error 1.74% |

Honest reading: the level and the 2012 seam are fixed, in time and across regions. The weak spot is transfer to an
unseen region (≈17% error, intervals too narrow there): the model is calibrated for the region as a whole. Holdout
bias by year (+3.6% … −13.5%, worst in 2022) follows MODIS instability: the Terra/Aqua cell-day ratio is
0.86–1.02 in 2003–2021, then 1.36 in 2022 and 0.76 → 0.57 in 2024–2026.

Full report with every metric and figure: [`reports/validation.md`](reports/validation.md) (machine-readable:
`reports/metrics.json`, model choice: `reports/model_selection.json`, cleaning log: `reports/cleaning_summary.json`).

## Method

1. **Cell-days, not dots.** Every hotspot goes to an H3 res-7 hexagon (~5 km²). A hexagon with ≥1 detection on a day
   counts once (`n_*` = cell-days per month). This removes most of the resolution gap before any statistics.
2. **Stable reference.** Target scale = VIIRS **S-NPP only** (2012+). NOAA-20 is used only to fill S-NPP outage days
   (days with zero S-NPP and ≥ `snpp_gap_min_noaa20` NOAA-20 detections region-wide), scaled by a NOAA-20→S-NPP
   coefficient fit on 2018–2019. MODIS = Terra ∪ Aqua; Terra-only months (Nov 2000 – Jun 2002) are scaled by
   (Terra∪Aqua)/Terra fit on 2003–2011.
3. **Calibration on 2012–2019** (both sensors flying), 2020+ held out because of MODIS orbit drift.
   Strata fall back from `land_cover × month` → `land_cover × season` → `land_cover` → region when
   ΣMODIS < `min_count`. The production model is a **Poisson GLM with log link on monthly totals**,
   E[V] = exp(a)·(M+1)^b (count-data best practice instead of OLS on log-transformed counts); its multiplier depends
   on the regional monthly total, so it is always evaluated on whole-region MODIS totals.
   It was chosen among 8 candidates (ratio, OLS log1p, Poisson log-link; Terra∪Aqua vs Aqua-only, day/night split)
   by a protocol written before running ([`reports/model_protocol.md`](reports/model_protocol.md)): mean MAE of a
   backcast (fit 2016–19 → predict 2012–15, the direction the product is used in), leave-one-region-out and
   leave-one-year-out. Results: [`reports/model_comparison.md`](reports/model_comparison.md).
4. **Uncertainty.** `n_harm_low/high`: 90% prediction interval from leave-one-year-out residuals inside 2012–2019,
   heteroscedastic (relative width shrinks as the regional monthly prediction grows); chosen by the same protocol
   for coverage closest to 90% on drift-free tests. `n_harm_ci_low/high`: bootstrap over years of the coefficients.
5. **Harmonize.** 2000–2011: `n_harm = MODIS_eff × multiplier` (`source = MODIS_calibrated`); 2012+: `n_harm` = VIIRS
   S-NPP (+ NOAA-20 outage fill) (`source = VIIRS_SNPP`).

## Run it

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Linux/macOS: .venv/bin/pip
cp .env.example .env            # put FIRMS_MAP_KEY=... in .env
python -m pipeline.run_all      # or: make pipeline; single steps: python -m pipeline.run_all 05 06
python -m uvicorn api.main:app --port 8000   # open http://localhost:8000, API docs at /docs
python -m pytest -q
```

**FIRMS MAP_KEY:** free, request at <https://firms.modaps.eosdis.nasa.gov/api/map_key/>. Without it the pipeline
still runs on the yearly archive; the key adds the current year (SP via API where available, NRT for the last weeks).

**Archive:** `01_download.py` fetches FIRMS per-country yearly CSVs from
`https://firms.modaps.eosdis.nasa.gov/data/country/` (no key needed). Manually downloaded CSVs dropped into
`data/raw/` are picked up as well.

**Optional (NASA Earthdata):**
- one `MCD12C1*.hdf` (land cover, any year) in `data/reference/` enables land-cover strata (`04_landcover.py`);
- `MCD64A1` C6.1 tiles in `data/reference/mcd64a1/` (Kazakhstan: h20–h23 v03, h20–h24 v04; e.g. 2008–2016) enable the
  burned-area check (`04b_burned_area.py` → section 6 of the validation report).

Both are read with `pyhdf`; after adding them run `python -m pipeline.run_all 04 05 06 07`.

**Docker:** build after running the pipeline (the image ships `data/aggregated`, `data/processed`, `reports`):
`docker build -t fire-regimes . && docker run -p 7860:7860 fire-regimes`.

## API

All POST endpoints take one area — `geometry` (GeoJSON), `bbox` `[w,s,e,n]`, `point` `[lat,lon]` + `radius_km`, or
`region_id` — plus `start_year`, `end_year`, `mode` (`harmonized | raw_modis | raw_viirs | naive`).

| endpoint | returns |
|---|---|
| `POST /api/calendar` | year × month matrices: `values`, `source`, `low`, `high`, `anomaly_pct`, partial-month flag |
| `POST /api/anomaly` | value for `year`/`month` (default: latest) vs base-period median, p25, p75, z, percentile; partial month scaled to full |
| `POST /api/yearly` | annual totals, ranks among complete years |
| `POST /api/seasonal` | median profile with IQR, peak month |
| `POST /api/export.csv` | hotspot points with `harmonization_weight` (MODIS: applied multiplier, S-NPP: 1) and `in_harmonized_series` |
| `POST /api/export_calendar.csv` | the calendar as a table |
| `POST /api/points`, `/api/hexes` | map layers for one month |
| `GET /api/regions`, `/api/meta` | ADM1 list (geoBoundaries), data period and model version |

Areas are matched to H3 cells by centre-in-polygon, the same rule as `h3.geo_to_cells`, evaluated with vectorized
`shapely.contains_xy` against the cells that have data, so a country-sized polygon answers in well under a second.

## Where the data differ from the spec

- FIRMS per-country files carry MODIS `version` values `6.03` / `6.2` (standard) and `61.03` (NRT tail of the latest
  year); VIIRS `2` (standard) and `2.0NRT`. Processing (SP/NRT) is derived from these and from the API source name.
- VIIRS `satellite` codes: `N` = S-NPP, `1` = NOAA-20, `2` = NOAA-21. NOAA-21 yearly country files are not published
  (`viirs-jpss2` returns 404); NOAA-21 comes only from the API and is not used in the harmonized series.
- Country files already include `type`, so most "NRT" rows have it; the static-source mask (`data/reference/static_mask.parquet`)
  is still built and applied to rows without `type`.
- MODIS confidence classes: < 30 low, 30–79 nominal, ≥ 80 high.
- S-NPP NRT ends on 2026-11-02 in the API at the time of the last download; later days rely on the NOAA-20 outage fill.

## Known limitations

- MODIS orbit drift after 2020 shifts the VIIRS/MODIS relationship; holdout bias by year is in the report.
- Prediction intervals are calibrated on regional monthly totals; for small areas the true uncertainty is wider.
- Land-cover strata and the MCD64A1 burned-area check run only when the NASA Earthdata files are present (see above).

## Layout

```
pipeline/   01_download … 07_validate, calib.py (models), metrics.py, run_all.py
api/        FastAPI + DuckDB over data/aggregated/cell_month.parquet
web/        static SPA (Leaflet + leaflet-draw, ECharts), strings in web/i18n.js (EN, RU)
tests/      pytest; synthetic data only inside tests
reports/    validation.md, metrics.json, figures
```

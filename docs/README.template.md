# FIREWATCH — one fire record from 2000 to today, independent of the satellite

MODIS (since 2000, 1 km pixels) and VIIRS (since 2012, 375 m pixels) see the same fires very differently: VIIRS
finds several times more of them. Splice the two NASA records naively and fire activity "explodes" in 2012 — an
artefact of the instrument, not of the landscape. FIREWATCH translates MODIS onto the VIIRS S-NPP scale, tests the
translation on data it never saw, and serves the result as a monthly fire calendar and map for Central Asia
(Kazakhstan, Uzbekistan, Turkmenistan, Kyrgyzstan, Tajikistan), with transfer tests on five other countries.

## Three numbers

| | before | after |
|---|---|---|
| **Honest uncertainty.** Share of held-out region-months inside the 90% interval (Kazakhstan, leave-one-region-out) | {cov_before} | **{cov_after}** |
| **No 2012 jump.** Step in annual fire activity 2009–11 → 2012–14 (MODIS alone changes ×{uz_modis} in Uzbekistan, ×{tm_modis} in Turkmenistan) | naive splice: Uzbekistan ×{uz_naive}, Turkmenistan ×{tm_naive} | harmonized: **×{uz_local}**, **×{tm_local}** |
| **Consistent with burned area.** Step at 2012 in fire cell-days once monthly MODIS burned area (MCD64A1) is accounted for; ≈ 1 means no break | naive: Uzbekistan ×{uz_ba_naive}, Turkmenistan ×{tm_ba_naive} | harmonized: **×{uz_ba}** (95% CI {uz_ba_ci}), **×{tm_ba}** ({tm_ba_ci}) |

Uzbekistan and Turkmenistan use coefficients fitted on their own 2012–2019 overlap (the Kazakh coefficients do not
transfer — see below). Full numbers: [`reports/VALIDATION.md`](reports/VALIDATION.md) (machine-readable:
[`reports/validation.json`](reports/validation.json)); Kazakhstan technical report:
[`reports/validation_kz.md`](reports/validation_kz.md); model choice: [`reports/model_card.json`](reports/model_card.json).

## How it works

1. **Count cell-days, not dots.** Every detection goes to an H3 hexagon (resolution 7, ~5 km²); a hexagon with at
   least one detection on a day counts once. This alone removes about half of the resolution gap.
2. **One stable reference.** The target scale is VIIRS S-NPP; NOAA-20 only fills satellite-wide S-NPP outage days.
   MODIS = Terra ∪ Aqua. Static heat sources (gas flares, industry) are removed with FIRMS `type` and a mask.
3. **Calibrate on the overlap, apply backwards.** In 2012–2019 both sensors fly; a Poisson model
   `E[VIIRS] = exp(a)·(MODIS+1)^b` per season is chosen among 8 candidates by a protocol fixed before the run, then
   applied to 2000–2011. 2020+ is held out (MODIS orbit drift).
4. **Test on what the model never saw.** Back-cast (fit 2016–19 → predict 2012–15): {t1}% monthly error in
   Kazakhstan; leave-one-year-out {t4}%; leave-one-region-out {t3}% (median of {n_regions} oblasts); held-out {holdout}:
   {t2}%, bias {t2_bias}%. 90% intervals are sized at the level shown (country or region) from held-out errors.

## Honest limitations

- **2002–2004 is extrapolation.** Kazakhstan's MODIS activity in 2002–2004 ({kz_0204} cell-days a year) exceeds every
  calibration year (max {kz_calmax}), so those years rely on the fitted curve beyond its range. An extrapolation test
  (fit on the quieter years of each month, predict the busier ones) gives {t5_c2_mae}% error and {t5_c2_bias}% bias for the chosen
  model vs {t5_c0_bias}% bias for a constant ratio ([`docs/HARMONIZATION_REVIEW.md`](docs/HARMONIZATION_REVIEW.md) §2.1),
  but the far tail is still untested.
- **Known fires rank by count, not intensity.** Events are ranked by excess fire cell-days in a ~40 km hexagon.
  A compact, intense forest fire is small in counts: the Abai (Semey Ormany) fire of June 2023 ranks {abai_rank} of {abai_of}
  events. Ranking by intensity (fire radiative power) is the natural next step.
- **A new industrial site in Uzbekistan is not caught by FIRMS labels.** A heat source near 38.1°N 67.3°E appears
  in 2025; FIRMS labels 92% of its VIIRS detections as vegetation fire, so `type` cannot remove it and it inflates
  Uzbekistan's 2025–26 VIIRS counts.
- **Coefficients are local.** The Kazakh model applied unchanged elsewhere is off by {asis_range}% (it cannot know a
  country's VIIRS/MODIS ratio, ×{ratio_min} in {ratio_min_c} to ×{ratio_max} in {ratio_max_c}); refitted on each country's own overlap the same
  method gets {local_range}%. The method transfers, the coefficients do not.

## Run it

Pipeline + API (Python 3.12; FIRMS archive zips in `data/raw/zips/`, listed in `pipeline/manifest.csv`):

```bash
pip install -r requirements.txt
python -m pipeline.run_all
python -m uvicorn api.main:app --port 8000
```

Website (static, reads `web/public/data/` written by `python -m pipeline.run_all 08`):
`cd web && npm ci && npm run dev`. Tests: `python -m pytest -q`.

## Repository

```
pipeline/   01_download … 07_validate, 07b_validation_package, 08_export_web; calib.py, models.py, intervals.py
api/        FastAPI + DuckDB over the harmonized cell-months
web/        website (Vite + TypeScript), data in web/public/data/
reports/    VALIDATION.md, validation_kz.md, model_card.json, model_comparison.md
docs/       AUDIT.md, HARMONIZATION_REVIEW.md, PHASE_*.md, DECISIONS.md, EVENTS.md
tests/      pytest, synthetic data only
```

## Credits and data

- **Baseline pipeline and methodology review:** Elbek (`fire-regimes`; [`docs/HARMONIZATION_REVIEW.md`](docs/HARMONIZATION_REVIEW.md)).
- **NASA FIRMS** — MODIS Collection 6.1 and VIIRS 375 m (S-NPP, NOAA-20) active fire detections:
  https://firms.modaps.eosdis.nasa.gov
- **NASA GIBS — VIIRS Black Marble** night-lights basemap on the website: https://gibs.earthdata.nasa.gov
- **MODIS MCD64A1** Collection 6.1 monthly burned area (independent check of the 2012 seam).
- **geoBoundaries** ADM1 boundaries (CC BY 4.0): https://www.geoboundaries.org
- Uber **H3** hexagonal grid, **DuckDB**, **FastAPI**.

# Validation — Kazakhstan

Calibration 2012–2019, holdout 2020–2025. Unit: H3 res 7 cell-days, VIIRS S-NPP equivalent. Selected model: **poisson_log**.

## Summary / Вывод

**EN.** On years the model never saw (2020–2025), harmonized MODIS reproduces observed VIIRS S-NPP monthly fire activity with R = 0.984 and total bias -2.2%. The naive MODIS→VIIRS splice jumps ×2.82 at 2012, while MODIS alone changes ×0.89; after harmonization the step is ×0.92.

**RU.** На годах, которых модель не видела (2020–2025), гармонизированный MODIS воспроизводит наблюдаемую активность VIIRS S-NPP по месяцам с R = 0.984 и суммарным смещением -2.2%. Наивная склейка MODIS→VIIRS даёт скачок ×2.82 в 2012 году, хотя сам MODIS меняется лишь в ×0.89; после гармонизации скачок ×0.92.

![before/after](before_after.png)

## 0. Model choice

Protocol fixed before running: [model_protocol.md](model_protocol.md); all candidates: [model_comparison.md](model_comparison.md). Selected **C2** (Terra∪Aqua, Poisson log-link): backcast 2016–19→2012–15 MAE 6.9%, leave-one-region-out 15.6%, leave-one-year-out 6.5%. Intervals: **hetero**, coverage of the nominal 90% on drift-free tests 90%.

## 1. Temporal holdout

| model | period | MAE | MAE % mean | bias % | median rel. bias % | Pearson R | Spearman ρ | coverage (pred. 90%) | coverage (bootstrap CI) |
|---|---|---|---|---|---|---|---|---|---|
| ratio | in_sample | 212.6 | 6.6 | 0.0 | -3.0 | 0.996 | 0.994 | 93% | — |
| loglog | in_sample | 213.0 | 6.6 | 0.3 | 0.9 | 0.996 | 0.993 | 89% | — |
| poisson_log | in_sample | 195.4 | 6.1 | -0.0 | 0.9 | 0.997 | 0.993 | 92% | — |
| ratio | holdout | 281.4 | 14.8 | -9.3 | -13.8 | 0.979 | 0.986 | 72% | 24% |
| loglog | holdout | 201.7 | 10.6 | -2.3 | -0.4 | 0.983 | 0.991 | 85% | 24% |
| poisson_log | holdout | 195.7 | 10.3 | -2.2 | -1.5 | 0.984 | 0.991 | 83% | 19% |

Holdout by season (selected model):

| season | MAE % mean | bias % | R | coverage |
|---|---|---|---|---|
| DJF | 39.6 | 26.4 | 0.989 | 83% |
| JJA | 7.4 | 2.8 | 0.994 | 100% |
| MAM | 11.8 | -6.1 | 0.970 | 56% |
| SON | 7.6 | -0.5 | 0.995 | 94% |

Holdout by year (watch for MODIS orbit drift):

| year | observed | harmonized MODIS | bias % |
|---|---|---|---|
| 2020 | 35708 | 37311 | 4.5 |
| 2021 | 30219 | 30953 | 2.4 |
| 2022 | 22548 | 19728 | -12.5 |
| 2023 | 18107 | 17328 | -4.3 |
| 2024 | 9914 | 9105 | -8.2 |
| 2025 | 20119 | 19176 | -4.7 |

![holdout](holdout.png)

Intervals. `n_harm_low/high` = prediction interval: leave-one-year-out residuals log(VIIRS/pred) of regional monthly totals inside 2012–2019, 5th–95th percentile per season (cross-conformal). `n_harm_ci_*` = bootstrap over years of the coefficients only, so it is expected to under-cover single months. Intervals are calibrated for regional monthly totals; for small areas true uncertainty is wider.

## 2. Spatial cross-validation (leave-one-region-out)

Subregions: H3 res 1 parents; ones with < 3% of MODIS cell-days merged. Calibrated without the region, tested on it over 2012–2025. Log-log multipliers use whole-region MODIS totals (input data, exactly as in production). Median over subregions: loglog: MAE 17.1%, bias -3.5%, coverage 42%; poisson_log: MAE 17.3%, bias -2.9%, coverage 40%; ratio: MAE 16.7%, bias -0.7%, coverage 38%.

| subregion | model | center | MODIS cell-days | MAE % mean | bias % | R | coverage |
|---|---|---|---|---|---|---|---|
| `8110bffffffffff` | ratio | 52.8, 48.9 | 42593 | 23.9 | 11.9 | 0.987 | 38% |
| `8110bffffffffff` | loglog | 52.8, 48.9 | 42593 | 22.7 | 12.9 | 0.993 | 26% |
| `8110bffffffffff` | poisson_log | 52.8, 48.9 | 42593 | 22.8 | 13.0 | 0.993 | 28% |
| `81203ffffffffff` | ratio | 46.0, 71.5 | 132264 | 13.7 | -1.1 | 0.986 | 62% |
| `81203ffffffffff` | loglog | 46.0, 71.5 | 132264 | 12.8 | -1.1 | 0.986 | 51% |
| `81203ffffffffff` | poisson_log | 46.0, 71.5 | 132264 | 12.8 | -0.8 | 0.987 | 50% |
| `81207ffffffffff` | ratio | 49.3, 82.8 | 74753 | 15.4 | -0.2 | 0.983 | 49% |
| `81207ffffffffff` | loglog | 49.3, 82.8 | 74753 | 15.0 | 1.6 | 0.984 | 40% |
| `81207ffffffffff` | poisson_log | 49.3, 82.8 | 74753 | 15.4 | 1.4 | 0.982 | 40% |
| `81213ffffffffff` | ratio | 50.0, 60.8 | 149246 | 14.0 | -4.8 | 0.990 | 35% |
| `81213ffffffffff` | loglog | 50.0, 60.8 | 149246 | 13.8 | -8.1 | 0.988 | 42% |
| `81213ffffffffff` | poisson_log | 50.0, 60.8 | 149246 | 12.9 | -8.0 | 0.991 | 39% |
| `81217ffffffffff` | ratio | 54.2, 72.2 | 174426 | 17.9 | 5.0 | 0.990 | 33% |
| `81217ffffffffff` | loglog | 54.2, 72.2 | 174426 | 8.8 | -5.9 | 0.996 | 48% |
| `81217ffffffffff` | poisson_log | 54.2, 72.2 | 174426 | 9.3 | -4.9 | 0.995 | 44% |
| `8121bffffffffff` | ratio | 41.9, 61.7 | 33730 | 15.5 | 5.5 | 0.985 | 55% |
| `8121bffffffffff` | loglog | 41.9, 61.7 | 33730 | 19.1 | 10.0 | 0.985 | 43% |
| `8121bffffffffff` | poisson_log | 41.9, 61.7 | 33730 | 19.1 | 10.5 | 0.984 | 42% |
| `812c7ffffffffff` | ratio | 45.0, 51.5 | 21765 | 32.6 | -15.2 | 0.982 | 27% |
| `812c7ffffffffff` | loglog | 45.0, 51.5 | 21765 | 28.2 | -16.0 | 0.984 | 27% |
| `812c7ffffffffff` | poisson_log | 45.0, 51.5 | 21765 | 27.9 | -16.2 | 0.984 | 27% |
| `merged_small` | ratio | —, — | 23259 | 28.9 | -23.4 | 0.969 | 37% |
| `merged_small` | loglog | —, — | 23259 | 25.1 | -19.2 | 0.972 | 42% |
| `merged_small` | poisson_log | —, — | 23259 | 25.0 | -17.6 | 0.968 | 41% |

## 3. The 2012 jump

Step ratio = mean(2012–2014) / mean(2009–2011) of annual totals. MODIS-only is the same instrument on both sides, so its step is the real change; excess = series step / MODIS step. Pettitt test on log annual totals.

| series | step ratio | excess vs MODIS | Pettitt change after | Pettitt p |
|---|---|---|---|---|
| naive_points | ×2.82 | ×3.19 | 2011 | 0.6815 |
| naive_cell_days | ×1.65 | ×1.86 | 2020 | 0.2370 |
| harmonized | ×0.92 | ×1.04 | 2010 | 0.0022 |
| modis_only_reference | ×0.89 | ×1.00 | 2010 | 0.0032 |

Monthly step regression, 2003–2019 (log1p series ~ month dummies + linear trend + step at 2012; Newey-West 95% CI, 12 lags). A sensor artefact shows as a step whose CI excludes 1; MODIS-only is the same-instrument reference.

| series | step factor | 95% CI | CI includes 1 |
|---|---|---|---|
| naive_points | ×3.23 | 1.76–5.93 | no |
| harmonized | ×0.86 | 0.54–1.38 | yes |
| modis_only_reference | ×0.76 | 0.40–1.47 | yes |

## 4. Seasonality

Peak month MODIS = VIIRS in 100% of years 2012–2019 (within ±1 month: 100%); all overlap years: 100%.

| year | peak MODIS | peak VIIRS |
|---|---|---|
| 2012 | 4 | 4 |
| 2013 | 4 | 4 |
| 2014 | 4 | 4 |
| 2015 | 8 | 8 |
| 2016 | 4 | 4 |
| 2017 | 7 | 7 |
| 2018 | 4 | 4 |
| 2019 | 4 | 4 |
| 2020 | 4 | 4 |
| 2021 | 4 | 4 |
| 2022 | 4 | 4 |
| 2023 | 4 | 4 |
| 2024 | 4 | 4 |
| 2025 | 4 | 4 |

## 5. Synthetic recovery (sanity check, synthetic data only)

True k: {'A': 3.2, 'B': 2.1}. Recovered (min–max over months): A: 3.166–3.215, B: 2.064–2.135. Max relative error 1.74% → PASS (< 5%). Also covered by `tests/test_calibration.py`.

## 6. Burned area (MCD64A1)

Not run: put MCD64A1 tiles into `data/reference/mcd64a1/` (NASA Earthdata, see README).

## 7. Known events

| event | year-month | value | median same month | rank (same month) | rank (all months) |
|---|---|---|---|---|---|
| Kostanay forest and steppe fires (Auliekol) | 2022-09 | 162 | 142 | 11 / 26 | 76 / 222 |
| Abai region forest fire (Semey Ormany) | 2023-06 | 223 | 15 | 1 / 26 | 11 / 209 |

## Coefficients

![coefficients](coefficients.png)

![raw series](raw_series.png)

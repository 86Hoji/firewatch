# Validation — Kazakhstan

Calibration 2012–2019, holdout 2020–2025. Unit: H3 res 7 cell-days, VIIRS S-NPP equivalent. Selected model: **poisson_log**.

## Summary / Вывод

**EN.** On years the model never saw (2020–2025), harmonized MODIS reproduces observed VIIRS S-NPP monthly fire activity with R = 0.985 and total bias -0.9%. The naive MODIS→VIIRS splice jumps ×2.76 at 2012, while MODIS alone changes ×0.88; after harmonization the step is ×0.92.

**RU.** На годах, которых модель не видела (2020–2025), гармонизированный MODIS воспроизводит наблюдаемую активность VIIRS S-NPP по месяцам с R = 0.985 и суммарным смещением -0.9%. Наивная склейка MODIS→VIIRS даёт скачок ×2.76 в 2012 году, хотя сам MODIS меняется лишь в ×0.88; после гармонизации скачок ×0.92.

![before/after](before_after.png)

## 0. Model choice

Protocol fixed before running: [model_protocol.md](model_protocol.md); all candidates: [model_comparison.md](model_comparison.md). Selected **C2** (Terra∪Aqua, Poisson log-link): backcast 2016–19→2012–15 MAE 7.0%, leave-one-region-out 13.5%, leave-one-year-out 6.4%. 90% intervals sized at the predicted level: country coverage (leave-one-year-out) 89%, region coverage (leave-one-region-out) 50% before → 92% after.

## 1. Temporal holdout

| model | period | MAE | MAE % mean | bias % | median rel. bias % | Pearson R | Spearman ρ | coverage (pred. 90%) | coverage (bootstrap CI) |
|---|---|---|---|---|---|---|---|---|---|
| ratio | in_sample | 182.2 | 5.9 | 0.0 | -2.2 | 0.997 | 0.996 | 92% | — |
| loglog | in_sample | 194.1 | 6.3 | 0.5 | 2.3 | 0.996 | 0.994 | 91% | — |
| poisson_log | in_sample | 181.5 | 5.9 | 0.0 | 1.6 | 0.997 | 0.994 | 93% | — |
| ratio | holdout | 215.9 | 12.3 | -6.7 | -11.2 | 0.982 | 0.993 | 75% | 28% |
| loglog | holdout | 179.3 | 10.2 | -1.1 | 0.4 | 0.984 | 0.994 | 90% | 25% |
| poisson_log | holdout | 171.9 | 9.8 | -0.9 | -0.1 | 0.985 | 0.995 | 92% | 25% |

Holdout by season (selected model):

| season | MAE % mean | bias % | R | coverage |
|---|---|---|---|---|
| DJF | 37.2 | 25.0 | 0.994 | 94% |
| JJA | 8.2 | 6.5 | 0.994 | 100% |
| MAM | 10.7 | -5.1 | 0.972 | 72% |
| SON | 6.8 | 0.1 | 0.995 | 100% |

Holdout by year (watch for MODIS orbit drift):

| year | observed | harmonized MODIS | bias % |
|---|---|---|---|
| 2020 | 34006 | 35549 | 4.5 |
| 2021 | 28473 | 29260 | 2.8 |
| 2022 | 20668 | 18414 | -10.9 |
| 2023 | 16478 | 16126 | -2.1 |
| 2024 | 8521 | 8222 | -3.5 |
| 2025 | 18547 | 17946 | -3.2 |

![holdout](holdout.png)

Intervals (since C3): sized at the level being predicted. Country totals: leave-one-year-out log errors, width shrinking with size (coverage above). Regions: percentiles of leave-one-region-out errors for predictions of similar size (section 2). `n_harm_ci_*` = bootstrap over years of the coefficients only, expected to under-cover single months.

## 2. Spatial cross-validation (leave-one-ADM1-region-out)

Computed once in `experiments.py` (T3) for the selected model: fit 2012–2019 without the region, predict it over the same years. Multipliers use whole-country MODIS totals (input data, as in production). Median over the 13 regions with ≥ 1% of MODIS activity: MAE 13.5%, bias 0.4%. Coverage of the 90% interval over all region-months: before 50%, after 92%.

| region | name | share of MODIS | in median | MAE % mean | bias % | R | coverage before | coverage after |
|---|---|---|---|---|---|---|---|---|
| `KZ-KUS` | Kostanay Region | 12.7% | yes | 10.5 | -3.3 | 0.991 | 68% | 94% |
| `KZ-SEV` | North Kazakhstan Region | 12.3% | yes | 10.0 | 0.4 | 0.997 | 60% | 93% |
| `KZ-KAR` | Karaganda Region | 12.2% | yes | 11.5 | 1.1 | 0.994 | 59% | 96% |
| `KZ-AKM` | Akmola Region | 10.5% | yes | 11.4 | 3.0 | 0.996 | 66% | 96% |
| `KZ-KZY` | Kyzylorda Region | 10.0% | yes | 17.8 | 3.7 | 0.980 | 43% | 75% |
| `KZ-ALM` | Almaty Region | 8.4% | yes | 12.7 | -7.4 | 0.990 | 58% | 92% |
| `KZ-VOS` | East Kazakhstan Region | 7.7% | yes | 13.5 | -0.9 | 0.985 | 54% | 92% |
| `KZ-AKT` | Aktobe Region | 7.6% | yes | 13.1 | -7.2 | 0.994 | 42% | 82% |
| `KZ-ZAP` | West Kazakhstan Region | 6.0% | yes | 16.8 | 10.9 | 0.996 | 45% | 96% |
| `KZ-PAV` | Pavlodar Region | 4.2% | yes | 15.6 | -7.7 | 0.987 | 38% | 94% |
| `KZ-ZHA` | Jambyl Region | 3.8% | yes | 15.8 | 3.4 | 0.985 | 49% | 92% |
| `KZ-YUZ` | South Kazakhstan Region | 2.5% | yes | 19.9 | -8.8 | 0.972 | 50% | 94% |
| `KZ-ATY` | Atyrau Region | 2.1% | yes | 19.2 | 1.9 | 0.986 | 46% | 91% |
| `KZ-MAN` | Mangystau Region | 0.0% | no | 80.2 | -75.3 | 0.589 | 30% | 89% |
| `KZ-ALA` | Almaty | 0.0% | no | 86.1 | -83.2 | 0.624 | 33% | 97% |
| `KZ-AST` | Astana | 0.0% | no | 71.0 | -50.2 | 0.727 | 64% | 99% |

## 3. The 2012 jump

Step ratio = mean(2012–2014) / mean(2009–2011) of annual totals. MODIS-only is the same instrument on both sides, so its step is the real change; excess = series step / MODIS step. Pettitt test on log annual totals.

| series | step ratio | excess vs MODIS | Pettitt change after | Pettitt p |
|---|---|---|---|---|
| naive_points | ×2.76 | ×3.12 | 2021 | 0.6283 |
| naive_cell_days | ×1.58 | ×1.79 | 2020 | 0.1883 |
| harmonized | ×0.92 | ×1.05 | 2010 | 0.0022 |
| modis_only_reference | ×0.88 | ×1.00 | 2010 | 0.0032 |

Monthly step regression, 2003–2019 (log1p series ~ month dummies + linear trend + step at 2012; Newey-West 95% CI, 12 lags). A sensor artefact shows as a step whose CI excludes 1; MODIS-only is the same-instrument reference.

| series | step factor | 95% CI | CI includes 1 |
|---|---|---|---|
| naive_points | ×2.65 | 1.50–4.65 | no |
| harmonized | ×0.79 | 0.50–1.27 | yes |
| modis_only_reference | ×0.71 | 0.38–1.33 | yes |

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
| Kostanay forest and steppe fires (Auliekol) | 2022-09 | 162 | 140 | 11 / 26 | 75 / 222 |
| Abai region forest fire (Semey Ormany) | 2023-06 | 222 | 12 | 1 / 26 | 9 / 207 |

## Coefficients

![coefficients](coefficients.png)

![raw series](raw_series.png)

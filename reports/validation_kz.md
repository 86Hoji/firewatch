# Validation — Kazakhstan

Calibration 2012–2019, holdout 2020–2025. Unit: H3 res 7 cell-days, VIIRS S-NPP equivalent. Selected model: **poisson_log**.

## Summary / Вывод

**EN.** On years the model never saw (2020–2025), harmonized MODIS reproduces observed VIIRS S-NPP monthly fire activity with R = 0.984 and total bias -2.6%. The naive MODIS→VIIRS splice jumps ×2.76 at 2012, while MODIS alone changes ×0.88; after harmonization the step is ×0.92.

**RU.** На годах, которых модель не видела (2020–2025), гармонизированный MODIS воспроизводит наблюдаемую активность VIIRS S-NPP по месяцам с R = 0.984 и суммарным смещением -2.6%. Наивная склейка MODIS→VIIRS даёт скачок ×2.76 в 2012 году, хотя сам MODIS меняется лишь в ×0.88; после гармонизации скачок ×0.92.

![before/after](before_after.png)

## 0. Model choice

Protocol fixed before running: [model_protocol.md](model_protocol.md); all candidates: [model_comparison.md](model_comparison.md). Selected **C2** (Terra∪Aqua, Poisson log-link): backcast 2016–19→2012–15 MAE 6.9%, leave-one-region-out 13.5%, leave-one-year-out 6.4%. 90% intervals sized at the predicted level: country coverage (leave-one-year-out) 89%, region coverage (leave-one-region-out) 48% before → 92% after.

## 1. Temporal holdout

| model | period | MAE | MAE % mean | bias % | median rel. bias % | Pearson R | Spearman ρ | coverage (pred. 90%) | coverage (bootstrap CI) |
|---|---|---|---|---|---|---|---|---|---|
| ratio | in_sample | 183.8 | 5.9 | 0.0 | -2.1 | 0.997 | 0.996 | 93% | — |
| loglog | in_sample | 195.2 | 6.3 | 0.5 | 2.0 | 0.996 | 0.994 | 91% | — |
| poisson_log | in_sample | 182.8 | 5.9 | 0.0 | 1.7 | 0.997 | 0.994 | 93% | — |
| ratio | holdout | 241.3 | 13.4 | -8.5 | -13.1 | 0.981 | 0.990 | 69% | 19% |
| loglog | holdout | 187.7 | 10.4 | -2.7 | -1.7 | 0.983 | 0.992 | 88% | 24% |
| poisson_log | holdout | 180.3 | 10.0 | -2.6 | -1.8 | 0.984 | 0.993 | 86% | 22% |

Holdout by season (selected model):

| season | MAE % mean | bias % | R | coverage |
|---|---|---|---|---|
| DJF | 37.2 | 24.0 | 0.994 | 89% |
| JJA | 7.4 | 3.1 | 0.993 | 100% |
| MAM | 11.5 | -6.2 | 0.971 | 61% |
| SON | 6.7 | -1.4 | 0.995 | 94% |

Holdout by year (watch for MODIS orbit drift):

| year | observed | harmonized MODIS | bias % |
|---|---|---|---|
| 2020 | 34576 | 35808 | 3.6 |
| 2021 | 28998 | 29514 | 1.8 |
| 2022 | 21390 | 18615 | -13.0 |
| 2023 | 17187 | 16285 | -5.2 |
| 2024 | 8928 | 8332 | -6.7 |
| 2025 | 18988 | 18141 | -4.5 |

![holdout](holdout.png)

Intervals (since C3): sized at the level being predicted. Country totals: leave-one-year-out log errors, width shrinking with size (coverage above). Regions: percentiles of leave-one-region-out errors for predictions of similar size (section 2). `n_harm_ci_*` = bootstrap over years of the coefficients only, expected to under-cover single months.

## 2. Spatial cross-validation (leave-one-ADM1-region-out)

Computed once in `experiments.py` (T3) for the selected model: fit 2012–2019 without the region, predict it over the same years. Multipliers use whole-country MODIS totals (input data, as in production). Median over the 13 regions with ≥ 1% of MODIS activity: MAE 13.5%, bias 0.6%. Coverage of the 90% interval over all region-months: before 48%, after 92%.

| region | name | share of MODIS | in median | MAE % mean | bias % | R | coverage before | coverage after |
|---|---|---|---|---|---|---|---|---|
| `KZ-KUS` | Kostanay Region | 12.7% | yes | 10.4 | -2.7 | 0.991 | 67% | 93% |
| `KZ-SEV` | North Kazakhstan Region | 12.3% | yes | 10.0 | 0.6 | 0.997 | 59% | 94% |
| `KZ-KAR` | Karaganda Region | 12.2% | yes | 11.4 | 1.0 | 0.994 | 55% | 96% |
| `KZ-AKM` | Akmola Region | 10.5% | yes | 11.5 | 3.2 | 0.997 | 61% | 96% |
| `KZ-KZY` | Kyzylorda Region | 10.0% | yes | 18.2 | 3.9 | 0.979 | 40% | 75% |
| `KZ-ALM` | Almaty Region | 8.4% | yes | 12.7 | -7.0 | 0.990 | 57% | 93% |
| `KZ-VOS` | East Kazakhstan Region | 7.7% | yes | 13.5 | -0.9 | 0.985 | 51% | 94% |
| `KZ-AKT` | Aktobe Region | 7.6% | yes | 13.2 | -6.8 | 0.993 | 43% | 85% |
| `KZ-ZAP` | West Kazakhstan Region | 6.0% | yes | 17.6 | 11.9 | 0.996 | 42% | 97% |
| `KZ-PAV` | Pavlodar Region | 4.2% | yes | 16.5 | -9.9 | 0.987 | 35% | 93% |
| `KZ-ZHA` | Jambyl Region | 3.8% | yes | 16.2 | 3.5 | 0.985 | 48% | 92% |
| `KZ-YUZ` | South Kazakhstan Region | 2.5% | yes | 21.9 | -10.7 | 0.968 | 47% | 92% |
| `KZ-ATY` | Atyrau Region | 2.1% | yes | 19.6 | 1.5 | 0.985 | 46% | 92% |
| `KZ-MAN` | Mangystau Region | 0.0% | no | 84.1 | -82.1 | 0.652 | 21% | 77% |
| `KZ-ALA` | Almaty | 0.0% | no | 84.7 | -82.8 | 0.622 | 34% | 99% |
| `KZ-AST` | Astana | 0.0% | no | 71.0 | -49.9 | 0.726 | 64% | 99% |

## 3. The 2012 jump

Step ratio = mean(2012–2014) / mean(2009–2011) of annual totals. MODIS-only is the same instrument on both sides, so its step is the real change; excess = series step / MODIS step. Pettitt test on log annual totals.

| series | step ratio | excess vs MODIS | Pettitt change after | Pettitt p |
|---|---|---|---|---|
| naive_points | ×2.76 | ×3.13 | 2011 | 0.6815 |
| naive_cell_days | ×1.59 | ×1.80 | 2020 | 0.2116 |
| harmonized | ×0.92 | ×1.04 | 2010 | 0.0022 |
| modis_only_reference | ×0.88 | ×1.00 | 2010 | 0.0032 |

Monthly step regression, 2003–2019 (log1p series ~ month dummies + linear trend + step at 2012; Newey-West 95% CI, 12 lags). A sensor artefact shows as a step whose CI excludes 1; MODIS-only is the same-instrument reference.

| series | step factor | 95% CI | CI includes 1 |
|---|---|---|---|
| naive_points | ×2.64 | 1.51–4.63 | no |
| harmonized | ×0.78 | 0.49–1.25 | yes |
| modis_only_reference | ×0.71 | 0.38–1.32 | yes |

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
| Kostanay forest and steppe fires (Auliekol) | 2022-09 | 162 | 141 | 11 / 26 | 76 / 222 |
| Abai region forest fire (Semey Ormany) | 2023-06 | 223 | 12 | 1 / 26 | 9 / 208 |

## Coefficients

![coefficients](coefficients.png)

![raw series](raw_series.png)

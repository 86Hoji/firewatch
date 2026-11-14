# Validation — Kazakhstan

Calibration 2012–2019, holdout 2020–2025. Unit: H3 res 7 cell-days, VIIRS S-NPP equivalent. Selected model: **poisson_log**.

## Summary / Вывод

**EN.** On years the model never saw (2020–2025), harmonized MODIS reproduces observed VIIRS S-NPP monthly fire activity with R = 0.984 and total bias -2.2%. The naive MODIS→VIIRS splice jumps ×2.82 at 2012, while MODIS alone changes ×0.89; after harmonization the step is ×0.92.

**RU.** На годах, которых модель не видела (2020–2025), гармонизированный MODIS воспроизводит наблюдаемую активность VIIRS S-NPP по месяцам с R = 0.984 и суммарным смещением -2.2%. Наивная склейка MODIS→VIIRS даёт скачок ×2.82 в 2012 году, хотя сам MODIS меняется лишь в ×0.89; после гармонизации скачок ×0.92.

![before/after](before_after.png)

## 0. Model choice

Protocol fixed before running: [model_protocol.md](model_protocol.md); all candidates: [model_comparison.md](model_comparison.md). Selected **C2** (Terra∪Aqua, Poisson log-link): backcast 2016–19→2012–15 MAE 6.9%, leave-one-region-out 18.5%, leave-one-year-out 6.5%. 90% intervals sized at the predicted level: country coverage (leave-one-year-out) 90%, region coverage (leave-one-region-out) 44% before → 91% after.

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

Intervals (since C3): sized at the level being predicted. Country totals: leave-one-year-out log errors, width shrinking with size (coverage above). Regions: percentiles of leave-one-region-out errors for predictions of similar size (section 2). `n_harm_ci_*` = bootstrap over years of the coefficients only, expected to under-cover single months.

## 2. Spatial cross-validation (leave-one-ADM1-region-out)

Computed once in `experiments.py` (T3) for the selected model: fit 2012–2019 without the region, predict it over the same years. Multipliers use whole-country MODIS totals (input data, as in production). Median over the 13 regions with ≥ 1% of MODIS activity: MAE 18.5%, bias 0.2%. Coverage of the 90% interval over all region-months: before 44%, after 91%.

| region | name | share of MODIS | in median | MAE % mean | bias % | R | coverage before | coverage after |
|---|---|---|---|---|---|---|---|---|
| `KZ-KUS` | Kostanay Region | 12.7% | yes | 10.0 | 0.2 | 0.992 | 67% | 97% |
| `KZ-KAR` | Karaganda Region | 12.2% | yes | 12.9 | 2.3 | 0.992 | 49% | 95% |
| `KZ-SEV` | North Kazakhstan Region | 12.2% | yes | 10.2 | 2.6 | 0.998 | 60% | 96% |
| `KZ-AKM` | Akmola Region | 10.4% | yes | 12.0 | 5.5 | 0.997 | 64% | 100% |
| `KZ-KZY` | Kyzylorda Region | 10.1% | yes | 21.8 | 1.5 | 0.975 | 29% | 73% |
| `KZ-ALM` | Almaty Region | 8.3% | yes | 13.0 | -4.0 | 0.989 | 58% | 97% |
| `KZ-AKT` | Aktobe Region | 7.7% | yes | 18.5 | -15.1 | 0.989 | 23% | 74% |
| `KZ-VOS` | East Kazakhstan Region | 7.7% | yes | 14.1 | -1.3 | 0.983 | 52% | 91% |
| `KZ-ZAP` | West Kazakhstan Region | 6.0% | yes | 19.9 | 13.5 | 0.994 | 36% | 97% |
| `KZ-PAV` | Pavlodar Region | 4.2% | yes | 20.9 | -15.2 | 0.984 | 21% | 92% |
| `KZ-ZHA` | Jambyl Region | 3.8% | yes | 18.9 | 6.7 | 0.983 | 44% | 91% |
| `KZ-YUZ` | South Kazakhstan Region | 2.5% | yes | 24.3 | -7.4 | 0.955 | 49% | 91% |
| `KZ-ATY` | Atyrau Region | 2.1% | yes | 24.8 | -7.6 | 0.974 | 32% | 95% |
| `KZ-MAN` | Mangystau Region | 0.1% | no | 84.2 | -83.2 | 0.526 | 16% | 74% |
| `KZ-ALA` | Almaty | 0.0% | no | 84.9 | -82.8 | 0.612 | 35% | 100% |
| `KZ-AST` | Astana | 0.0% | no | 70.7 | -48.4 | 0.721 | 65% | 99% |

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

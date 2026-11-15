# Model comparison (protocol: baseline/model_protocol.md; regions = ADM1 since C3)

MAE as % of the mean monthly total; bias = total over the test period. Score = mean MAE % of T1, T3, T4. T3 = median over the 13 ADM1 regions with ≥ 1% of MODIS activity (of 16).

T5 (extrapolation, reported only): per calendar month, fit on the 2012–2019 years whose MODIS total is at or below the month's 75th percentile, predict the busier years.

| id | model | params | **score** | T1 backcast MAE / bias | T3 LORO MAE / median bias | T4 LOYO MAE / bias | T2 forecast MAE / bias (drift) | T5 extrapolation MAE / bias |
|---|---|---|---|---|---|---|---|---|
| C2 ✔ | Terra∪Aqua, Poisson log-link | 2 | **8.90** | 6.9 / -2.2 | 13.5 / 0.6 | 6.4 / 0.1 | 10.0 / -2.6 | 7.3 / 3.5 |
| C1 | Terra∪Aqua, OLS log1p (v1) | 2 | **9.03** | 7.6 / -1.2 | 13.4 / 1.6 | 6.1 / -0.2 | 10.4 / -2.7 | 8.1 / 3.0 |
| C0 | Terra∪Aqua, ratio | 1 | **10.24** | 8.2 / -3.0 | 15.3 / 0.5 | 7.2 / 0.7 | 13.4 / -8.5 | 10.9 / 10.7 |
| C3 | Terra∪Aqua day+night, ratio | 2 | **10.40** | 7.5 / -1.9 | 16.7 / 0.2 | 7.0 / 0.6 | 12.1 / -3.0 | 10.2 / 8.6 |
| C4 | Aqua, ratio | 1 | **12.93** | 10.4 / -4.0 | 18.9 / 2.0 | 9.5 / 0.8 | 16.8 / -12.0 | 13.7 / 13.0 |
| C5 | Aqua day+night, ratio | 2 | **13.23** | 9.7 / -2.0 | 20.8 / 0.5 | 9.1 / 0.5 | 17.5 / -6.3 | 11.9 / 11.3 |
| C6 | Aqua, Poisson log-link | 2 | **13.67** | 11.7 / -2.1 | 18.2 / -2.7 | 11.1 / 0.4 | 15.9 / -3.2 | 12.1 / 4.5 |
| C7 | Aqua day+night, Poisson log-link | 4 | **15.06** | 12.7 / 0.3 | 20.9 / 2.4 | 11.5 / 1.3 | 16.2 / 1.8 | 12.4 / 7.4 |

Selected by the protocol rule: **C2** (Terra∪Aqua, Poisson log-link).

## 90% intervals: before (baseline) vs after (conformal, sized at the predicted level)

Country: baseline interval (leave-one-year-out log errors, width shrinking with size). Region: percentiles of leave-one-region-out errors for predictions of similar size. Coverage is cross-fitted: the interval for a held-out year/region is fitted on the others only.

| test | before | after |
|---|---|---|
| T3 leave-one-region-out, region-months | 48% | 92% |
| T1 backcast, country | 96% | 96% |
| T2 holdout 2020+ (drift), country | 86% | 86% |
| T4 leave-one-year-out, country | 89% | 89% |

## How sure is the choice?

Paired bootstrap over calibration years (1000 draws): score of each model minus the selected **C2**, with a 90% interval, and how often each model would have the best score. An interval that contains 0 means the data cannot tell the two apart; the parsimony rule then decides.

| id | score − selected (median) | interval | wins |
|---|---|---|---|
| C2 | 0.00 | 0.00 … 0.00 | 62% |
| C1 | 0.11 | -0.28 … 0.61 | 33% |
| C0 | 0.99 | 0.11 … 1.83 | 2% |
| C3 | 1.15 | 0.11 … 2.45 | 3% |
| C4 | 3.79 | 2.50 … 5.28 | 0% |
| C5 | 3.92 | 2.64 … 5.62 | 0% |
| C6 | 4.59 | 3.75 … 5.35 | 0% |
| C7 | 6.19 | 4.80 … 7.31 | 0% |

## Extrapolation: the product predicts busier years than it was fitted on

2003–2011: 34% of months have more MODIS cell-days than the same calendar month in any calibration year (median ratio to that maximum 0.69, largest 17.65); busiest year 56694 vs busiest calibration year 36054.

Annual totals each candidate would give for 2003–2011 (VIIRS S-NPP-equivalent cell-days; % = difference from the selected C2). The spread is model (structural) uncertainty that the 90% interval does not contain. Computed with `pipeline/models.py` on country totals, like T1–T5; the published series comes from `calib.py` (same model, plus land-cover strata if present), so the selected column can differ slightly from `n_harm`.

| year | C0 | C1 | C2 |
|---|---|---|---|
| 2003 | 96780 (+15.0%) | 83253 (-1.1%) | 84190 |
| 2004 | 94724 (+15.6%) | 82934 (+1.2%) | 81932 |
| 2005 | 62611 (+8.8%) | 56931 (-1.1%) | 57539 |
| 2006 | 72702 (+11.3%) | 65124 (-0.3%) | 65296 |
| 2007 | 51056 (+6.7%) | 47186 (-1.4%) | 47863 |
| 2008 | 73963 (+6.3%) | 70801 (+1.7%) | 69593 |
| 2009 | 38916 (+0.8%) | 38357 (-0.6%) | 38608 |
| 2010 | 57043 (+7.2%) | 53363 (+0.3%) | 53218 |
| 2011 | 22597 (-6.9%) | 24125 (-0.6%) | 24271 |
| **total** | 570393 (+9.2%) | 522075 (-0.1%) | 522511 |

All 8 candidates: total from -0.1% to +11.6% vs the selected model.

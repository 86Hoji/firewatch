# Model comparison (protocol: baseline/model_protocol.md; regions = ADM1 since C3)

MAE as % of the mean monthly total; bias = total over the test period. Score = mean MAE % of T1, T3, T4. T3 = median over the 13 ADM1 regions with ≥ 1% of MODIS activity (of 16).

| id | model | params | **score** | T1 backcast MAE / bias | T3 LORO MAE / median bias | T4 LOYO MAE / bias | T2 forecast MAE / bias (drift) |
|---|---|---|---|---|---|---|---|
| C2 ✔ | Terra∪Aqua, Poisson log-link | 2 | **10.63** | 6.9 / -2.1 | 18.5 / 0.2 | 6.5 / 0.1 | 10.3 / -2.2 |
| C1 | Terra∪Aqua, OLS log1p (v1) | 2 | **10.97** | 7.8 / -1.2 | 18.8 / 0.6 | 6.4 / -0.4 | 10.6 / -2.3 |
| C0 | Terra∪Aqua, ratio | 1 | **11.79** | 8.9 / -3.3 | 18.5 / -0.6 | 8.0 / 0.8 | 14.8 / -9.3 |
| C3 | Terra∪Aqua day+night, ratio | 2 | **12.24** | 7.9 / -1.7 | 21.3 / 3.2 | 7.5 / 0.7 | 13.3 / -4.1 |
| C5 | Aqua day+night, ratio | 2 | **14.59** | 10.0 / -2.1 | 24.1 / 1.2 | 9.6 / 0.5 | 18.3 / -7.6 |
| C4 | Aqua, ratio | 1 | **14.62** | 10.8 / -4.3 | 23.1 / -1.2 | 10.0 / 0.8 | 18.3 / -12.8 |
| C6 | Aqua, Poisson log-link | 2 | **14.71** | 11.7 / -2.1 | 21.3 / -1.9 | 11.1 / 0.3 | 16.2 / -2.8 |
| C7 | Aqua day+night, Poisson log-link | 4 | **15.77** | 12.5 / 0.2 | 23.5 / 5.1 | 11.3 / 1.3 | 16.4 / 2.1 |

Selected by the protocol rule: **C2** (Terra∪Aqua, Poisson log-link).

## 90% intervals: before (baseline) vs after (negative binomial at the predicted level)

Country: baseline interval (leave-one-year-out log errors, width shrinking with size). Region: percentiles of leave-one-region-out errors for predictions of similar size. Coverage is cross-fitted: the interval for a held-out year/region is fitted on the others only.

| test | before | after |
|---|---|---|
| T3 leave-one-region-out, region-months | 44% | 91% |
| T1 backcast, country | 94% | 94% |
| T2 holdout 2020+ (drift), country | 83% | 83% |
| T4 leave-one-year-out, country | 90% | 90% |

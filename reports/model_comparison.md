# Model comparison (protocol: baseline/model_protocol.md; regions = ADM1 since C3)

MAE as % of the mean monthly total; bias = total over the test period. Score = mean MAE % of T1, T3, T4. T3 = median over the 13 ADM1 regions with ≥ 1% of MODIS activity (of 16).

| id | model | params | **score** | T1 backcast MAE / bias | T3 LORO MAE / median bias | T4 LOYO MAE / bias | T2 forecast MAE / bias (drift) |
|---|---|---|---|---|---|---|---|
| C2 ✔ | Terra∪Aqua, Poisson log-link | 2 | **8.94** | 7.0 / -2.5 | 13.5 / 0.4 | 6.4 / 0.2 | 9.8 / -0.9 |
| C1 | Terra∪Aqua, OLS log1p (v1) | 2 | **9.03** | 7.7 / -1.5 | 13.3 / 1.5 | 6.1 / -0.1 | 10.2 / -1.1 |
| C0 | Terra∪Aqua, ratio | 1 | **9.91** | 8.2 / -3.3 | 14.3 / 0.2 | 7.2 / 0.6 | 12.3 / -6.7 |
| C3 | Terra∪Aqua day+night, ratio | 2 | **10.28** | 7.4 / -2.3 | 16.3 / -0.1 | 7.1 / 0.6 | 11.6 / -1.2 |
| C4 | Aqua, ratio | 1 | **12.87** | 10.4 / -4.3 | 18.7 / 1.6 | 9.5 / 0.7 | 16.0 / -10.3 |
| C5 | Aqua day+night, ratio | 2 | **13.13** | 9.7 / -2.4 | 20.6 / -0.2 | 9.1 / 0.5 | 17.1 / -4.6 |
| C6 | Aqua, Poisson log-link | 2 | **13.79** | 11.8 / -2.5 | 18.5 / -2.9 | 11.1 / 0.5 | 16.1 / -1.6 |
| C7 | Aqua day+night, Poisson log-link | 4 | **15.39** | 12.8 / -0.5 | 21.9 / 2.5 | 11.5 / 1.4 | 16.9 / 3.5 |

Selected by the protocol rule: **C2** (Terra∪Aqua, Poisson log-link).

## 90% intervals: before (baseline) vs after (negative binomial at the predicted level)

Country: baseline interval (leave-one-year-out log errors, width shrinking with size). Region: percentiles of leave-one-region-out errors for predictions of similar size. Coverage is cross-fitted: the interval for a held-out year/region is fitted on the others only.

| test | before | after |
|---|---|---|
| T3 leave-one-region-out, region-months | 50% | 92% |
| T1 backcast, country | 94% | 94% |
| T2 holdout 2020+ (drift), country | 92% | 92% |
| T4 leave-one-year-out, country | 89% | 89% |

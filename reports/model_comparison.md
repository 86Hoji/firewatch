# Model comparison (protocol: model_protocol.md)

MAE as % of the mean monthly total; bias = total over the test period. Score = mean MAE % of T1, T3, T4.

| id | model | params | **score** | T1 backcast MAE / bias | T3 LORO MAE / median bias | T4 LOYO MAE / bias | T2 forecast MAE / bias (drift) |
|---|---|---|---|---|---|---|---|
| C2 ✔ | Terra∪Aqua, Poisson log-link | 2 | **9.68** | 6.9 / -2.1 | 15.6 / -1.6 | 6.5 / 0.1 | 10.3 / -2.2 |
| C1 | Terra∪Aqua, OLS log1p (v1) | 2 | **9.81** | 7.8 / -1.2 | 15.3 / -2.4 | 6.4 / -0.4 | 10.6 / -2.3 |
| C3 | Terra∪Aqua day+night, ratio | 2 | **10.55** | 7.9 / -1.7 | 16.2 / 3.1 | 7.5 / 0.7 | 13.3 / -4.1 |
| C0 | Terra∪Aqua, ratio | 1 | **11.31** | 8.9 / -3.3 | 17.0 / 1.0 | 8.0 / 0.8 | 14.8 / -9.3 |
| C5 | Aqua day+night, ratio | 2 | **12.58** | 10.0 / -2.1 | 18.1 / 2.4 | 9.6 / 0.5 | 18.3 / -7.6 |
| C4 | Aqua, ratio | 1 | **13.29** | 10.8 / -4.3 | 19.1 / 1.3 | 10.0 / 0.8 | 18.3 / -12.8 |
| C6 | Aqua, Poisson log-link | 2 | **14.82** | 11.7 / -2.1 | 21.7 / -5.8 | 11.1 / 0.3 | 16.2 / -2.8 |
| C7 | Aqua day+night, Poisson log-link | 4 | **15.87** | 12.5 / 0.2 | 23.8 / 5.8 | 11.3 / 1.3 | 16.4 / 2.1 |

Selected by the protocol rule: **C2** (Terra∪Aqua, Poisson log-link).
## Prediction intervals for the selected model (T1 + T4)

| method | coverage of 90% | T1 | T4 | median width, % of prediction |
|---|---|---|---|---|
| season | 81% | 71% | 85% | 33% |
| hetero ✔ | 90% | 94% | 89% | 34% |

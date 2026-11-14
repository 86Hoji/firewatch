# Model comparison (protocol: model_protocol.md)

MAE as % of the mean monthly total; bias = total over the test period. Score = mean MAE % of T1, T3, T4.

| id | model | params | **score** | T1 backcast MAE / bias | T3 LORO MAE / median bias | T4 LOYO MAE / bias | T2 forecast MAE / bias (drift) |
|---|---|---|---|---|---|---|---|
| C2 ✔ | Terra∪Aqua, Poisson log-link | 2 | **9.54** | 7.0 / -2.0 | 15.3 / -1.4 | 6.3 / 0.1 | 10.3 / -3.2 |
| C1 | Terra∪Aqua, OLS log1p (v1) | 2 | **9.64** | 7.7 / -1.1 | 14.9 / -1.9 | 6.2 / -0.2 | 10.7 / -3.5 |
| C3 | Terra∪Aqua day+night, ratio | 2 | **10.50** | 7.8 / -1.4 | 16.4 / 2.2 | 7.3 / 0.7 | 13.2 / -5.0 |
| C0 | Terra∪Aqua, ratio | 1 | **11.00** | 8.7 / -3.1 | 16.5 / 1.1 | 7.8 / 0.7 | 15.0 / -10.1 |
| C5 | Aqua day+night, ratio | 2 | **12.60** | 10.0 / -1.7 | 18.4 / 2.6 | 9.5 / 0.6 | 18.2 / -8.7 |
| C4 | Aqua, ratio | 1 | **12.95** | 10.7 / -4.2 | 18.4 / 1.4 | 9.7 / 0.8 | 18.3 / -13.5 |
| C6 | Aqua, Poisson log-link | 2 | **14.60** | 11.7 / -2.0 | 21.1 / -6.0 | 11.0 / 0.3 | 15.9 / -3.6 |
| C7 | Aqua day+night, Poisson log-link | 4 | **15.20** | 12.4 / 0.7 | 21.9 / 7.0 | 11.3 / 1.4 | 16.2 / 1.4 |

Selected by the protocol rule: **C2** (Terra∪Aqua, Poisson log-link).
## Prediction intervals for the selected model (T1 + T4)

| method | coverage of 90% | T1 | T4 | median width, % of prediction |
|---|---|---|---|---|
| season | 81% | 73% | 85% | 31% |
| hetero ✔ | 90% | 94% | 88% | 35% |

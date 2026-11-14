# Model comparison protocol (fixed before running, 2026-11-14)

Why a second protocol: v1 chose the model on the 2020–2025 forecast holdout only. That period is affected by Terra
(from Feb 2020) and Aqua (from 2021–22) orbit drift, and it tests the model *forward* in time, while the product applies
it *backward* (2000–2011). v2 adds drift-free tests that mimic the real use. v1 results stay in the report.

## Target and unit
Monthly regional totals of VIIRS S-NPP cell-days (+ NOAA-20 outage fill), H3 res 7. Kazakhstan, no land-cover strata.

## Tests
- **T1 backcast** (direction of use): fit 2016–2019 → predict 2012–2015.
- **T2 forecast holdout**: fit 2012–2019 → predict 2020–2025 (drift-affected; reported, not used for selection).
- **T3 leave-one-region-out**: fit 2012–2019 without one H3 res-1 subregion → predict that subregion 2012–2019.
  Multipliers that depend on totals use whole-region MODIS totals (input data). Median over subregions.
- **T4 leave-one-year-out** within 2012–2019: each year predicted from the other seven.

## Score and rule
Primary score = mean of MAE % of mean over T1, T3, T4. Lowest score wins; if within 0.5 percentage points of the best,
the model with fewer parameters per stratum wins. Bias and R are reported for every test.

## Candidates
| id | predictor | model |
|---|---|---|
| C0 | MODIS Terra∪Aqua | ratio V = k·M (Poisson MLE, identity link) |
| C1 | MODIS Terra∪Aqua | OLS on log1p, smearing (current v1 choice) |
| C2 | MODIS Terra∪Aqua | Poisson GLM, log link: E[V] = exp(a)·(M+1)^b |
| C3 | MODIS day, night | V = k_d·M_d + k_n·M_n (Poisson MLE, k ≥ 0) |
| C4 | Aqua | ratio V = k·M_aqua |
| C5 | Aqua day, night | V = k_d·A_d + k_n·A_n |
| C6 | Aqua | Poisson GLM, log link |
| C7 | Aqua day, night | Poisson GLM, log link, separate day and night: E[V] = exp(a_d)(A_d+1)^b_d + exp(a_n)(A_n+1)^b_n |

Strata: month → season → region fallback when Σpredictor < `min_count` (log-link models also need ≥ 12 points).
Aqua-based models need a Terra→Aqua bridge for Nov 2000 – Jun 2002 (fit 2003–2011, same family); this affects only
the production series, not the tests above.

## Intervals (after the point model is chosen)
Candidates: (a) LOYO conformal on log ratio per season (current); (b) LOYO conformal on log ratio pooled over all
months, scaled by 1/sqrt(predicted) relative to the median (heteroscedastic). Choose the one whose coverage of the
nominal 90% interval is closest to 90% on T1 + T4 combined.

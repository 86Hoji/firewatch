# Kazakhstan: what moved

| metric | Phase B | after C3 | now |
|---|---|---|---|
| hotspots after cleaning | 3,171,270 | 3,171,270 | 3,172,931 |
| removed as static (type != 0) | 482,852 | 482,852 | 482,852 |
| NRT removed by static mask | 13,750 | 13,750 | 12,089 |
| static mask cells | 189 | 189 | 91 |
| selected model | C2 (poisson_log) | C2 (poisson_log) | C2 (poisson_log) |
| step ratio 2012: naive points | 2.824 | 2.824 | 2.824 |
| step ratio 2012: naive cell-days | 1.647 | 1.647 | 1.647 |
| step ratio 2012: harmonized | 0.924 | 0.924 | 0.924 |
| step ratio 2012: MODIS alone | 0.886 | 0.886 | 0.886 |
| harmonized jump vs MODIS alone | 1.042 | 1.042 | 1.042 |
| monthly step factor, harmonized | 0.861 | 0.861 | 0.861 |
| backcast T1 MAE % | 6.927 | 6.927 | 6.927 |
| backcast T1 bias % | -2.146 | -2.146 | -2.146 |
| leave-one-year-out T4 MAE % | 6.453 | 6.453 | 6.453 |
| holdout 2020+ MAE % | 10.3 | 10.3 | 10.3 |
| holdout 2020+ bias % | -2.207 | -2.207 | -2.178 |
| holdout 2020+ coverage | 0.833 | 0.833 | 0.833 |
| LORO MAE % (median region) | 17.3 | 18.5 | 18.5 |
| LORO coverage (region-months) | 0.405 | 0.912 | 0.912 |
| model score (mean T1, T3, T4) | 9.675 | 10.6 | 10.6 |

Phase B LORO used H3 res-1 hexagons without zero months; since C3 it uses ADM1 oblasts with zero months and the region-level interval (not comparable one-to-one).

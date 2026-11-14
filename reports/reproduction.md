# Reproduction of the baseline — Kazakhstan

His numbers: `reports/baseline/`. Ours: `reports/`. Flag = difference > 2%.

| metric | his | ours | diff % | > 2% |
|---|---|---|---|---|
| naive points step | 2.807 | 2.824 | +0.62 |  |
| naive cell-day step | 1.634 | 1.647 | +0.80 |  |
| MODIS-only step | 0.887 | 0.886 | -0.12 |  |
| harmonized step | 0.924 | 0.924 | -0.01 |  |
| monthly step regression, naive | 3.194 | 3.231 | +1.13 |  |
| monthly step regression, harmonized | 0.862 | 0.861 | -0.05 |  |
| backcast MAE % (T1) | 6.975 | 6.927 | -0.68 |  |
| holdout MAE % | 10.346 | 10.314 | -0.31 |  |
| holdout bias % | -3.233 | -2.207 | -31.74 | ⚠ |
| holdout Pearson R | 0.984 | 0.984 | -0.01 |  |
| LORO median MAE % | 16.849 | 17.262 | +2.45 | ⚠ |
| LORO interval coverage | 0.402 | 0.405 | +0.75 |  |
| Terra/Aqua cell-day ratio 2003–2021 (min) | 0.860 | 0.859 | -0.08 |  |
| Terra/Aqua cell-day ratio 2003–2021 (max) | 1.020 | 1.023 | +0.25 |  |

Terra/Aqua cell-day ratio by year (ours):

| year | Terra / Aqua |
|---|---|
| 2002 | 1.467 |
| 2003 | 0.862 |
| 2004 | 0.941 |
| 2005 | 0.965 |
| 2006 | 0.995 |
| 2007 | 0.923 |
| 2008 | 0.954 |
| 2009 | 0.938 |
| 2010 | 0.973 |
| 2011 | 0.870 |
| 2012 | 0.986 |
| 2013 | 0.859 |
| 2014 | 1.016 |
| 2015 | 1.009 |
| 2016 | 0.915 |
| 2017 | 1.023 |
| 2018 | 0.928 |
| 2019 | 1.003 |
| 2020 | 0.953 |
| 2021 | 1.010 |
| 2022 | 1.359 |
| 2023 | 0.872 |
| 2024 | 0.759 |
| 2025 | 0.617 |
| 2026 | 0.521 |

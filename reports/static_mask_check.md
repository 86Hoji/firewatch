# Static-source mask: honest test

Every mask is built ONLY from archive rows before 2025-01-01; tested on archive rows 2025-01-01 … 2026-07-31 (which carry the true FIRMS `type`). A detection counts as "caught" if it falls in a masked H3 cell.

## Does the mask catch static sources (type = 2)?

| country | rule | precision | recall | F1 | test rows | of which type 2 |
|---|---|---|---|---|---|---|
| KAZ | production: type-2 rule, last 5 y | 93.9% | 88.4% | 0.911 | 235,202 | 46,396 (19.7%) |
| KAZ | C2 mask (both rules, all history) | 88.6% | 96.1% | 0.922 | 235,202 | 46,396 (19.7%) |
| KAZ | type-2 rule, all history | 92.2% | 88.7% | 0.904 | 235,202 | 46,396 (19.7%) |
| KAZ | persistent rule only | 88.9% | 95.4% | 0.920 | 235,202 | 46,396 (19.7%) |
| UZB | production: type-2 rule, last 5 y | 94.0% | 74.7% | 0.832 | 82,161 | 24,548 (29.9%) |
| UZB | C2 mask (both rules, all history) | 84.2% | 76.4% | 0.801 | 82,161 | 24,548 (29.9%) |
| UZB | type-2 rule, all history | 87.1% | 74.7% | 0.804 | 82,161 | 24,548 (29.9%) |
| UZB | persistent rule only | 85.0% | 75.6% | 0.800 | 82,161 | 24,548 (29.9%) |
| TKM | production: type-2 rule, last 5 y | 86.1% | 84.5% | 0.853 | 134,450 | 68,894 (51.2%) |
| TKM | C2 mask (both rules, all history) | 82.3% | 95.0% | 0.882 | 134,450 | 68,894 (51.2%) |
| TKM | type-2 rule, all history | 85.4% | 85.2% | 0.853 | 134,450 | 68,894 (51.2%) |
| TKM | persistent rule only | 82.4% | 89.2% | 0.857 | 134,450 | 68,894 (51.2%) |

## If the mask replaced `type`: change in monthly cell-days

Production keeps `type = 0`; the alternative drops masked cells and ignores `type`. Positive = the mask lets through more than `type` does (missed flares, or real fires `type` drops).

| country | rule | sensor | total change | median monthly abs. change | worst month |
|---|---|---|---|---|---|
| KAZ | production: type-2 rule, last 5 y | MODIS | +0.9% | 0.8% | 9.0% |
| KAZ | production: type-2 rule, last 5 y | NOAA20 | +2.4% | 3.9% | 52.4% |
| KAZ | production: type-2 rule, last 5 y | SNPP | +2.1% | 2.8% | 47.7% |
| KAZ | C2 mask (both rules, all history) | MODIS | +0.1% | 0.5% | 7.9% |
| KAZ | C2 mask (both rules, all history) | NOAA20 | -2.9% | 4.5% | 23.8% |
| KAZ | C2 mask (both rules, all history) | SNPP | -3.1% | 6.6% | 22.6% |
| KAZ | type-2 rule, all history | MODIS | +0.5% | 0.5% | 7.9% |
| KAZ | type-2 rule, all history | NOAA20 | +1.7% | 2.5% | 52.4% |
| KAZ | type-2 rule, all history | SNPP | +1.4% | 1.7% | 40.9% |
| UZB | production: type-2 rule, last 5 y | MODIS | +37.3% | 49.2% | 206.8% |
| UZB | production: type-2 rule, last 5 y | NOAA20 | +6.1% | 4.9% | 19.9% |
| UZB | production: type-2 rule, last 5 y | SNPP | +5.2% | 4.6% | 20.6% |
| UZB | C2 mask (both rules, all history) | MODIS | +35.4% | 42.5% | 213.6% |
| UZB | C2 mask (both rules, all history) | NOAA20 | +1.1% | 2.0% | 12.0% |
| UZB | C2 mask (both rules, all history) | SNPP | +0.3% | 3.3% | 12.5% |
| UZB | type-2 rule, all history | MODIS | +36.3% | 43.3% | 215.9% |
| UZB | type-2 rule, all history | NOAA20 | +4.0% | 2.0% | 17.8% |
| UZB | type-2 rule, all history | SNPP | +3.1% | 2.5% | 18.5% |
| TKM | production: type-2 rule, last 5 y | MODIS | -0.6% | 5.0% | 24.0% |
| TKM | production: type-2 rule, last 5 y | NOAA20 | -1.7% | 4.0% | 28.6% |
| TKM | production: type-2 rule, last 5 y | SNPP | -3.9% | 4.3% | 25.3% |
| TKM | C2 mask (both rules, all history) | MODIS | -5.7% | 9.1% | 32.8% |
| TKM | C2 mask (both rules, all history) | NOAA20 | -16.1% | 16.6% | 31.4% |
| TKM | C2 mask (both rules, all history) | SNPP | -18.5% | 18.5% | 36.8% |
| TKM | type-2 rule, all history | MODIS | -0.5% | 5.0% | 24.0% |
| TKM | type-2 rule, all history | NOAA20 | -3.6% | 4.8% | 25.5% |
| TKM | type-2 rule, all history | SNPP | -6.1% | 4.9% | 24.0% |

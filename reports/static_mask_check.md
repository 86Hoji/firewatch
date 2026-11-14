# Static-source mask: honest test

Mask built from archive rows before 2025-01-01; tested on archive rows 2025-01-01 … 2026-07-31 (which carry the true FIRMS `type`). A detection counts as "caught" if it falls in a masked H3 cell.

## Does the mask catch static sources (type = 2)?

| country | rule | precision | recall | F1 | test rows | of which type 2 |
|---|---|---|---|---|---|---|
| KAZ | mask as configured | 88.6% | 96.1% | 0.922 | 235,202 | 46,396 (19.7%) |
| KAZ | type-2 share rule only | 92.2% | 88.7% | 0.904 | 235,202 | 46,396 (19.7%) |
| KAZ | persistent rule only | 88.9% | 95.4% | 0.920 | 235,202 | 46,396 (19.7%) |
| UZB | mask as configured | 84.2% | 76.4% | 0.801 | 82,161 | 24,548 (29.9%) |
| UZB | type-2 share rule only | 87.1% | 74.7% | 0.804 | 82,161 | 24,548 (29.9%) |
| UZB | persistent rule only | 85.0% | 75.6% | 0.800 | 82,161 | 24,548 (29.9%) |
| TKM | mask as configured | 82.3% | 95.0% | 0.882 | 134,450 | 68,894 (51.2%) |
| TKM | type-2 share rule only | 85.4% | 85.2% | 0.853 | 134,450 | 68,894 (51.2%) |
| TKM | persistent rule only | 82.4% | 89.2% | 0.857 | 134,450 | 68,894 (51.2%) |

## If the mask replaced `type`: change in monthly cell-days

Production keeps `type = 0`; the alternative drops masked cells and ignores `type`. Positive = the mask lets through more than `type` does (missed flares, or real fires `type` drops).

| country | rule | sensor | total change | median monthly abs. change | worst month |
|---|---|---|---|---|---|
| KAZ | as configured | MODIS | +0.1% | 0.5% | 7.9% |
| KAZ | as configured | NOAA20 | -2.9% | 4.5% | 23.8% |
| KAZ | as configured | SNPP | -3.1% | 6.6% | 22.6% |
| KAZ | type-2 rule only | MODIS | +0.5% | 0.5% | 7.9% |
| KAZ | type-2 rule only | NOAA20 | +1.7% | 2.5% | 52.4% |
| KAZ | type-2 rule only | SNPP | +1.4% | 1.7% | 40.9% |
| UZB | as configured | MODIS | +35.4% | 42.5% | 213.6% |
| UZB | as configured | NOAA20 | +1.1% | 2.0% | 12.0% |
| UZB | as configured | SNPP | +0.3% | 3.3% | 12.5% |
| UZB | type-2 rule only | MODIS | +36.3% | 43.3% | 215.9% |
| UZB | type-2 rule only | NOAA20 | +4.0% | 2.0% | 17.8% |
| UZB | type-2 rule only | SNPP | +3.1% | 2.5% | 18.5% |
| TKM | as configured | MODIS | -5.7% | 9.1% | 32.8% |
| TKM | as configured | NOAA20 | -16.1% | 16.6% | 31.4% |
| TKM | as configured | SNPP | -18.5% | 18.5% | 36.8% |
| TKM | type-2 rule only | MODIS | -0.5% | 5.0% | 24.0% |
| TKM | type-2 rule only | NOAA20 | -3.6% | 4.8% | 25.5% |
| TKM | type-2 rule only | SNPP | -6.1% | 4.9% | 24.0% |

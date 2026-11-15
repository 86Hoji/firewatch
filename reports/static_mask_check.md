# Static-source mask: honest test

Every mask is built ONLY from archive rows before 2025-01-01; tested on archive rows 2025-01-01 … 2026-07-31 (which carry the true FIRMS `type`). A detection counts as "caught" if it falls in a masked H3 cell.

## Does the mask catch static sources (type = 2)?

| country | rule | precision | recall | F1 | test rows | of which type 2 |
|---|---|---|---|---|---|---|
| KAZ | production: type rule (last 5 y + all history) + static_site, built < 2020 | 86.6% | 81.0% | 0.837 | 235,202 | 46,396 (19.7%) |
| KAZ | previous production: type-2 rule, last 5 y | 91.9% | 88.8% | 0.904 | 235,202 | 46,396 (19.7%) |
| KAZ | C2 mask (both rules, all history) | 88.3% | 96.1% | 0.921 | 235,202 | 46,396 (19.7%) |
| KAZ | type rule, all history | 90.3% | 89.1% | 0.897 | 235,202 | 46,396 (19.7%) |
| KAZ | persistent rule only | 88.9% | 95.4% | 0.920 | 235,202 | 46,396 (19.7%) |
| UZB | production: type rule (last 5 y + all history) + static_site, built < 2020 | 83.8% | 64.5% | 0.729 | 82,161 | 24,548 (29.9%) |
| UZB | previous production: type-2 rule, last 5 y | 93.8% | 75.7% | 0.838 | 82,161 | 24,548 (29.9%) |
| UZB | C2 mask (both rules, all history) | 84.0% | 76.4% | 0.801 | 82,161 | 24,548 (29.9%) |
| UZB | type rule, all history | 86.9% | 75.7% | 0.809 | 82,161 | 24,548 (29.9%) |
| UZB | persistent rule only | 85.0% | 75.6% | 0.800 | 82,161 | 24,548 (29.9%) |
| TKM | production: type rule (last 5 y + all history) + static_site, built < 2020 | 81.7% | 82.3% | 0.820 | 134,450 | 68,894 (51.2%) |
| TKM | previous production: type-2 rule, last 5 y | 86.1% | 84.5% | 0.853 | 134,450 | 68,894 (51.2%) |
| TKM | C2 mask (both rules, all history) | 82.3% | 95.0% | 0.882 | 134,450 | 68,894 (51.2%) |
| TKM | type rule, all history | 85.4% | 85.2% | 0.853 | 134,450 | 68,894 (51.2%) |
| TKM | persistent rule only | 82.4% | 89.2% | 0.857 | 134,450 | 68,894 (51.2%) |

## If the mask replaced `type`: change in monthly cell-days

Production keeps `type = 0` (outside masked cells, as production now drops every row there); the alternative drops masked cells and ignores `type`. Positive = the mask lets through more than `type` does (missed flares, or real fires `type` drops).

| country | rule | sensor | total change | median monthly abs. change | worst month |
|---|---|---|---|---|---|
| KAZ | production: type rule (last 5 y + all history) + static_site, built < 2020 | MODIS | +1.2% | 1.3% | 13.1% |
| KAZ | production: type rule (last 5 y + all history) + static_site, built < 2020 | NOAA20 | +6.5% | 12.1% | 75.5% |
| KAZ | production: type rule (last 5 y + all history) + static_site, built < 2020 | SNPP | +6.4% | 12.2% | 106.9% |
| KAZ | previous production: type-2 rule, last 5 y | MODIS | +0.8% | 0.8% | 9.0% |
| KAZ | previous production: type-2 rule, last 5 y | NOAA20 | +1.7% | 2.5% | 52.4% |
| KAZ | previous production: type-2 rule, last 5 y | SNPP | +1.3% | 2.1% | 47.7% |
| KAZ | C2 mask (both rules, all history) | MODIS | +0.1% | 0.5% | 7.9% |
| KAZ | C2 mask (both rules, all history) | NOAA20 | -3.0% | 4.5% | 23.8% |
| KAZ | C2 mask (both rules, all history) | SNPP | -3.2% | 6.6% | 22.6% |
| KAZ | type rule, all history | MODIS | +0.5% | 0.5% | 7.9% |
| KAZ | type rule, all history | NOAA20 | +0.9% | 1.6% | 52.4% |
| KAZ | type rule, all history | SNPP | +0.6% | 1.3% | 40.9% |
| UZB | production: type rule (last 5 y + all history) + static_site, built < 2020 | MODIS | +40.8% | 59.1% | 245.2% |
| UZB | production: type rule (last 5 y + all history) + static_site, built < 2020 | NOAA20 | +16.3% | 14.6% | 53.8% |
| UZB | production: type rule (last 5 y + all history) + static_site, built < 2020 | SNPP | +15.3% | 14.4% | 51.9% |
| UZB | previous production: type-2 rule, last 5 y | MODIS | +37.3% | 49.2% | 206.8% |
| UZB | previous production: type-2 rule, last 5 y | NOAA20 | +5.3% | 4.4% | 18.1% |
| UZB | previous production: type-2 rule, last 5 y | SNPP | +4.4% | 4.2% | 17.8% |
| UZB | C2 mask (both rules, all history) | MODIS | +35.4% | 42.5% | 213.6% |
| UZB | C2 mask (both rules, all history) | NOAA20 | +0.9% | 2.0% | 12.0% |
| UZB | C2 mask (both rules, all history) | SNPP | +0.2% | 3.1% | 12.5% |
| UZB | type rule, all history | MODIS | +36.2% | 43.3% | 215.9% |
| UZB | type rule, all history | NOAA20 | +3.1% | 2.0% | 15.4% |
| UZB | type rule, all history | SNPP | +2.2% | 2.9% | 15.7% |
| TKM | production: type rule (last 5 y + all history) + static_site, built < 2020 | MODIS | +1.7% | 1.8% | 10.0% |
| TKM | production: type rule (last 5 y + all history) + static_site, built < 2020 | NOAA20 | +26.5% | 34.7% | 61.1% |
| TKM | production: type rule (last 5 y + all history) + static_site, built < 2020 | SNPP | +24.4% | 32.8% | 60.6% |
| TKM | previous production: type-2 rule, last 5 y | MODIS | -0.6% | 5.0% | 24.0% |
| TKM | previous production: type-2 rule, last 5 y | NOAA20 | -1.8% | 4.1% | 28.6% |
| TKM | previous production: type-2 rule, last 5 y | SNPP | -3.9% | 4.3% | 25.3% |
| TKM | C2 mask (both rules, all history) | MODIS | -5.7% | 9.1% | 32.8% |
| TKM | C2 mask (both rules, all history) | NOAA20 | -16.2% | 16.6% | 31.7% |
| TKM | C2 mask (both rules, all history) | SNPP | -18.5% | 18.5% | 37.0% |
| TKM | type rule, all history | MODIS | -0.5% | 5.0% | 24.0% |
| TKM | type rule, all history | NOAA20 | -3.7% | 4.8% | 25.5% |
| TKM | type rule, all history | SNPP | -6.1% | 4.9% | 24.0% |

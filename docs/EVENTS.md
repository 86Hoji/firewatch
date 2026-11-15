# Fire events — candidates for the demo

Metric (pipeline/07b_validation_package.py `events`): harmonized cell-days in an H3 res-4 hexagon (~40 km across) in one month, minus that hexagon's normal for the same calendar month (median 2001–2025); ranked by the excess; one event per region and year. Same coefficients as the website (Kazakhstan: production; other countries: refitted on their own 2012–2019 overlap).

*Place* = ADM1 region (geoBoundaries, pre-2022: Abai oblast is inside East Kazakhstan, Jetisu inside Almaty Region, Ulytau inside Karaganda). lat/lon = fire-weighted centre of the hexagon that month. *Data*: before 2012 = MODIS converted to S-NPP equivalent (modelled); from 2012 = S-NPP observed — observed events are easier to defend in front of judges.

## Kazakhstan

### Top 5, all years

| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Kyzylorda Region | April 2003 | 44.88, 65.07 | 583 | 168 | 415 | 1 | MODIS → S-NPP (model) |  |
| 2 | Karaganda Region | July 2005 | 47.31, 66.23 | 380 | 0 | 380 | 2 | MODIS → S-NPP (model) |  |
| 3 | West Kazakhstan Region | July 2001 | 49.75, 52.35 | 374 | 0 | 374 | 3 | MODIS → S-NPP (model) |  |
| 4 | Karaganda Region | July 2015 | 47.18, 70.95 | 368 | 0 | 368 | 4 | S-NPP observed |  |
| 5 | Karaganda Region | June 2004 | 47.40, 69.91 | 368 | 0 | 368 | 5 | MODIS → S-NPP (model) |  |

### Top 5 since 2012 (observed S-NPP only — same metric and normal, filtered)

| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Karaganda Region | July 2015 | 47.18, 70.95 | 368 | 0 | 368 | 4 | S-NPP observed | same hexagon also in 2019 (recurring burn?) |
| 2 | Karaganda Region | July 2017 | 46.81, 71.37 | 361 | 0 | 361 | 7 | S-NPP observed |  |
| 3 | Karaganda Region | July 2019 | 47.22, 70.93 | 290 | 0 | 290 | 18 | S-NPP observed | same hexagon also in 2015 (recurring burn?) |
| 4 | Almaty Region | April 2021 | 45.49, 74.80 | 425 | 150 | 275 | 20 | S-NPP observed |  |
| 5 | Aktobe Region | August 2017 | 48.01, 57.14 | 266 | 11 | 255 | 27 | S-NPP observed |  |

### Known events in Kazakhstan (rank among all 1255 region-month events)

| event | place (ADM1) | month | cell-days | normal | excess | rank |
|---|---|---|---|---|---|---|
| Kostanay forest and steppe fires (Auliekol) | Kostanay Region | September 2022 | 91 | 1 | 90 | 412 |
| Abai region forest fire (Semey Ormany) | East Kazakhstan Region | June 2023 | 123 | 0 | 123 | 242 |

## Uzbekistan

### Top 5, all years

| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Republic of Karakalpakstan | August 2001 | 43.50, 59.75 | 435 | 0 | 435 | 1 | MODIS → S-NPP (model) |  |
| 2 | Republic of Karakalpakstan | August 2006 | 43.66, 59.12 | 296 | 5 | 291 | 2 | MODIS → S-NPP (model) |  |
| 3 | Republic of Karakalpakstan | August 2007 | 43.78, 59.72 | 241 | 0 | 241 | 3 | MODIS → S-NPP (model) | same hexagon also in 2009 (recurring burn?) |
| 4 | Bukhara Region | August 2008 | 40.37, 63.58 | 228 | 19 | 209 | 4 | MODIS → S-NPP (model) |  |
| 5 | Republic of Karakalpakstan | March 2009 | 43.82, 59.77 | 206 | 0 | 206 | 5 | MODIS → S-NPP (model) | same hexagon also in 2007 (recurring burn?) |

### Top 5 since 2012 (observed S-NPP only — same metric and normal, filtered)

| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Republic of Karakalpakstan | April 2021 | 42.84, 58.94 | 240 | 59 | 181 | 8 | S-NPP observed | same hexagon also in 2014 (recurring burn?) |
| 2 | Republic of Karakalpakstan | April 2012 | 42.60, 59.25 | 198 | 51 | 147 | 23 | S-NPP observed |  |
| 3 | Republic of Karakalpakstan | April 2014 | 42.84, 58.92 | 193 | 59 | 134 | 31 | S-NPP observed | same hexagon also in 2021 (recurring burn?) |
| 4 | Surxondaryo Region | June 2025 | 38.04, 67.29 | 131 | 0 | 131 | 35 | S-NPP observed | **NOT A FIRE: new industrial heat source found in C2 (FIRMS labels it vegetation)** |
| 5 | Republic of Karakalpakstan | March 2017 | 43.68, 59.08 | 145 | 21 | 124 | 40 | S-NPP observed |  |

Rank 1 is the largest local excess of fire *counts*. Big wildfires in forest (Abai 2023) rank lower than large steppe/farm burns because the metric counts detections, not intensity or damage. Check any candidate against news or burned-area imagery before the demo.

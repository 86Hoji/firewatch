# Fire events — candidates for the demo

Metric (pipeline/07b_validation_package.py `events`): harmonized cell-days in an H3 res-4 hexagon (~40 km across) in one month, minus that hexagon's normal for the same calendar month (median 2001–2025); ranked by the excess; one event per region and year. Same coefficients as the website (Kazakhstan: production; other countries: refitted on their own 2012–2019 overlap).

*Place* = ADM1 region (geoBoundaries, pre-2022: Abai oblast is inside East Kazakhstan, Jetisu inside Almaty Region, Ulytau inside Karaganda). lat/lon = fire-weighted centre of the hexagon that month. *Data*: before 2012 = MODIS converted to S-NPP equivalent (modelled); from 2012 = S-NPP observed — observed events are easier to defend in front of judges.

## Kazakhstan

### Top 5, all years

| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Kyzylorda Region | April 2003 | 44.88, 65.07 | 579 | 166 | 413 | 1 | MODIS → S-NPP (model) |  |
| 2 | Karaganda Region | July 2005 | 47.31, 66.23 | 376 | 0 | 376 | 2 | MODIS → S-NPP (model) |  |
| 3 | Karaganda Region | July 2015 | 47.18, 70.95 | 368 | 0 | 368 | 3 | S-NPP observed |  |
| 4 | Karaganda Region | June 2004 | 47.40, 69.91 | 367 | 0 | 367 | 4 | MODIS → S-NPP (model) |  |
| 5 | West Kazakhstan Region | July 2001 | 49.75, 52.35 | 364 | 0 | 364 | 5 | MODIS → S-NPP (model) |  |

### Top 5 since 2012 (observed S-NPP only — same metric and normal, filtered)

| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Karaganda Region | July 2015 | 47.18, 70.95 | 368 | 0 | 368 | 3 | S-NPP observed | same hexagon also in 2019 (recurring burn?) |
| 2 | Karaganda Region | July 2017 | 46.81, 71.37 | 361 | 0 | 361 | 6 | S-NPP observed |  |
| 3 | Karaganda Region | July 2019 | 47.22, 70.93 | 290 | 0 | 290 | 17 | S-NPP observed | same hexagon also in 2015 (recurring burn?) |
| 4 | Almaty Region | April 2021 | 45.49, 74.80 | 425 | 150 | 275 | 20 | S-NPP observed |  |
| 5 | Aktobe Region | August 2014 | 50.38, 54.88 | 253 | 0 | 253 | 27 | S-NPP observed |  |

### Known events in Kazakhstan (rank among all 1191 region-month events)

| event | place (ADM1) | month | cell-days | normal | excess | rank |
|---|---|---|---|---|---|---|
| Kostanay forest and steppe fires (Auliekol) | Kostanay Region | September 2022 | 91 | 1 | 90 | 394 |
| Abai region forest fire (Semey Ormany) | East Kazakhstan Region | June 2023 | 123 | 0 | 123 | 233 |

## Uzbekistan

### Top 5, all years

| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Republic of Karakalpakstan | August 2001 | 43.50, 59.75 | 393 | 0 | 393 | 1 | MODIS → S-NPP (model) |  |
| 2 | Republic of Karakalpakstan | August 2006 | 43.66, 59.12 | 263 | 5 | 258 | 2 | MODIS → S-NPP (model) |  |
| 3 | Republic of Karakalpakstan | August 2007 | 43.78, 59.72 | 203 | 0 | 203 | 3 | MODIS → S-NPP (model) | same hexagon also in 2009 (recurring burn?) |
| 4 | Republic of Karakalpakstan | March 2009 | 43.82, 59.77 | 190 | 0 | 190 | 5 | MODIS → S-NPP (model) | same hexagon also in 2007 (recurring burn?) |
| 5 | Bukhara Region | August 2008 | 40.37, 63.58 | 201 | 16 | 185 | 6 | MODIS → S-NPP (model) |  |

### Top 5 since 2012 (observed S-NPP only — same metric and normal, filtered)

| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Republic of Karakalpakstan | April 2021 | 42.84, 58.94 | 240 | 57 | 183 | 7 | S-NPP observed | same hexagon also in 2014 (recurring burn?) |
| 2 | Republic of Karakalpakstan | April 2012 | 42.60, 59.25 | 198 | 51 | 147 | 17 | S-NPP observed |  |
| 3 | Republic of Karakalpakstan | April 2014 | 42.84, 58.92 | 193 | 57 | 136 | 20 | S-NPP observed | same hexagon also in 2021 (recurring burn?) |
| 4 | Surxondaryo Region | June 2025 | 38.04, 67.29 | 131 | 0 | 131 | 25 | S-NPP observed | **NOT A FIRE: new industrial heat source found in C2 (FIRMS labels it vegetation)** |
| 5 | Republic of Karakalpakstan | March 2017 | 43.68, 59.08 | 145 | 21 | 124 | 32 | S-NPP observed |  |

Rank 1 is the largest local excess of fire *counts*. Big wildfires in forest (Abai 2023) rank lower than large steppe/farm burns because the metric counts detections, not intensity or damage. Check any candidate against news or burned-area imagery before the demo.

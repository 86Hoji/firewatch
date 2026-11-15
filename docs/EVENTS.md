# Fire events — candidates for the demo

Metric (pipeline/07b_validation_package.py `events`): harmonized cell-days in an H3 res-4 hexagon (~40 km across) in one month, minus that hexagon's normal for the same calendar month (median 2001–2025); ranked by the excess; one event per region and year. Same coefficients as the website (Kazakhstan: production; other countries: refitted on their own 2012–2019 overlap).

*Place* = ADM1 region (geoBoundaries, pre-2022: Abai oblast is inside East Kazakhstan, Jetisu inside Almaty Region, Ulytau inside Karaganda). lat/lon = fire-weighted centre of the hexagon that month. *Data*: before 2012 = MODIS converted to S-NPP equivalent (modelled); from 2012 = S-NPP observed — observed events are easier to defend in front of judges.

## Kazakhstan

### Top 5, all years

| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Kyzylorda Region | April 2003 | 44.88, 65.07 | 578 | 166 | 413 | 1 | MODIS → S-NPP (model) |  |
| 2 | Karaganda Region | July 2005 | 47.31, 66.23 | 375 | 0 | 375 | 2 | MODIS → S-NPP (model) |  |
| 3 | Karaganda Region | July 2015 | 47.18, 70.95 | 368 | 0 | 368 | 3 | S-NPP observed |  |
| 4 | Karaganda Region | June 2004 | 47.40, 69.91 | 366 | 0 | 366 | 4 | MODIS → S-NPP (model) |  |
| 5 | West Kazakhstan Region | July 2001 | 49.75, 52.35 | 361 | 0 | 361 | 5 | MODIS → S-NPP (model) |  |

### Top 5 since 2012 (observed S-NPP only — same metric and normal, filtered)

| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Karaganda Region | July 2015 | 47.18, 70.95 | 368 | 0 | 368 | 3 | S-NPP observed | same hexagon also in 2019 (recurring burn?) |
| 2 | Karaganda Region | July 2017 | 46.81, 71.37 | 361 | 0 | 361 | 6 | S-NPP observed |  |
| 3 | Karaganda Region | July 2019 | 47.22, 70.93 | 290 | 0 | 290 | 17 | S-NPP observed | same hexagon also in 2015 (recurring burn?) |
| 4 | Almaty Region | April 2021 | 45.49, 74.80 | 425 | 150 | 275 | 20 | S-NPP observed |  |
| 5 | Aktobe Region | August 2017 | 48.00, 57.14 | 255 | 2 | 253 | 24 | S-NPP observed |  |

### Known events in Kazakhstan (rank among all 1183 region-month events)

| event | place (ADM1) | month | cell-days | normal | excess | rank |
|---|---|---|---|---|---|---|
| Kostanay forest and steppe fires (Auliekol) | Kostanay Region | September 2022 | 91 | 1 | 90 | 393 |
| Abai region forest fire (Semey Ormany) | East Kazakhstan Region | June 2023 | 123 | 0 | 123 | 231 |

## Uzbekistan

### Top 5, all years

| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Republic of Karakalpakstan | August 2001 | 43.50, 59.75 | 376 | 0 | 376 | 1 | MODIS → S-NPP (model) |  |
| 2 | Republic of Karakalpakstan | August 2006 | 43.66, 59.12 | 248 | 4 | 244 | 2 | MODIS → S-NPP (model) |  |
| 3 | Republic of Karakalpakstan | August 2007 | 43.78, 59.72 | 186 | 0 | 186 | 4 | MODIS → S-NPP (model) | same hexagon also in 2009 (recurring burn?) |
| 4 | Republic of Karakalpakstan | March 2009 | 43.82, 59.77 | 184 | 0 | 184 | 5 | MODIS → S-NPP (model) | same hexagon also in 2007 (recurring burn?) |
| 5 | Republic of Karakalpakstan | April 2021 | 42.84, 58.94 | 240 | 57 | 183 | 6 | S-NPP observed |  |

### Top 5 since 2012 (observed S-NPP only — same metric and normal, filtered)

| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Republic of Karakalpakstan | April 2021 | 42.84, 58.94 | 240 | 57 | 183 | 6 | S-NPP observed | same hexagon also in 2014 (recurring burn?) |
| 2 | Republic of Karakalpakstan | April 2012 | 42.60, 59.25 | 198 | 51 | 147 | 16 | S-NPP observed |  |
| 3 | Republic of Karakalpakstan | April 2014 | 42.84, 58.92 | 193 | 57 | 136 | 19 | S-NPP observed | same hexagon also in 2021 (recurring burn?) |
| 4 | Republic of Karakalpakstan | March 2017 | 43.67, 59.09 | 143 | 21 | 122 | 27 | S-NPP observed |  |
| 5 | Tashkent Region | July 2013 | 41.11, 69.37 | 239 | 118 | 121 | 29 | S-NPP observed |  |

Rank 1 is the largest local excess of fire *counts*. Big wildfires in forest (Abai 2023) rank lower than large steppe/farm burns because the metric counts detections, not intensity or damage. Check any candidate against news or burned-area imagery before the demo.

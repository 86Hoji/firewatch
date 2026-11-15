# FIREWATCH — validation package (C4)

Model: **C2 — Terra∪Aqua, Poisson log-link** (`poisson_log`), fitted on Kazakhstan 2012–2019 and applied unchanged everywhere below unless a row says "local". Error = mean absolute error as % of the mean month (MAE %); bias = total predicted vs actual. Actual = S-NPP cell-days (+ NOAA-20 on satellite-wide S-NPP outage days). Machine-readable: [validation.json](validation.json). Kazakhstan technical report: [validation_kz.md](validation_kz.md).

*January 2012 is incomplete:* the S-NPP archive starts on 2012-01-20, so that month has about a third of its observations (it is inside the 2012 step windows and the 2012–2019 overlap as recorded).

## 1. Uzbekistan — independent test (model never saw UZ)

| series | step 2009–11 → 2012–14 | vs MODIS alone | monthly step (95% CI), 2003–2019 |
|---|---|---|---|
| naive splice (MODIS → S-NPP) | ×4.40 | ×3.20 | ×5.15 (3.31–8.00) |
| harmonized (KZ model) | ×1.77 | ×1.29 | ×1.79 (1.19–2.68) |
| harmonized (local refit) | ×1.19 | ×0.86 | ×1.24 (0.87–1.76) |
| MODIS alone (reference) | ×1.37 | ×1.00 | ×1.39 (0.87–2.22) |

| period | model | MAE % | bias % | R | 90% interval coverage |
|---|---|---|---|---|---|
| overlap 2012–2019 | KZ as-is | 33.3 | -31.0 | 0.934 | 58% |
| overlap 2012–2019 | local refit (LOYO) | 16.0 | -0.3 | 0.964 | – |
| holdout 2020–2025 | KZ as-is | 36.5 | -35.2 | 0.938 | 58% |
| holdout 2020–2024 | KZ as-is | 38.3 | -36.7 | 0.929 | 58% |
| holdout 2020–2025 | local refit | 22.2 | -4.7 | 0.932 | – |

VIIRS/MODIS ratio 2012–2019: observed ×3.50, KZ model gives ×2.42.

**Takeaway.** Applied to Uzbekistan without any Uzbek data, the naive splice jumps ×4.40 at 2012, the KZ-harmonized series ×1.77, a locally refitted one ×1.19 (MODIS alone ×1.37). In 2012–2019 the KZ model is off by 33.3% a month and -31.0% in total; the same model refitted on Uzbekistan: 16.0% and -0.3%. Uzbekistan's VIIRS/MODIS ratio is ×3.50, the KZ model implies ×2.42: VIIRS sees relatively more fires there (C1: small agricultural burns). 2025 contains the new industrial source near 38.1°N 67.3°E (C2), so the holdout is also shown to 2024 — it changes little.

## 2. Turkmenistan — stress test (gas flares)

| series | step 2009–11 → 2012–14 | vs MODIS alone | monthly step (95% CI), 2003–2019 |
|---|---|---|---|
| naive splice (MODIS → S-NPP) | ×3.65 | ×3.03 | ×5.58 (3.44–9.05) |
| harmonized (KZ model) | ×1.42 | ×1.17 | ×1.97 (1.29–3.02) |
| harmonized (local refit) | ×1.08 | ×0.89 | ×1.24 (0.88–1.74) |
| MODIS alone (reference) | ×1.21 | ×1.00 | ×1.74 (1.08–2.82) |

| period | model | MAE % | bias % | R | 90% interval coverage |
|---|---|---|---|---|---|
| overlap 2012–2019 | KZ as-is | 31.6 | -21.6 | 0.884 | 64% |
| overlap 2012–2019 | local refit (LOYO) | 18.9 | -1.3 | 0.923 | – |
| holdout 2020–2025 | KZ as-is | 45.9 | -40.4 | 0.866 | 39% |
| holdout 2020–2024 | KZ as-is | 45.3 | -40.0 | 0.870 | 42% |
| holdout 2020–2025 | local refit | 30.2 | -21.5 | 0.924 | – |

VIIRS/MODIS ratio 2012–2019: observed ×3.20, KZ model gives ×2.50.

| country | detections removed as static (type ≠ 0) | mask test: precision / recall |
|---|---|---|
| KAZ | 13.2% | 88% / 94% |
| UZB | 39.5% | 83% / 76% |
| TKM | 56.5% | 80% / 96% |

**Takeaway.** The naive splice jumps ×3.65 at 2012, the KZ-harmonized series ×1.42, a locally refitted one ×1.08 (MODIS alone ×1.21). Overlap error as-is 31.6% (bias -21.6%), local refit 18.9%. 57% of Turkmenistan's confident detections are static sources (Kazakhstan 13%); FIRMS `type` removes them in archive data and the mask in recent data (precision/recall above). The remaining error is the same kind as Uzbekistan's: VIIRS/MODIS ×3.20 vs ×2.50 from the KZ model. TM's monthly R is the lowest of the cell-level countries.

## 3. Kyrgyzstan and Tajikistan — annual totals

KZ coefficients as-is, and *local* = the country's own refit (what the website uses): leave-one-year-out in 2012–2019 and fit on the overlap → holdout.

| country | years | mean actual cell-days / year | MAE % (annual), KZ as-is | bias % | R | naive MODIS bias % | local LOYO MAE % / bias % | local holdout MAE % / bias % |
|---|---|---|---|---|---|---|---|---|
| KGZ | 2012–2025 | 720 | 16.7 | -16.2 | 0.951 | -71 | 6.2 / -1.3 | 10.6 / -4.9 (2020–2025) |
| TJK | 2012–2025 | 269 | 13.5 | +8.8 | 0.919 | -73 | 17.7 / +4.6 | 16.0 / -16.0 (2020–2025) |

**Takeaway.** Kyrgyzstan and Tajikistan have only a few hundred fire cell-days a year, so only annual totals are meaningful. KGZ: annual error 16.7%, bias -16.2% (raw MODIS: -71%); TJK: annual error 13.5%, bias +8.8% (raw MODIS: -73%). The harmonized totals are usable for a yearly trend, not for single months.

## 4. Transfer table — does the Kazakh model work elsewhere?

Overlap 2012–2019. *As-is* = KZ coefficients unchanged (for KZ itself: leave-one-year-out, so it is not in-sample). *Local* = the same model refitted on that country, each year predicted from the other years. "Transfers" = as-is error ≤ 1.5× local and |bias| ≤ 15%.

| country | role | VIIRS/MODIS observed | KZ model | as-is MAE % | as-is bias % | local MAE % | holdout as-is MAE % / bias % | holdout local MAE % | transfers? |
|---|---|---|---|---|---|---|---|---|---|
| PRT | transfer | ×1.54 | ×2.29 | 51.5 | +48.1 | 16.4 | 80.0 / +75.2 | 22.1 | **no** |
| KAZ | train | ×1.74 | ×1.74 | 6.4 | +0.1 | 6.4 | 10.0 / -2.6 | 10.0 | yes |
| AUS | transfer | ×1.97 | ×1.39 | 30.6 | -29.6 | 5.2 | 32.8 / -32.8 | 7.0 | **no** |
| USA | transfer | ×2.15 | ×1.60 | 26.6 | -25.7 | 8.3 | 29.1 / -29.1 | 8.8 | **no** |
| BRA | transfer | ×2.47 | ×1.23 | 50.3 | -50.1 | 5.5 | 46.5 / -46.4 | 10.3 | **no** |
| TKM | stress | ×3.20 | ×2.50 | 31.6 | -21.6 | 18.9 | 45.9 / -40.4 | 30.2 | **no** |
| KGZ | extra | ×3.37 | ×2.86 | 26.2 | -15.3 | 22.3 | 26.7 / -17.9 | 24.8 | **no** |
| TJK | extra | ×3.44 | ×4.01 | 40.2 | +16.6 | 41.7 | 41.2 / -0.7 | 31.3 | **no** |
| UZB | test | ×3.50 | ×2.42 | 33.3 | -31.0 | 16.0 | 36.5 / -35.2 | 22.2 | **no** |
| IND | transfer | ×4.46 | ×1.62 | 63.7 | -63.6 | 9.2 | 63.4 / -63.4 | 10.1 | **no** |

**Takeaway.** Transfers as-is: KAZ; does not: AUS, BRA, IND, KGZ, PRT, TJK, TKM, USA, UZB. The observed VIIRS/MODIS ratio ranges from ×1.54 to ×4.46; the KZ model cannot know a country's ratio and errs in the direction of the difference (too high for Portugal, too low for India). Refitted locally, the same model gets 5.2–41.7% monthly error. Honest conclusion: the METHOD transfers across biomes, the COEFFICIENTS do not — every country needs its own 2012–2019 overlap fit (which FIRMS provides everywhere).

## 5. Burned area cross-check

Monthly burned area (`data/external/burned_area.csv`) vs monthly cell-days, 2003–2025. Burned area does not change sensor in 2012, so a fire-count series that is consistent across 2012 should show **no step once burned area is accounted for** (factor ≈ 1).

| country | series | R (log) all | R before 2012 | R from 2012 | step at 2012 given burned area (95% CI) |
|---|---|---|---|---|---|
| KAZ | naive | 0.86 | 0.86 | 0.89 | ×2.37 (1.75–3.22) |
| KAZ | harmonized | 0.88 | 0.86 | 0.89 | ×1.13 (0.86–1.48) |
| KAZ | harmonized_local | 0.88 | 0.86 | 0.89 | ×1.13 (0.86–1.48) |
| KAZ | modis_only | 0.88 | 0.86 | 0.89 | ×1.22 (0.82–1.83) |
| KGZ | naive | 0.56 | 0.75 | 0.52 | ×1.93 (1.32–2.83) |
| KGZ | harmonized | 0.66 | 0.78 | 0.52 | ×0.60 (0.41–0.87) |
| KGZ | harmonized_local | 0.65 | 0.74 | 0.52 | ×0.56 (0.39–0.79) |
| KGZ | modis_only | 0.68 | 0.75 | 0.57 | ×0.61 (0.42–0.88) |
| TJK | naive | 0.34 | 0.57 | 0.38 | ×2.32 (1.58–3.42) |
| TJK | harmonized | 0.50 | 0.58 | 0.37 | ×0.62 (0.42–0.91) |
| TJK | harmonized_local | 0.47 | 0.56 | 0.37 | ×0.71 (0.49–1.03) |
| TJK | modis_only | 0.52 | 0.57 | 0.42 | ×0.86 (0.57–1.31) |
| TKM | naive | 0.35 | 0.62 | 0.52 | ×3.97 (3.09–5.09) |
| TKM | harmonized | 0.51 | 0.65 | 0.52 | ×1.44 (1.14–1.82) |
| TKM | harmonized_local | 0.53 | 0.57 | 0.52 | ×0.98 (0.78–1.24) |
| TKM | modis_only | 0.56 | 0.62 | 0.52 | ×1.44 (1.09–1.90) |
| UZB | naive | 0.49 | 0.68 | 0.64 | ×3.96 (2.94–5.33) |
| UZB | harmonized | 0.62 | 0.68 | 0.64 | ×1.41 (1.07–1.85) |
| UZB | harmonized_local | 0.64 | 0.69 | 0.64 | ×0.99 (0.77–1.27) |
| UZB | modis_only | 0.69 | 0.68 | 0.71 | ×1.03 (0.74–1.44) |

MODIS alone has no sensor change at 2012, so its step is the change in fire regime; the seam test for the harmonized series is its step relative to MODIS alone.

**Takeaway.** Holding burned area fixed, naive: continuous (95% CI includes 1) in none; KZ-harmonized: continuous (95% CI includes 1) in KAZ; locally harmonized: continuous (95% CI includes 1) in KAZ, TJK, TKM, UZB. The naive series jumps ×1.9–×4.0 everywhere. Correlation with burned area is high in Kazakhstan and weak in Kyrgyzstan/Tajikistan (few fires; much burned area there is not seen as active fire).

## 6. Events for the demo

Event = far more fire than usual for that place and month: harmonized cell-days in an H3 res-4 hexagon (~40 km across) minus its normal (median of the same hexagon and calendar month, 2001–2025); ranked by that excess; one per region and year in the top list. Region = ADM1 (pre-2022 boundaries). Coefficients as on the website: Kazakhstan production, every other country its own refit.

| country | rank | region | month | cell-days | normal | excess |
|---|---|---|---|---|---|---|
| KAZ | 1 | Kyzylorda Region | 2003-04 | 579 | 166 | 413 |
| KAZ | 2 | Karaganda Region | 2005-07 | 376 | 0 | 376 |
| KAZ | 3 | Karaganda Region | 2015-07 | 368 | 0 | 368 |
| UZB | 1 | Republic of Karakalpakstan | 2001-08 | 393 | 0 | 393 |
| UZB | 2 | Republic of Karakalpakstan | 2006-08 | 263 | 5 | 258 |
| UZB | 3 | Republic of Karakalpakstan | 2007-08 | 203 | 0 | 203 |
| TKM | 1 | Balkan | 2003-08 | 245 | 0 | 245 |
| TKM | 2 | Balkan | 2010-07 | 201 | 0 | 201 |
| TKM | 3 | Ahai | 2005-02 | 198 | 50 | 148 |
| KGZ | 1 | Jalal-Abad Region | 2007-11 | 236 | 0 | 236 |
| KGZ | 2 | Issyk-Kul Region | 2004-10 | 130 | 5 | 125 |
| KGZ | 3 | Chuy Region | 2007-09 | 139 | 19 | 120 |
| TJK | 1 | Khatlon Region | 2003-10 | 55 | 2 | 53 |
| TJK | 2 | Khatlon Region | 2004-10 | 42 | 2 | 40 |
| TJK | 4 | Khatlon Region | 2006-04 | 31 | 0 | 31 |

Known events (Kazakhstan), rank among all hexagon-month events:

| event | region | month | cell-days (best hexagon) | normal | excess | rank |
|---|---|---|---|---|---|---|
| Kostanay forest and steppe fires (Auliekol) | KZ-KUS | 2022-09 | 91 | 1 | 90 | 394 of 1191 |
| Abai region forest fire (Semey Ormany) | KZ-VOS | 2023-06 | 123 | 0 | 123 | 233 of 1191 |

**Takeaway.** Kostanay forest and steppe fires (Auliekol) (2022-09): 91 cell-days in one hexagon vs a normal of 1, rank 394 of 1191. Abai region forest fire (Semey Ormany) (2023-06): 123 cell-days in one hexagon vs a normal of 0, rank 233 of 1191. The top events are the largest local excesses; check them against news before the demo.

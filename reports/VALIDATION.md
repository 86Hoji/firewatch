# FIREWATCH — validation package (C4)

Model: **C2 — Terra∪Aqua, Poisson log-link** (`poisson_log`), fitted on Kazakhstan 2012–2019 and applied unchanged everywhere below unless a row says "local". Error = mean absolute error as % of the mean month (MAE %); bias = total predicted vs actual. Actual = S-NPP cell-days (+ NOAA-20 on satellite-wide S-NPP outage days). Machine-readable: [validation.json](validation.json). Kazakhstan technical report: [validation_kz.md](validation_kz.md).

## 1. Uzbekistan — independent test (model never saw UZ)

| series | step 2009–11 → 2012–14 | vs MODIS alone | monthly step (95% CI), 2003–2019 |
|---|---|---|---|
| naive splice (MODIS → S-NPP) | ×4.32 | ×3.14 | ×5.05 (3.30–7.72) |
| harmonized (KZ model) | ×1.77 | ×1.28 | ×1.79 (1.21–2.65) |
| harmonized (local refit) | ×1.24 | ×0.90 | ×1.32 (0.93–1.87) |
| MODIS alone (reference) | ×1.38 | ×1.00 | ×1.39 (0.87–2.22) |

| period | model | MAE % | bias % | R | 90% interval coverage |
|---|---|---|---|---|---|
| overlap 2012–2019 | KZ as-is | 31.2 | -28.6 | 0.939 | 62% |
| overlap 2012–2019 | local refit (LOYO) | 15.6 | -0.2 | 0.966 | – |
| holdout 2020–2025 | KZ as-is | 32.9 | -31.2 | 0.952 | 62% |
| holdout 2020–2024 | KZ as-is | 33.6 | -31.5 | 0.942 | 62% |
| holdout 2020–2025 | local refit | 20.9 | -2.0 | 0.946 | – |

VIIRS/MODIS ratio 2012–2019: observed ×3.34, KZ model gives ×2.38.

**Takeaway.** Applied to Uzbekistan without any Uzbek data, the naive splice jumps ×4.32 at 2012, the KZ-harmonized series ×1.77, a locally refitted one ×1.24 (MODIS alone ×1.38). In 2012–2019 the KZ model is off by 31.2% a month and -28.6% in total; the same model refitted on Uzbekistan: 15.6% and -0.2%. Uzbekistan's VIIRS/MODIS ratio is ×3.34, the KZ model implies ×2.38: VIIRS sees relatively more fires there (C1: small agricultural burns). 2025 contains the new industrial source near 38.1°N 67.3°E (C2), so the holdout is also shown to 2024 — it changes little.

## 2. Turkmenistan — stress test (gas flares)

| series | step 2009–11 → 2012–14 | vs MODIS alone | monthly step (95% CI), 2003–2019 |
|---|---|---|---|
| naive splice (MODIS → S-NPP) | ×3.48 | ×2.87 | ×5.42 (3.36–8.76) |
| harmonized (KZ model) | ×1.37 | ×1.13 | ×1.95 (1.27–2.99) |
| harmonized (local refit) | ×1.15 | ×0.95 | ×1.46 (1.01–2.11) |
| MODIS alone (reference) | ×1.21 | ×1.00 | ×1.75 (1.08–2.82) |

| period | model | MAE % | bias % | R | 90% interval coverage |
|---|---|---|---|---|---|
| overlap 2012–2019 | KZ as-is | 26.0 | -13.9 | 0.914 | 82% |
| overlap 2012–2019 | local refit (LOYO) | 16.0 | -0.2 | 0.951 | – |
| holdout 2020–2025 | KZ as-is | 32.4 | -24.2 | 0.942 | 69% |
| holdout 2020–2024 | KZ as-is | 30.7 | -22.3 | 0.950 | 77% |
| holdout 2020–2025 | local refit | 18.9 | -9.8 | 0.976 | – |

VIIRS/MODIS ratio 2012–2019: observed ×2.88, KZ model gives ×2.48.

| country | detections removed as static (type ≠ 0) | mask test: precision / recall |
|---|---|---|
| KAZ | 13.2% | 88% / 94% |
| UZB | 39.5% | 83% / 76% |
| TKM | 56.5% | 80% / 96% |

**Takeaway.** The naive splice jumps ×3.48 at 2012, the KZ-harmonized series ×1.37, a locally refitted one ×1.15 (MODIS alone ×1.21). Overlap error as-is 26.0% (bias -13.9%), local refit 16.0%. 57% of Turkmenistan's confident detections are static sources (Kazakhstan 13%); FIRMS `type` removes them in archive data and the mask in recent data (precision/recall above). The remaining error is the same kind as Uzbekistan's: VIIRS/MODIS ×2.88 vs ×2.48 from the KZ model. TM's monthly R is the lowest of the cell-level countries.

## 3. Kyrgyzstan and Tajikistan — annual totals

| country | years | mean actual cell-days / year | MAE % (annual) | bias % | R | naive MODIS bias % |
|---|---|---|---|---|---|---|
| KGZ | 2012–2025 | 689 | 14.9 | -14.0 | 0.945 | -70 |
| TJK | 2012–2025 | 255 | 13.6 | +9.6 | 0.938 | -72 |

**Takeaway.** Kyrgyzstan and Tajikistan have only a few hundred fire cell-days a year, so only annual totals are meaningful. KGZ: annual error 14.9%, bias -14.0% (raw MODIS: -70%); TJK: annual error 13.6%, bias +9.6% (raw MODIS: -72%). The harmonized totals are usable for a yearly trend, not for single months.

## 4. Transfer table — does the Kazakh model work elsewhere?

Overlap 2012–2019. *As-is* = KZ coefficients unchanged (for KZ itself: leave-one-year-out, so it is not in-sample). *Local* = the same model refitted on that country, each year predicted from the other years. "Transfers" = as-is error ≤ 1.5× local and |bias| ≤ 15%.

| country | role | VIIRS/MODIS observed | KZ model | as-is MAE % | as-is bias % | local MAE % | holdout as-is MAE % / bias % | holdout local MAE % | transfers? |
|---|---|---|---|---|---|---|---|---|---|
| PRT | transfer | ×1.54 | ×2.25 | 49.8 | +46.5 | 16.5 | 77.0 / +72.1 | 21.6 | **no** |
| KAZ | train | ×1.73 | ×1.73 | 6.4 | +0.2 | 6.4 | 9.8 / -0.9 | 9.8 | yes |
| AUS | transfer | ×1.97 | ×1.40 | 30.2 | -29.1 | 5.2 | 32.5 / -32.5 | 7.0 | **no** |
| USA | transfer | ×2.15 | ×1.60 | 26.5 | -25.5 | 8.3 | 28.9 / -28.9 | 8.8 | **no** |
| BRA | transfer | ×2.47 | ×1.24 | 50.1 | -49.9 | 5.5 | 46.3 / -46.2 | 10.3 | **no** |
| TKM | stress | ×2.88 | ×2.48 | 26.0 | -13.9 | 16.0 | 32.4 / -24.2 | 18.9 | **no** |
| KGZ | extra | ×3.22 | ×2.81 | 25.7 | -12.7 | 22.4 | 25.6 / -16.3 | 24.8 | yes |
| UZB | test | ×3.34 | ×2.38 | 31.2 | -28.6 | 15.6 | 32.9 / -31.2 | 20.9 | **no** |
| TJK | extra | ×3.36 | ×3.89 | 39.5 | +15.7 | 38.7 | 40.2 / +2.0 | 31.1 | **no** |
| IND | transfer | ×4.46 | ×1.63 | 63.5 | -63.5 | 9.2 | 63.1 / -63.1 | 10.1 | **no** |

**Takeaway.** Transfers as-is: KAZ, KGZ; does not: AUS, BRA, IND, PRT, TJK, TKM, USA, UZB. The observed VIIRS/MODIS ratio ranges from ×1.54 to ×4.46; the KZ model cannot know a country's ratio and errs in the direction of the difference (too high for Portugal, too low for India). Refitted locally, the same model gets 5.2–38.7% monthly error. Honest conclusion: the METHOD transfers across biomes, the COEFFICIENTS do not — every country needs its own 2012–2019 overlap fit (which FIRMS provides everywhere).

## 5. Burned area cross-check

Monthly burned area (`data/external/burned_area.csv`) vs monthly cell-days, 2003–2025. Burned area does not change sensor in 2012, so a fire-count series that is consistent across 2012 should show **no step once burned area is accounted for** (factor ≈ 1).

| country | series | R (log) all | R before 2012 | R from 2012 | step at 2012 given burned area (95% CI) |
|---|---|---|---|---|---|
| KAZ | naive | 0.86 | 0.86 | 0.88 | ×2.41 (1.77–3.27) |
| KAZ | harmonized | 0.88 | 0.86 | 0.89 | ×1.16 (0.88–1.53) |
| KAZ | harmonized_local | 0.88 | 0.86 | 0.89 | ×1.16 (0.88–1.53) |
| KGZ | naive | 0.57 | 0.75 | 0.53 | ×1.77 (1.18–2.64) |
| KGZ | harmonized | 0.66 | 0.78 | 0.53 | ×0.56 (0.38–0.83) |
| KGZ | harmonized_local | 0.66 | 0.75 | 0.53 | ×0.54 (0.37–0.80) |
| TJK | naive | 0.35 | 0.56 | 0.38 | ×2.26 (1.50–3.41) |
| TJK | harmonized | 0.49 | 0.58 | 0.37 | ×0.62 (0.42–0.94) |
| TJK | harmonized_local | 0.47 | 0.56 | 0.37 | ×0.71 (0.47–1.07) |
| TKM | naive | 0.39 | 0.62 | 0.53 | ×3.93 (2.96–5.21) |
| TKM | harmonized | 0.55 | 0.64 | 0.53 | ×1.45 (1.11–1.91) |
| TKM | harmonized_local | 0.55 | 0.60 | 0.53 | ×1.14 (0.87–1.49) |
| UZB | naive | 0.51 | 0.68 | 0.65 | ×3.87 (2.88–5.21) |
| UZB | harmonized | 0.63 | 0.67 | 0.65 | ×1.40 (1.06–1.85) |
| UZB | harmonized_local | 0.65 | 0.69 | 0.65 | ×1.04 (0.80–1.35) |

**Takeaway.** Holding burned area fixed, naive: continuous (95% CI includes 1) in none; KZ-harmonized: continuous (95% CI includes 1) in KAZ; locally harmonized: continuous (95% CI includes 1) in KAZ, TJK, TKM, UZB. The naive series jumps ×1.8–×3.9 everywhere. Correlation with burned area is high in Kazakhstan and weak in Kyrgyzstan/Tajikistan (few fires; much burned area there is not seen as active fire).

## 6. Events for the demo

Event = far more fire than usual for that place and month: harmonized cell-days in an H3 res-4 hexagon (~40 km across) minus its normal (median of the same hexagon and calendar month, 2001–2025); ranked by that excess; one per region and year in the top list. Region = ADM1 (pre-2022 boundaries).

| country | rank | region | month | cell-days | normal | excess |
|---|---|---|---|---|---|---|
| KAZ | 1 | Kyzylorda Region | 2003-04 | 578 | 166 | 413 |
| KAZ | 2 | Karaganda Region | 2005-07 | 375 | 0 | 375 |
| KAZ | 3 | Karaganda Region | 2015-07 | 368 | 0 | 368 |
| UZB | 1 | Republic of Karakalpakstan | 2001-03 | 242 | 2 | 240 |
| UZB | 3 | Republic of Karakalpakstan | 2021-04 | 240 | 49 | 191 |
| UZB | 4 | Republic of Karakalpakstan | 2012-04 | 198 | 44 | 154 |
| TKM | 1 | Balkan | 2003-08 | 185 | 0 | 185 |
| TKM | 2 | Ahai | 2005-02 | 226 | 52 | 174 |
| TKM | 3 | Balkan | 2010-07 | 148 | 0 | 148 |
| KGZ | 1 | Jalal-Abad Region | 2007-11 | 136 | 0 | 136 |
| KGZ | 2 | Chuy Region | 2002-08 | 127 | 10 | 117 |
| KGZ | 3 | Chuy Region | 2006-08 | 116 | 22 | 94 |
| TJK | 1 | Khatlon Region | 2003-10 | 69 | 2 | 67 |
| TJK | 2 | Khatlon Region | 2004-10 | 51 | 2 | 49 |
| TJK | 3 | Khatlon Region | 2002-08 | 44 | 2 | 42 |

Known events (Kazakhstan), rank among all hexagon-month events:

| event | region | month | cell-days (best hexagon) | normal | excess | rank |
|---|---|---|---|---|---|---|
| Kostanay forest and steppe fires (Auliekol) | KZ-KUS | 2022-09 | 91 | 1 | 90 | 393 of 1183 |
| Abai region forest fire (Semey Ormany) | KZ-VOS | 2023-06 | 123 | 0 | 123 | 231 of 1183 |

**Takeaway.** Kostanay forest and steppe fires (Auliekol) (2022-09): 91 cell-days in one hexagon vs a normal of 1, rank 393 of 1183. Abai region forest fire (Semey Ormany) (2023-06): 123 cell-days in one hexagon vs a normal of 0, rank 231 of 1183. The top events are the largest local excesses; check them against news before the demo.

# FIREWATCH — validation package (C4)

Model: **C2 — Terra∪Aqua, Poisson log-link** (`poisson_log`), fitted on Kazakhstan 2012–2019 and applied unchanged everywhere below unless a row says "local". Error = mean absolute error as % of the mean month (MAE %); bias = total predicted vs actual. Actual = S-NPP cell-days (+ NOAA-20 on satellite-wide S-NPP outage days). Machine-readable: [validation.json](validation.json). Kazakhstan technical report: [validation_kz.md](validation_kz.md).

## 1. Uzbekistan — independent test (model never saw UZ)

| series | step 2009–11 → 2012–14 | vs MODIS alone | monthly step (95% CI), 2003–2019 |
|---|---|---|---|
| naive splice (MODIS → S-NPP) | ×4.88 | ×3.62 | ×5.70 (3.80–8.56) |
| harmonized (KZ model) | ×1.77 | ×1.32 | ×1.75 (1.23–2.51) |
| harmonized (local refit) | ×1.15 | ×0.86 | ×1.16 (0.86–1.55) |
| MODIS alone (reference) | ×1.35 | ×1.00 | ×1.32 (0.85–2.06) |

| period | model | MAE % | bias % | R | 90% interval coverage |
|---|---|---|---|---|---|
| overlap 2012–2019 | KZ as-is | 35.5 | -32.4 | 0.920 | 52% |
| overlap 2012–2019 | local refit (LOYO) | 17.7 | -0.4 | 0.949 | – |
| holdout 2020–2025 | KZ as-is | 35.5 | -33.4 | 0.929 | 60% |
| holdout 2020–2024 | KZ as-is | 37.6 | -35.3 | 0.920 | 58% |
| holdout 2020–2025 | local refit | 22.7 | +0.5 | 0.917 | – |

VIIRS/MODIS ratio 2012–2019: observed ×3.94, KZ model gives ×2.66.

**Takeaway.** Applied to Uzbekistan without any Uzbek data, the naive splice jumps ×4.88 at 2012, the KZ-harmonized series ×1.77, a locally refitted one ×1.15 (MODIS alone ×1.35). In 2012–2019 the KZ model is off by 35.5% a month and -32.4% in total; the same model refitted on Uzbekistan: 17.7% and -0.4%. Uzbekistan's VIIRS/MODIS ratio is ×3.94, the KZ model implies ×2.66: VIIRS sees relatively more fires there (C1: small agricultural burns). 2025 contains the new industrial source near 38.1°N 67.3°E (C2), so the holdout is also shown to 2024 — it changes little.

## 2. Turkmenistan — stress test (gas flares)

| series | step 2009–11 → 2012–14 | vs MODIS alone | monthly step (95% CI), 2003–2019 |
|---|---|---|---|
| naive splice (MODIS → S-NPP) | ×4.75 | ×3.91 | ×7.68 (4.64–12.71) |
| harmonized (KZ model) | ×1.66 | ×1.37 | ×2.40 (1.55–3.70) |
| harmonized (local refit) | ×1.02 | ×0.84 | ×1.15 (0.81–1.65) |
| MODIS alone (reference) | ×1.21 | ×1.00 | ×1.79 (1.11–2.89) |

| period | model | MAE % | bias % | R | 90% interval coverage |
|---|---|---|---|---|---|
| overlap 2012–2019 | KZ as-is | 42.3 | -34.9 | 0.727 | 42% |
| overlap 2012–2019 | local refit (LOYO) | 22.9 | -0.7 | 0.827 | – |
| holdout 2020–2025 | KZ as-is | 50.4 | -45.3 | 0.737 | 38% |
| holdout 2020–2024 | KZ as-is | 49.9 | -44.8 | 0.730 | 40% |
| holdout 2020–2025 | local refit | 29.8 | -12.4 | 0.852 | – |

VIIRS/MODIS ratio 2012–2019: observed ×4.16, KZ model gives ×2.70.

| country | detections removed as static (type ≠ 0) | mask test: precision / recall |
|---|---|---|
| KAZ | 13.2% | 94% / 88% |
| UZB | 39.5% | 94% / 75% |
| TKM | 56.5% | 86% / 84% |

**Takeaway.** The naive splice jumps ×4.75 at 2012, the KZ-harmonized series ×1.66, a locally refitted one ×1.02 (MODIS alone ×1.21). Overlap error as-is 42.3% (bias -34.9%), local refit 22.9%. 57% of Turkmenistan's confident detections are static sources (Kazakhstan 13%); FIRMS `type` removes them in archive data and the mask in recent data (precision/recall above). The remaining error is the same kind as Uzbekistan's: VIIRS/MODIS ×4.16 vs ×2.70 from the KZ model. TM's monthly R is the lowest of the cell-level countries.

## 3. Kyrgyzstan and Tajikistan — annual totals

| country | years | mean actual cell-days / year | MAE % (annual) | bias % | R | naive MODIS bias % |
|---|---|---|---|---|---|---|
| KGZ | 2012–2025 | 763 | 9.2 | -5.7 | 0.955 | -72 |
| TJK | 2012–2025 | 307 | 20.3 | +19.6 | 0.923 | -76 |

**Takeaway.** Kyrgyzstan and Tajikistan have only a few hundred fire cell-days a year, so only annual totals are meaningful. KGZ: annual error 9.2%, bias -5.7% (raw MODIS: -72%); TJK: annual error 20.3%, bias +19.6% (raw MODIS: -76%). The harmonized totals are usable for a yearly trend, not for single months.

## 4. Transfer table — does the Kazakh model work elsewhere?

Overlap 2012–2019. *As-is* = KZ coefficients unchanged (for KZ itself: leave-one-year-out, so it is not in-sample). *Local* = the same model refitted on that country, each year predicted from the other years. "Transfers" = as-is error ≤ 1.5× local and |bias| ≤ 15%.

| country | role | VIIRS/MODIS observed | KZ model | as-is MAE % | as-is bias % | local MAE % | holdout as-is MAE % / bias % | holdout local MAE % | transfers? |
|---|---|---|---|---|---|---|---|---|---|
| PRT | transfer | ×1.58 | ×2.51 | 61.7 | +58.9 | 15.6 | 94.3 / +89.5 | 22.2 | **no** |
| KAZ | train | ×1.80 | ×1.80 | 6.5 | +0.1 | 6.5 | 10.3 / -2.2 | 10.3 | yes |
| AUS | transfer | ×1.97 | ×1.33 | 33.3 | -32.6 | 5.2 | 34.9 / -34.9 | 7.0 | **no** |
| USA | transfer | ×2.15 | ×1.57 | 27.4 | -26.7 | 8.3 | 30.3 / -30.3 | 8.8 | **no** |
| BRA | transfer | ×2.47 | ×1.18 | 52.5 | -52.4 | 5.5 | 48.8 / -48.7 | 10.3 | **no** |
| KGZ | extra | ×3.47 | ×3.26 | 24.2 | -5.8 | 20.8 | 27.5 / -5.4 | 24.2 | yes |
| TJK | extra | ×3.92 | ×4.95 | 49.3 | +26.0 | 37.4 | 51.8 / +11.5 | 30.9 | **no** |
| UZB | test | ×3.94 | ×2.66 | 35.5 | -32.4 | 17.7 | 35.5 / -33.4 | 22.7 | **no** |
| TKM | stress | ×4.16 | ×2.70 | 42.3 | -34.9 | 22.9 | 50.4 / -45.3 | 29.8 | **no** |
| IND | transfer | ×4.46 | ×1.58 | 64.6 | -64.6 | 9.2 | 64.7 / -64.7 | 10.1 | **no** |

**Takeaway.** Transfers as-is: KAZ, KGZ; does not: AUS, BRA, IND, PRT, TJK, TKM, USA, UZB. The observed VIIRS/MODIS ratio ranges from ×1.58 to ×4.46; the KZ model cannot know a country's ratio and errs in the direction of the difference (too high for Portugal, too low for India). Refitted locally, the same model gets 5.2–37.4% monthly error. Honest conclusion: the METHOD transfers across biomes, the COEFFICIENTS do not — every country needs its own 2012–2019 overlap fit (which FIRMS provides everywhere).

## 5. Burned area cross-check

Monthly burned area (`data/external/burned_area.csv`) vs monthly cell-days, 2003–2025. Burned area does not change sensor in 2012, so a fire-count series that is consistent across 2012 should show **no step once burned area is accounted for** (factor ≈ 1).

| country | series | R (log) all | R before 2012 | R from 2012 | step at 2012 given burned area (95% CI) |
|---|---|---|---|---|---|
| KAZ | naive | 0.86 | 0.87 | 0.89 | ×2.72 (1.95–3.78) |
| KAZ | harmonized | 0.88 | 0.87 | 0.89 | ×1.16 (0.88–1.53) |
| KAZ | harmonized_local | 0.88 | 0.87 | 0.89 | ×1.16 (0.88–1.53) |
| KGZ | naive | 0.54 | 0.75 | 0.51 | ×2.23 (1.54–3.25) |
| KGZ | harmonized | 0.65 | 0.79 | 0.51 | ×0.58 (0.40–0.85) |
| KGZ | harmonized_local | 0.65 | 0.74 | 0.51 | ×0.63 (0.44–0.88) |
| TJK | naive | 0.30 | 0.57 | 0.38 | ×2.95 (2.09–4.17) |
| TJK | harmonized | 0.50 | 0.58 | 0.37 | ×0.66 (0.47–0.93) |
| TJK | harmonized_local | 0.47 | 0.56 | 0.37 | ×0.78 (0.56–1.09) |
| TKM | naive | 0.30 | 0.62 | 0.52 | ×5.77 (4.34–7.66) |
| TKM | harmonized | 0.48 | 0.66 | 0.51 | ×1.87 (1.44–2.44) |
| TKM | harmonized_local | 0.50 | 0.52 | 0.51 | ×1.01 (0.76–1.34) |
| UZB | naive | 0.47 | 0.68 | 0.65 | ×4.67 (3.55–6.14) |
| UZB | harmonized | 0.61 | 0.66 | 0.64 | ×1.47 (1.16–1.88) |
| UZB | harmonized_local | 0.65 | 0.68 | 0.64 | ×1.00 (0.81–1.24) |

**Takeaway.** Holding burned area fixed, naive: continuous (95% CI includes 1) in none; KZ-harmonized: continuous (95% CI includes 1) in KAZ; locally harmonized: continuous (95% CI includes 1) in KAZ, TJK, TKM, UZB. The naive series jumps ×2.2–×5.8 everywhere. Correlation with burned area is high in Kazakhstan and weak in Kyrgyzstan/Tajikistan (few fires; much burned area there is not seen as active fire).

## 6. Events for the demo

Event = far more fire than usual for that place and month: harmonized cell-days in an H3 res-4 hexagon (~40 km across) minus its normal (median of the same hexagon and calendar month, 2001–2025); ranked by that excess; one per region and year in the top list. Region = ADM1 (pre-2022 boundaries).

| country | rank | region | month | cell-days | normal | excess |
|---|---|---|---|---|---|---|
| KAZ | 1 | Kyzylorda Region | 2003-04 | 583 | 168 | 415 |
| KAZ | 2 | Karaganda Region | 2005-07 | 380 | 0 | 380 |
| KAZ | 3 | West Kazakhstan Region | 2001-07 | 374 | 0 | 374 |
| UZB | 1 | Republic of Karakalpakstan | 2001-08 | 253 | 0 | 253 |
| UZB | 3 | Republic of Karakalpakstan | 2021-04 | 240 | 51 | 189 |
| UZB | 4 | Republic of Karakalpakstan | 2006-08 | 173 | 5 | 168 |
| TKM | 1 | Balkan | 2003-08 | 214 | 0 | 214 |
| TKM | 2 | Balkan | 2010-07 | 172 | 0 | 172 |
| TKM | 3 | Ahai | 2005-02 | 219 | 52 | 167 |
| KGZ | 1 | Jalal-Abad Region | 2007-11 | 151 | 0 | 151 |
| KGZ | 2 | Chuy Region | 2002-08 | 146 | 10 | 136 |
| KGZ | 3 | Chuy Region | 2006-08 | 135 | 26 | 109 |
| TJK | 1 | Khatlon Region | 2003-10 | 79 | 2 | 77 |
| TJK | 2 | Khatlon Region | 2004-10 | 59 | 2 | 57 |
| TJK | 3 | Khatlon Region | 2002-08 | 55 | 2 | 53 |

Known events (Kazakhstan), rank among all hexagon-month events:

| event | region | month | cell-days (best hexagon) | normal | excess | rank |
|---|---|---|---|---|---|---|
| Kostanay forest and steppe fires (Auliekol) | KZ-KUS | 2022-09 | 91 | 1 | 90 | 412 of 1255 |
| Abai region forest fire (Semey Ormany) | KZ-VOS | 2023-06 | 123 | 0 | 123 | 242 of 1255 |

**Takeaway.** Kostanay forest and steppe fires (Auliekol) (2022-09): 91 cell-days in one hexagon vs a normal of 1, rank 412 of 1255. Abai region forest fire (Semey Ormany) (2023-06): 123 cell-days in one hexagon vs a normal of 0, rank 242 of 1255. The top events are the largest local excesses; check them against news before the demo.

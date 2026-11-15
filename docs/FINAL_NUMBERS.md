# Final numbers (for slides, the submission page and the website)

Reports at 86fd3c3 (`reports/model_card.json`, `reports/validation.json`, `reports/VALIDATION.md`). Every line names
its source; the README is generated from the same files (`python -m pipeline.readme_numbers`).

- **90% interval coverage** (Kazakhstan, leave-one-region-out, same regions and data): **50% → 92%**
  (`model_card.json` → `intervals.coverage_before/after.T3_loro_region`: 0.503 → 0.918).
- **Uzbekistan 2012 jump:** naive ×4.32 → harmonized **×1.24** with Uzbekistan's own coefficients (MODIS alone ×1.38 =
  real change) (`validation.json` → `uz_test.steps`).
- **Turkmenistan 2012 jump:** naive ×3.48 → harmonized **×1.15** with its own coefficients (MODIS alone ×1.21)
  (`tm_stress.steps`).
- **Independent check vs MODIS burned area (MCD64A1):** with each country's own coefficients, no jump at 2012 in KZ, UZ,
  TM, TJ (95% CI includes 1); the naive splice jumps ×2.3–3.9 in those four. Relative to MODIS alone, the
  harmonized series stays within ×0.79–0.98 in all five countries, the naive one ×2.0–3.7 (`burned_area`).
- **Kazakhstan holdout 2020–2025:** error 9.8%, bias −0.9%, 90% interval coverage 92% (`model_card.json` → `scores`,
  `intervals.coverage_after.T2_holdout_country`).
- **Extrapolation test** (fit on each month's quieter years, predict the busier ones): chosen model 7.3% error, +3.7%
  bias; a constant ratio +10.4% bias (`docs/HARMONIZATION_REVIEW.md` §2.1, §6.2).
- **Kyrgyzstan / Tajikistan annual:** error 15% / 14% (raw MODIS: −70% / −72%) (`annual`).
- **Gas flares and industry masked** (likely sites, matched by coordinates, not verified on imagery): Tengiz, Zhanazhol,
  Kumkol, Temirtau, Balkhash, Almalyk, Mubarek (`docs/STATIC_SOURCES.md`).
- **Honest limits:**
  - Kyrgyzstan has few fires, and its burned-area check is inconclusive: MODIS alone shifts ×0.62 at 2012.
  - 2002–2004 is extrapolation, tested as above.
  - We count activity, not intensity.

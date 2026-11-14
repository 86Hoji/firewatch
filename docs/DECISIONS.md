# Decisions log (autonomous run, 2026-11-15)

## Summary (read this first)

**Finished:** both C3-review changes, the full re-run of all 10 countries, C4 (`reports/VALIDATION.md`), the KZ
before/after table (`reports/kz_before_after.md`), Phase D export (`web/public/data/`, 37.6 MB hex + < 1 MB rest,
no file > 5 MB, largest 2.1 MB). 39 tests pass; regression check OK against the new `reports/phase_c4` snapshot.
Committed and pushed.

**Key numbers**
* Satellite-wide S-NPP outage days: **61** (all 10 countries combined; 9 partial days deliberately excluded).
* New mask (type-2 rule, last 5 y), honest 2025–26 test: precision/recall KZ 94/88%, UZ 94/75%, TM 86/85%;
  Turkmenistan distortion −18% → −4%.
* Kazakhstan vs Phase B: hotspots +0.05% (2025–26 NRT only), all step ratios / backcast / holdout MAE identical,
  holdout bias −2.21 → −2.18%; LORO 17.3 → 18.5% and region coverage 41 → 91% (C3 changes).
* C4: KZ coefficients do **not** transfer (UZ as-is 35% error / −32% bias vs 18% local; IND −65%, PRT +59%);
  refitted locally the same model gets 5–9% in big countries. With local coefficients the 2012 jump disappears
  (UZ ×1.15, TM ×1.02) and the burned-area relation is continuous (UZ ×1.00, TM ×1.01).
  **The method transfers, the coefficients do not.**

**Did not go as expected / needs you**
* **Abai 2023 is not #1** (rank 242 of 1,255 hexagon-month events; Kostanay 2022 rank 412). My first event metric
  was flawed and replaced (#16); I did not tune further. In counts a forest fire is small next to Kazakhstan's
  steppe/farm burning. It is in `anomalies.json` as a known event. Your call whether the demo uses count anomalies or
  a different signal (FRP intensity would be the natural next metric).
* **Incident:** my parallel India/USA run crashed the main Brazil re-ingest (shared spill folder). Fixed at the
  cause (#15), all countries re-run, no data lost.
* The new Uzbek source (38.1°N 67.3°E) cannot be masked by any `type`-based rule: FIRMS calls 92% of its VIIRS
  detections vegetation fire (#19).
* The site's harmonized series outside Kazakhstan use KZ coefficients (as specified) and are biased for small-fire
  countries; per C4 the honest fix is a per-country refit — a decision for the next phase.

## Decisions

| # | time | decision | why |
|---|---|---|---|
| 1 | 02:00 | Stopped the old Brazil re-ingest (C3 code) and re-ran **all 10 countries** with the new mask + outage code. | The mask change alters cleaning for every country; old Brazil output would have been inconsistent. |
| 2 | 02:00 | Outage rule: a UTC day is an S-NPP outage when, summed over all countries, S-NPP ≤ 1% of NOAA-20 and NOAA-20 ≥ 500 (`config.yaml: outage`). | Data are bimodal: 59 days with exactly 0 S-NPP, 2 days with < 0.4%, then a gap up to partial-data days (7–28%). Partial days are not "satellite off"; filling them with NOAA-20 would double-count. 500 is half the 1st percentile of combined NOAA-20 days. |
| 3 | 02:00 | NOAA-20 fill only in cells where S-NPP saw nothing that day (was: all NOAA-20 cells on outage days). | Matters only on the 2 near-zero days; avoids double counting. |
| 4 | 02:00 | Mask window = last **5 years** of SP data before the split (test) / before the newest SP row (production). Chosen a priori, not tuned on the 2025–26 test. | Long enough for stable type-2 shares, short enough to catch new sites. Other windows appear in the report only as sensitivity. |
| 5 | 02:00 | Mask test keeps the honest split (built < 2025-01-01, tested 2025-01…2026-07) and reports the old C2 mask beside the new one. | As you asked. |
| 6 | 02:10 | KZ technical report renamed `reports/validation.md` → `reports/validation_kz.md`; API link updated (one line). | Windows treats `VALIDATION.md` and `validation.md` as the same file. |
| 7 | 02:10 | C4 module named `pipeline/07b_validation_package.py`; the export is `pipeline/08_export_web.py` as you specified. | Two steps both prefixed 08 would run together via `run_all 08`. |
| 8 | 02:35 | **Provisional run** while Brazil re-ingests: outage list from the 9 ready countries, C4 + export for them (Brazil row marked pending). The final run (all 10) overwrites everything automatically, then C4 + export are rerun. | You asked not to block on AU/BR. Australia had already finished; India and USA (queued after Brazil) were re-ingested in parallel. |
| 9 | 02:35 | Transfer-country "actual" = S-NPP + the country's OWN NOAA-20→S-NPP ratio on outage days. | The target is a property of the country's data, not of the model being tested; using KZ's ratio would leak the model into the target. |
| 10 | 02:35 | Transfer test, local refit = leave-one-year-out inside 2012–2019; KZ's own "as-is" row also leave-one-year-out. | Otherwise local and KZ rows would be in-sample and look better than they are. |
| 11 | 02:35 | Events: robust z of log(1 + harmonized cell-days) vs the same ADM1 region and calendar month (median/MAD, MAD floor 0.25, ≥ 30 cell-days above normal, one per region-year). Defined before looking at where Abai lands. | Unusual for that place and season, not just "big". Abai oblast (2022) is inside East Kazakhstan in the pre-2022 boundary file. |
| 12 | 02:40 | Web export: values ≤ 3 significant digits; **coordinates** 3 decimals for polygons, 2 for bbox/centers/markers. | 3 significant digits on a latitude (51.2) would move borders by ~10 km. |
| 13 | 02:40 | Transfer countries have no ADM1 files: display bbox for PRT (mainland), USA (contiguous), AUS, BRA, IND set in `config.yaml: web.countries`. | `meta.json` needs a bbox for all 10. |
| 15 | 02:45 | **Incident (my fault):** the parallel India/USA run deleted the shared DuckDB spill folder on exit; the main re-run crashed in Brazil. Fixed at the cause: per-process spill folder (`ingest.spill_dir`), and `02_clean` now saves `cleaning_summary.json` after every country (the crash had lost the summary for all countries it finished). Brazil restarted alone; KZ/UZ/TM/KG/TJ/PRT/AUS re-run once more afterwards so the summary matches the data. | Their hotspot/country files were already rewritten with the new code; only the summary was stale. |
| 16 | 02:55 | **Event metric replaced (decision 11 failed).** The region-month robust z ranked early-season farm burning first (months whose normal is 0 make z explode: 788 cell-days vs normal 0 → z = 27) and could not see wildfires: Abai June 2023 ranked 255th, Kostanay Sept 2022 was *below* a normal September (farm burning dwarfs a forest fire at oblast scale). New metric: excess cell-days over the median of the same **H3 res-4 hexagon** (~40 km) and calendar month, ranked by excess. Applied once; Abai's rank is reported as it comes out, no further tuning. | The first metric had a structural flaw independent of Abai; the new one measures "far more fire than usual for this place and month" at the scale of a large fire. |
| 17 | 02:55 | Takeaways rewritten to state only what the numbers show (removed "one overlap year is enough" and "TM behaves like agriculture"; burned-area text now derived from the confidence intervals). Added "harmonized with a local refit" to the 2012-step and burned-area tests. | Two claims were not backed by a computation; the local series shows whether the METHOD fixes the jump when coefficients are local. |
| 18 | 03:00 | Regression reference moved to a new snapshot `reports/phase_c4` (config `regression.snapshot`), taken after the final run; `phase_b` kept. `python -m pipeline.regression_check --snapshot` writes one. | The mask and outage changes alter KZ on purpose (2025+ NRT rows, NOAA-20 fill), so Phase B can no longer be "identical"; `reports/kz_before_after.md` documents exactly what moved. |
| 19 | 04:05 | Checked whether the production UZ mask (data through 2026) catches the new site near 38.1°N 67.3°E: no (0 of 91 cells). Documented, not "fixed". | FIRMS labels 92% of its VIIRS detections type 0; masking it would need a non-`type` rule (e.g. persistence), which C2 showed removes real farm fires. |
| 20 | 04:06 | `anomaly_pct` = 100 × (value − normal) / max(normal, 10) (`web.anomaly_normal_floor`). | Hexagons with normal 0 gave 38,000%. |
| 21 | 04:06 | Export empties `web/public/data/` instead of deleting the folder. | Windows refused to delete a folder a shell was inside. |
| 22 | 04:06 | Site series for non-KZ countries use the KZ coefficients, exactly as your spec and the product's current state; the bias is documented in `docs/PHASE_D.md`, not silently corrected with local fits. | Switching the product to per-country coefficients changes what was validated as "the model" — your decision. |
| 14 | 02:40 | `last_ym` = latest month complete in every exported country; `first_ym` = 2001-01. lo90 = hi90 = value from 2012 (observed). Hex months after `last_ym` are `null`. | One time axis for the whole site; partial months would look like a drop. |

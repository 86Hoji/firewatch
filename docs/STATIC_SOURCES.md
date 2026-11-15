# Static heat sources leaking onto the map (2026-11-15)

**Symptom:** isolated tall hexagon columns on the Caspian coast (Tengiz/Atyrau), around Aktobe, Kumkol in the south and
at the industrial cities, every year.

**Cause:** every one of these sites *was* in the static mask: FIRMS labels 75–99% of their archive detections
type 2 (static land source). But the mask only removed **NRT** rows. Archive rows were filtered by `type` alone, and
FIRMS labels 1–8% of a flare's detections type 0 (vegetation). Over 14 years that is hundreds of detections per cell
(621 at Korolev/Tengiz, 701 at Kenkiyak, 2,420 at the Pavlodar site), so the cells lit up every month. A second, smaller
group of static cells (e.g. Angren, Chirchiq, Ustyurt, parts of Zhanazhol) is mostly labelled type 0 by FIRMS and never
entered the mask.

**Persistence signature** (VIIRS 2012–2025, cleaned data, res-7 cells): the top cells are active in 139–168 of 168
months, in all 14 years and all 12 calendar months, with 75–100% of detections at night and low FRP (1–8 MW). Real
fires in Kazakhstan are seasonal and mostly in the 13:30 overpass: across all cells, 33% (KZ) / 40% (UZ) of detections
are at night. Among cells active ≥ 24 months, the night share is bimodal (farm fields ~0–0.1, static sources 0.75–1.0).

## Fix (config.yaml `cleaning.static_mask`, pipeline/ingest.py)

1. `drop_all_rows: true`: **every** row in a masked cell is dropped (MODIS and VIIRS, archive and NRT, any `type`).
2. Type rule on the last 5 years **and** on all history (`type_all_history`), so sites that stopped or changed are
   included. Type 3 (FIRMS "offshore", which is how it labels Temirtau steel) counts as static (`static_types: [2, 3]`).
3. New rule `static_site` for static sources that FIRMS labels type 0: VIIRS-active in ≥ 36 distinct months, in ≥ 8
   calendar months, ≥ 50% of detections at night. Thresholds were set from the distribution above (midpoint of the
   bimodal night share; 36 months = 3 full years), before the re-run, and were not tuned afterwards.

Mask cells: KZ 91 → 424 (372 type rule + 52 static_site), UZ 91 → 261 (206 + 55).

Rows removed by the mask step (after the type filter):

| country | removed | of rows |
|---|---|---|
| KAZ | 77,430 | 2.4% |
| UZB | 49,746 | 15.7% |
| TKM | 111,169 | 34.0% |
| KGZ | 3,157 | 7.4% |
| TJK | 2,095 | 12.5% |
| PRT | 2,346 | 0.9% |

AUS, IND, USA and BRA were **not** re-cleaned yet (old rule; they feed only the transfer table and the outage list).

## Top 20 recurring cells (before the fix), with likely sites

Site names come from matching coordinates against known facilities (within ~15 km). They are *likely* labels, not
verified on imagery. "Leaked" = type-0 archive detections that passed cleaning before this fix.

### KAZ

| # | lat, lon | active months (of 168) | years | calendar months | night share | FIRMS type 2 / 3 (VIIRS SP) | type-0 detections that leaked | likely site | now masked by |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 50.040, 73.013 | 168 | 14 | 12 | 0.82 | 89% / 10% | 310 | Temirtau steel works (Karaganda) | type2 |
| 2 | 52.084, 76.854 | 168 | 14 | 12 | 0.87 | 99% / 0% | 128 | Aksu ferroalloy plant (Pavlodar) | type2 |
| 3 | 48.234, 57.351 | 168 | 14 | 12 | 0.77 | 99% / 0% | 294 | Zhanazhol oil-gas field (Aktobe) | type2 |
| 4 | 48.384, 57.424 | 167 | 14 | 12 | 0.75 | 98% / 0% | 181 | Zhanazhol oil-gas field (Aktobe) | type2 |
| 5 | 46.821, 74.938 | 167 | 14 | 12 | 0.76 | 98% / 0% | 131 | Balkhash copper smelter | type2 |
| 6 | 46.833, 74.950 | 166 | 14 | 12 | 0.88 | 98% / 0% | 154 | Balkhash copper smelter | type2 |
| 7 | 50.063, 73.058 | 166 | 14 | 12 | 0.90 | 97% / 0% | 312 | Temirtau steel works (Karaganda) | type2 |
| 8 | 48.327, 57.434 | 165 | 14 | 12 | 0.75 | 97% / 0% | 578 | Zhanazhol oil-gas field (Aktobe) | type2 |
| 9 | 48.387, 57.423 | 162 | 14 | 12 | 0.89 | 98% / 0% | 164 | Zhanazhol oil-gas field (Aktobe) | type2 |
| 10 | 46.156, 53.407 | 161 | 14 | 12 | 0.84 | 95% / 0% | 286 | Tengiz oil field (Atyrau) | type2 |
| 11 | 46.823, 74.932 | 161 | 14 | 12 | 0.81 | 96% / 0% | 267 | Balkhash copper smelter | type2 |
| 12 | 50.399, 80.183 | 160 | 14 | 12 | 0.81 | 98% / 0% | 188 | Semey area industry (East Kazakhstan) | type2 |
| 13 | 50.347, 57.131 | 159 | 14 | 12 | 0.88 | 98% / 0% | 413 | Aktobe ferroalloy plant | type2 |
| 14 | 46.153, 53.413 | 156 | 14 | 12 | 0.84 | 92% / 0% | 187 | Tengiz oil field (Atyrau) | type2 |
| 15 | 47.768, 67.747 | 155 | 14 | 12 | 0.82 | 94% / 0% | 566 | Zhezkazgan copper smelter | type2 |
| 16 | 45.898, 53.288 | 148 | 14 | 12 | 0.81 | 92% / 0% | 621 | Korolev / Tengiz-area oil field (Atyrau) | type2 |
| 17 | 50.064, 73.067 | 145 | 14 | 12 | 0.81 | 96% / 0% | 86 | Temirtau steel works (Karaganda) | type2 |
| 18 | 46.052, 65.044 | 144 | 14 | 12 | 0.88 | 98% / 0% | 158 | Kumkol-group oil fields (Kyzylorda) | type2 |
| 19 | 51.259, 75.679 | 143 | 14 | 12 | 0.90 | 45% / 0% | 2,420 | unidentified site, Pavlodar region (Ekibastuz–Bayanaul) | type2 |
| 20 | 47.880, 57.461 | 139 | 14 | 12 | 0.83 | 95% / 0% | 701 | Kenkiyak / Zhanazhol area oil field (Aktobe) | type2 |

### UZB

| # | lat, lon | active months (of 168) | years | calendar months | night share | FIRMS type 2 / 3 (VIIRS SP) | type-0 detections that leaked | likely site | now masked by |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 40.860, 69.538 | 168 | 14 | 12 | 0.82 | 99% / 0% | 145 | Almalyk mining-metallurgical complex | type2 |
| 2 | 38.455, 65.805 | 168 | 14 | 12 | 0.97 | 98% / 0% | 94 | Kashkadarya gas fields | type2 |
| 3 | 40.867, 69.532 | 168 | 14 | 12 | 0.78 | 98% / 0% | 227 | Almalyk mining-metallurgical complex | type2 |
| 4 | 39.188, 65.288 | 168 | 14 | 12 | 1.00 | 98% / 0% | 179 | Mubarek gas-processing area | type2 |
| 5 | 41.508, 64.545 | 167 | 14 | 12 | 1.00 | 99% / 0% | 101 | Kyzylkum, Muruntau / Zarafshan mining area | type2 |
| 6 | 38.558, 65.952 | 167 | 14 | 12 | 0.90 | 94% / 0% | 462 | Kashkadarya gas fields / Shurtan–Mubarek processing | type2 |
| 7 | 38.681, 65.958 | 166 | 14 | 12 | 0.93 | 96% / 0% | 453 | Kashkadarya gas fields / Shurtan–Mubarek processing | type2 |
| 8 | 38.460, 65.792 | 165 | 14 | 12 | 0.93 | 75% / 0% | 870 | Kashkadarya gas fields | type2 |
| 9 | 40.934, 69.649 | 163 | 14 | 12 | 0.94 | 98% / 0% | 78 | Almalyk / Akhangaran industrial area | type2 |
| 10 | 40.055, 65.292 | 162 | 14 | 12 | 0.97 | 99% / 0% | 105 | Navoi industrial zone (Navoiyazot, power plant) | type2 |
| 11 | 40.931, 69.649 | 162 | 14 | 12 | 0.90 | 98% / 0% | 70 | Almalyk / Akhangaran industrial area | type2 |
| 12 | 38.686, 65.987 | 156 | 14 | 12 | 1.00 | 98% / 0% | 58 | Kashkadarya gas fields / Shurtan–Mubarek processing | type2 |
| 13 | 38.683, 65.988 | 154 | 14 | 12 | 1.00 | 98% / 0% | 47 | Kashkadarya gas fields / Shurtan–Mubarek processing | type2 |
| 14 | 38.624, 66.067 | 143 | 14 | 12 | 0.98 | 95% / 0% | 200 | Kashkadarya gas fields / Shurtan–Mubarek processing | type2 |
| 15 | 39.499, 64.695 | 140 | 14 | 12 | 0.95 | 77% / 0% | 387 | Bukhara gas fields | type2 |
| 16 | 40.217, 69.221 | 139 | 14 | 12 | 0.99 | 93% / 0% | 132 | Bekabad steel plant area | type2 |
| 17 | 40.858, 69.546 | 135 | 14 | 12 | 0.89 | 80% / 0% | 82 | Almalyk mining-metallurgical complex | type2 |
| 18 | 40.216, 69.225 | 134 | 13 | 12 | 0.94 | 99% / 0% | 26 | Bekabad steel plant area | type2 |
| 19 | 38.801, 64.643 | 132 | 13 | 12 | 0.94 | 94% / 0% | 306 | Bukhara / Kandym gas fields | type2 |
| 20 | 38.563, 65.955 | 130 | 14 | 12 | 0.98 | 95% / 0% | 43 | Kashkadarya gas fields / Shurtan–Mubarek processing | type2 |

After the fix all 40 cells are masked. In the exported hexagons (web/public/data/hex/*/r7) the harmonized cell-days
in masked cells went from 26,208 (KZ) and 19,264 (UZ) to 0.

## What is left (not masked; candidates to look at)

The most recurring cells after the fix are active in ≤ 68 months (before: up to 129):
* **KZ, 40.96–40.99 N 68.54 E** (Turkestan region, by the Uzbek border) and **44.8–45.1 N 64.6–64.8 E** (Syr Darya
  rice belt, Kyzylorda): ~0–2% night, high FRP, so most likely recurring crop-residue burning. The rule leaves them, as intended.
* **KZ, 47.91 N 56.50 E** (Aktobe oil region) and **51.21 N 51.21 E** (likely the Chinarevskoye field, West Kazakhstan):
  night-only, but active in only 7 calendar months, so the ≥ 8 rule misses them. Small (≤ 60 active months), still visible.
* **UZ, 40.31–40.37 N 63.6–63.7 E** (Kyzylkum, Navoi region): all year, high FRP (7–9), but mostly daytime (25% night).
  Unidentified, possibly a mine or plant working day shifts. The rule cannot catch it without catching farmland.
* The new 2025 Uzbek source at 38.1 N 67.3 E has < 36 active months, so it is still not maskable. It stays flagged
  as NOT A FIRE in docs/EVENTS.md.

## Effect

Honest 2025–26 mask test (reports/static_mask_check.md; precision/recall against FIRMS type 2): KZ 92/89% → 88/94%,
UZ 94/76% → 83/76%, TM 86/85% → 80/96%. The lower precision is mostly by construction: type-0 rows inside flare
cells now count as "false positives", and they are exactly the rows this fix removes.

Kazakhstan (reports/kz_before_after.md, C4 snapshot → now): hotspots 3,172,931 → 3,107,590 (−2.1%); holdout
2020+ MAE 10.3 → 9.8%, bias −2.2 → −0.9%, coverage 0.83 → 0.92; LORO median 18.5 → 13.5%; backcast T1 MAE 6.9 → 7.0%,
bias −2.1 → −2.5%; harmonized 2012 step ratio unchanged (0.924); monthly step factor 0.86 → 0.79.

Transfer (reports/VALIDATION.md, local refit, leave-one-year-out 2012–2019): UZ 17.7 → 15.6%, TM 22.9 → 16.0%;
KZ-as-is TM 42.3 → 26.0%. UZ step ratio with local coefficients ×1.15 → ×1.24, TM ×1.02 → ×1.15.

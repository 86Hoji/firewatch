# Phase C — extend and improve

## C1 — multi-country ingestion

### What changed, in plain words
* **One list of inputs.** [`pipeline/manifest.csv`](../pipeline/manifest.csv) says, for every FIRMS request id, which
  country it belongs to (ISO3 code) and its role: `train` (KZ), `test` (UZ), `stress` (TM), `extra` (KG, TJ),
  `exclude` (the UZ bounding-box backup), `transfer` (PRT, AUS, BRA, USA, IND — confirmed by you from
  `python -m pipeline.inventory`, which lists any zip not in the manifest with rows, dates, bbox and a guessed country).
  A zip that is not in the manifest is never read; a manifest id without a zip, or the same id twice, stops the run.
* **Every table has a `country` column**, and countries are processed one at a time, so nothing can be merged by
  accident: `data/processed/hotspots/country=XXX/…`, `data/aggregated/cell_month_all.parquet` (country, cell, month),
  `data/aggregated/country_month/XXX.parquet`, `data/reference/static_mask/XXX.parquet`,
  `reports/cleaning_summary.json` (one block per country).
* **Two output levels.** Central Asia (train/test/stress/extra) keeps cell-level data (maps, regions). The five
  transfer countries keep **country-month totals only**: their cleaned points live in a temporary DuckDB file outside
  OneDrive and are deleted as soon as the totals are written.
* **No per-row Python loops.** Cleaning is SQL in DuckDB ([`pipeline/ingest.py`](../pipeline/ingest.py)); H3 cells come
  from DuckDB's `h3` extension (same H3 library as before — checked on the same point). CSVs are streamed out of the
  zips in 1-million-row chunks, so memory stays flat whatever the file size; DuckDB spills to disk above 4 GB.
* **One implementation of the cleaning rules.** The old pandas functions are now thin wrappers over the same SQL, so
  Elbek's unit tests test the new code. New test: the fast country-month query equals the sum of cell-months.

### Regression check (KZ must not move)
`python -m pipeline.regression_check` compares with the Phase B snapshot in `reports/phase_b/`:
cleaning steps, hotspots per satellite-year, yearly sums of all 25 cell-month columns, country-month = Σ cell-month,
and every number in `metrics.json`, `model_comparison.json`, `model_selection.json` (relative tolerance 1e-9).
**Result: identical.** Tests: 31 passed.

### Speed (this laptop)
| step | before (KZ only) | now |
|---|---|---|
| clean | 40 s | 38 s for all 5 Central Asian countries |
| grid | 15 s | 28 s for all 5 |
| transfer countries | impossible (all rows in pandas memory) | PRT 4 s, IND 2.5 min, USA 4 min, AUS 15.5 min, BRA 25 min |

### What the data look like (all countries, same cleaning rules)
| country | role | raw rows | kept | % kept | removed as `type≠0` | NRT rows removed by mask | first – last |
|---|---|---|---|---|---|---|---|
| KAZ | train | 3,919,557 | 3,171,270 | 81% | 482,852 | 13,750 | 2000-11 – 2026-11 |
| UZB | test | 568,405 | 311,155 | 55% | 207,251 | 6,078 | 2000-11 – 2026-11 |
| TKM | stress | 786,454 | 305,188 | **39%** | 425,545 | 22,017 | 2000-11 – 2026-11 |
| KGZ | extra | 71,790 | 42,112 | 59% | 24,439 | 647 | 2000-11 – 2026-11 |
| TJK | extra | 27,448 | 16,280 | 59% | 8,884 | 453 | 2000-11 – 2026-11 |
| PRT | transfer | 278,864 | 256,569 | 92% | 9,287 | 312 | 2000-11 – 2026-11 |
| IND | transfer | 18,036,968 | 13,261,137 | 74% | 1,830,467 | 56,619 | 2000-11 – 2026-11 |
| USA | transfer | 17,311,429 | 13,936,929 | 81% | 2,460,603 | 99,532 | 2000-11 – 2026-11 |
| AUS | transfer | 39,548,554 | 35,591,968 | 90% | 410,418 | 9,657 | 2000-11 – 2026-11 |
| BRA | transfer | 46,426,727 | 42,020,892 | 91% | 625,423 | 13,439 | 2000-11 – 2026-11 |

Turkmenistan loses 61% of its rows to `type≠0` — the gas flares we expected; it is the right stress test for C2.

**First look at transfer (2013–2019, VIIRS S-NPP ÷ MODIS):**

| country | cell-days ratio | points ratio |
|---|---|---|
| PRT | 1.58 | 2.75 |
| KAZ | 1.81 | 3.35 |
| AUS | 2.03 | 4.56 |
| USA | 2.18 | 3.59 |
| BRA | 2.48 | 3.82 |
| KGZ | 3.46 | 4.08 |
| TJK | 3.88 | 4.49 |
| UZB | 3.95 | 4.62 |
| TKM | 4.20 | 5.07 |
| IND | 4.54 | 5.79 |

The ratio depends on the kind of fires: large steppe/forest fires (KZ, PRT, AUS) need a small correction; many small
agricultural burns (UZ, TM, IND, KG/TJ) need a large one, because VIIRS' finer pixels catch fires MODIS misses.
**This already tells us the KZ coefficients will not transfer as-is to Uzbekistan or India** — C4 will measure how
badly, and whether a local refit fixes it.

### Not done yet / known
* The S-NPP outage threshold (20 NOAA-20 detections per day) is still one number for all countries; KGZ/TJK have
  0–1 outage days because of it. To revisit in C3/C4.
* `data/raw/modis/` (yearly MODIS zips) is not used.

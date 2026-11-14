# Phase D — static website data (`pipeline/08_export_web.py` → `web/public/data/`)

Run: `python -m pipeline.run_all 08` (after 07b). Deterministic except `meta.generated_at`.

| file | content |
|---|---|
| `meta.json` | `countries[{code,name,bbox,center}]`, `first_ym` 2001-01, `last_ym` (latest month complete in all countries), `model{name,id,trained_on,calibration,holdout,interval}`, `generated_at` |
| `series/{CC}.json` (10) | `ym[]`, `naive_points[]`, `naive_celldays[]`, `modis_only[]`, `harmonized[]`, `lo90[]`, `hi90[]`, `viirs[]` (null before 2012) |
| `regions/{CC}.json` (KAZ UZB TKM KGZ TJK) | `regions[{iso,name,ym[],harmonized[],lo90[],hi90[]}]` |
| `hex/{CC}/r5|r7/{YYYY}.json` (KAZ UZB) | `months["YYYY-MM"×12]`, `cells{h3:[12]}`; cells with no fire that year omitted; months after `last_ym` = null |
| `anomalies.json` | `[{country,region,ym,value,anomaly_pct,lat,lon,title}]` top-3 per country + known events (Abai 2023, Kostanay 2022) |
| `validation.json` | copy of `reports/validation.json` |
| `boundaries/{CC}_adm1.geojson` (5) | simplified (0.01°), `shapeName`, `shapeISO` |

Meaning:
* `harmonized`: production model (fitted on KZ) applied to every country, as the C4 transfer test does. Before 2012
  MODIS → S-NPP equivalent; from 2012 observed S-NPP (+ NOAA-20 on outage days), so lo90 = hi90 = value.
  **Outside Kazakhstan the C4 transfer table applies**: the KZ coefficients under-estimate pre-2012 levels in
  small-fire countries (UZ, TM, IND, …) and over-estimate them in Portugal — the site should say so next to those charts.
* `lo90/hi90`: C3 intervals at the level shown (country interval in `series/`, region interval in `regions/`).
* `anomalies.value` = cell-days in the event's H3 res-4 hexagon; `anomaly_pct` = 100 × (value − normal) /
  max(normal, 10); lat/lon = fire-weighted centre.
* Rounding: values ≤ 3 significant digits; coordinates 3 decimals (polygons) / 2 (meta, markers).

Size: hex 37.6 MB (largest file 2.1 MB, none > 5 MB), everything else < 1 MB.

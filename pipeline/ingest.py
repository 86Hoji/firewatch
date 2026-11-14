"""Multi-country ingestion in DuckDB: manifest, staging from zips, cleaning, H3 aggregation.

One implementation of the cleaning rules (SQL), used by the pipeline for every country and, through thin wrappers in
02_clean.py, by the unit tests. H3 cells come from the DuckDB `h3` extension (same H3 C library as h3-py), so no
per-row Python loops.

Data flow per country (see pipeline/manifest.csv):
  zips --(pandas chunks, unify)--> table raw --(SQL cleaning)--> table clean
  cell-level roles (train/test/stress/extra): clean -> data/processed/hotspots/country=XXX/sensor=/year=/
  totals-only roles (transfer):               clean -> data/aggregated/country_month/XXX.parquet, nothing else
The work database lives outside the project (system temp by default) and is deleted after each country.
"""
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from pipeline.common import ROOT, get_logger, outage_days_sql

log = get_logger("ingest")
ZIP_NAME = re.compile(r"DL_FIRE_([A-Z0-9]+-C\d+)_(\d{6})")

# sensor groups for cell-day counting (n_* = distinct days, p_* = points)
GROUPS = {
    "modis": "sensor = 'MODIS'",
    "modis_terra": "platform = 'Terra'",
    "modis_aqua": "platform = 'Aqua'",
    "viirs_snpp": "platform = 'SNPP'",
    "viirs_noaa20": "platform = 'NOAA20'",
    "viirs_noaa21": "platform = 'NOAA21'",
    "viirs_all": "sensor = 'VIIRS'",
}
RAW_COLS = ["sensor", "platform", "lat", "lon", "datetime_utc", "date", "daynight", "confidence", "confidence_norm",
            "frp", "type", "processing", "request_id", "src_order"]
HOTSPOT_COLS = ["sensor", "platform", "lat", "lon", "datetime_utc", "date", "year", "month", "daynight",
                "confidence", "confidence_norm", "frp", "type", "processing", "h3_cell"]


# ---------------------------------------------------------------- connection, manifest

def connect(cfg, path=":memory:"):
    con = duckdb.connect(str(path))
    inp = cfg.get("inputs", {})
    if inp.get("duckdb_memory_limit"):
        con.execute(f"SET memory_limit = '{inp['duckdb_memory_limit']}'")
    con.execute(f"SET temp_directory = '{work_dir(cfg).as_posix()}/spill'")
    con.execute("SET preserve_insertion_order = false")
    try:
        con.execute("LOAD h3")
    except duckdb.Error:
        con.execute("INSTALL h3 FROM community")
        con.execute("LOAD h3")
    return con


def work_dir(cfg):
    d = cfg.get("inputs", {}).get("work_dir")
    p = Path(d) if d else Path(tempfile.gettempdir()) / "firewatch_work"
    p = p if p.is_absolute() else ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_manifest(cfg):
    """Manifest joined with the zip files on disk. Unlisted zips are reported, never used."""
    inp = cfg["inputs"]
    man = pd.read_csv(ROOT / inp["manifest"], dtype={"request_id": int, "country": str, "role": str})
    if man["request_id"].duplicated().any():
        raise SystemExit(f"duplicate request ids in manifest: {man.loc[man['request_id'].duplicated(), 'request_id'].tolist()}")
    files = {}
    for p in sorted((ROOT / inp["zips_dir"]).glob("*.zip")):
        m = ZIP_NAME.match(p.name)
        if not m:
            continue
        rid = int(m.group(2))
        if rid in files:
            raise SystemExit(f"request id {rid} appears twice: {files[rid][1].name}, {p.name}")
        files[rid] = (m.group(1), p)
    unlisted = sorted(set(files) - set(man["request_id"]))
    if unlisted:
        log.warning("zips not in manifest (ignored, run `python -m pipeline.inventory`): %s", unlisted)
    missing = sorted(set(man["request_id"]) - set(files))
    if missing:
        raise SystemExit(f"manifest ids without a zip in {inp['zips_dir']}: {missing}")
    man["sensor_code"] = man["request_id"].map(lambda r: files[r][0])
    man["path"] = man["request_id"].map(lambda r: files[r][1])
    return man


def countries(cfg, man=None, level=None):
    """Countries to process, in manifest order. level: 'cell' | 'totals' | None (both)."""
    man = load_manifest(cfg) if man is None else man
    inp = cfg["inputs"]
    roles = {"cell": inp["cell_level_roles"], "totals": inp["totals_only_roles"]}
    keep = roles[level] if level else roles["cell"] + roles["totals"]
    return list(dict.fromkeys(man.loc[man["role"].isin(keep), "country"]))


def level_of(cfg, man, country):
    role = man.loc[man["country"] == country, "role"].iloc[0]
    return "cell" if role in cfg["inputs"]["cell_level_roles"] else "totals"


# ---------------------------------------------------------------- staging

def stage(con, cfg, files, unify, platforms_ok):
    """files: manifest rows of one country. Streams every CSV of every zip into table `raw` in chunks."""
    con.execute("DROP TABLE IF EXISTS raw")
    chunk_rows = int(cfg["inputs"].get("chunk_rows", 1_000_000))
    order, created, per_file = 0, False, []
    for f in files.itertuples():
        expected = set(platforms_ok[f.sensor_code])
        with zipfile.ZipFile(f.path) as z:
            for name in sorted(n for n in z.namelist() if n.endswith(".csv")):
                n_file = 0
                for ch in pd.read_csv(z.open(name), dtype={"acq_time": str, "version": str, "confidence": str},
                                      chunksize=chunk_rows):
                    u = unify(ch, is_modis=f.sensor_code.startswith("M-"))
                    if "fire_nrt_" in name:
                        u["processing"] = "NRT"
                    bad = set(u["platform"].dropna().unique()) - expected
                    if bad:
                        raise SystemExit(f"{f.path.name}/{name}: platforms {bad} do not match sensor {f.sensor_code}")
                    u["request_id"] = f.request_id
                    u["src_order"] = np.arange(order, order + len(u), dtype="int64")
                    order += len(u)
                    n_file += len(u)
                    con.register("chunk", u[RAW_COLS])
                    if not created:
                        con.execute("CREATE TABLE raw AS SELECT * EXCLUDE (date), CAST(date AS DATE) AS date FROM chunk")
                        created = True
                    else:
                        con.execute("INSERT INTO raw BY NAME SELECT * EXCLUDE (date), CAST(date AS DATE) AS date FROM chunk")
                    con.unregister("chunk")
                per_file.append({"request_id": int(f.request_id), "file": name, "rows": n_file})
                log.info("  %s %-34s %10d rows", f.request_id, name, n_file)
    return per_file


# ---------------------------------------------------------------- cleaning (the only implementation)

def conf_ok_sql(cfg):
    c = cfg["cleaning"]
    keep = ", ".join(f"'{s[0]}'" for s in dict.fromkeys(x[0] for x in c["viirs_keep_confidence"]))
    return (f"(CASE WHEN sensor = 'MODIS' THEN TRY_CAST(confidence AS DOUBLE) >= {float(c['modis_min_confidence'])} "
            f"ELSE confidence_norm IN ({keep}) END)")


def type_ok_sql(cfg):
    return f"(type IS NULL OR type = {float(cfg['cleaning']['keep_type'])})"


def static_mask_sql(cfg, src, before=None):
    """Cells with mostly type-2 detections, or active >= N months in >= Y years. SP rows (with `type`) of src;
    before: optional 'YYYY-MM-DD' -> only rows with date < before (honest train/test split, C2)."""
    m = cfg["cleaning"]["static_mask"]
    when = f"AND date < DATE '{before}'" if before else ""
    return f"""
        WITH sp AS (SELECT h3_cell, year, date, type FROM {src} WHERE type IS NOT NULL {when}),
        per_cell AS (SELECT h3_cell, count(*) AS n, avg(CASE WHEN type = 2 THEN 1.0 ELSE 0.0 END) AS t2
                     FROM sp GROUP BY 1),
        by_type AS (SELECT h3_cell FROM per_cell WHERE n >= {int(m['min_detections'])} AND t2 >= {float(m['min_type2_share'])}),
        months AS (SELECT h3_cell, year, count(DISTINCT date_trunc('month', date)) AS nm FROM sp GROUP BY 1, 2),
        by_persist AS (SELECT h3_cell FROM months WHERE nm >= {int(m['min_months_per_year'])}
                       GROUP BY 1 HAVING count(*) >= {int(m['min_years_persistent'])})
        SELECT h3_cell, CASE WHEN h3_cell IN (SELECT h3_cell FROM by_type) THEN 'type2' ELSE 'persistent' END AS reason
        FROM (SELECT h3_cell FROM by_type UNION SELECT h3_cell FROM by_persist) ORDER BY h3_cell"""


def confident(con, cfg, src="raw", table="t1"):
    """Known platform + confidence filter + H3 cell, the first cleaning steps (also used by the mask check)."""
    res = int(cfg["grid"]["h3_res"])
    con.execute(f"""CREATE OR REPLACE TABLE {table} AS
        SELECT *, CAST(year(date) AS INTEGER) AS year, CAST(month(date) AS INTEGER) AS month,
               h3_latlng_to_cell_string(lat, lon, {res}) AS h3_cell
        FROM {src} WHERE platform IS NOT NULL AND {conf_ok_sql(cfg)}""")


def clean(con, cfg, src="raw"):
    """Cleaning steps on table/view `src` -> tables `clean` and `static_mask`; returns the step log.

    Order (identical to the baseline): unknown platform -> confidence -> H3 cell -> static mask (from SP rows) ->
    type != keep_type dropped -> NRT rows (no type) in masked cells dropped -> exact duplicates (first by source
    order kept) -> NRT rows on a day that has SP data for the same satellite dropped."""
    n_raw, n_plat = con.execute(f"SELECT count(*), count(platform) FROM {src}").fetchall()[0]
    confident(con, cfg, src)
    con.execute(f"CREATE OR REPLACE TABLE static_mask AS {static_mask_sql(cfg, 't1')}")
    con.execute(f"""CREATE OR REPLACE VIEW t2 AS SELECT * FROM t1 WHERE {type_ok_sql(cfg)}""")
    con.execute("""CREATE OR REPLACE VIEW t3 AS SELECT * FROM t2
                   WHERE NOT (type IS NULL AND h3_cell IN (SELECT h3_cell FROM static_mask))""")
    con.execute("""CREATE OR REPLACE TABLE t4 AS SELECT * FROM t3
                   QUALIFY row_number() OVER (PARTITION BY platform, lat, lon, datetime_utc ORDER BY src_order) = 1""")
    con.execute("""CREATE OR REPLACE TABLE clean AS
        WITH sp_days AS (SELECT DISTINCT platform, date FROM t4 WHERE processing = 'SP')
        SELECT t4.* FROM t4 LEFT JOIN sp_days s ON t4.platform = s.platform AND t4.date = s.date
        WHERE t4.processing = 'SP' OR s.platform IS NULL""")
    n1 = con.execute("SELECT count(*) FROM t1").fetchall()[0][0]
    n2 = con.execute("SELECT count(*) FROM t2").fetchall()[0][0]
    n3 = con.execute("SELECT count(*) FROM t3").fetchall()[0][0]
    n4 = con.execute("SELECT count(*) FROM t4").fetchall()[0][0]
    n5 = con.execute("SELECT count(*) FROM clean").fetchall()[0][0]
    counts = [("unknown_platform", n_raw, n_plat), ("confidence", n_plat, n1), ("type_not_vegetation", n1, n2),
              ("nrt_static_mask", n2, n3), ("exact_duplicates", n3, n4), ("nrt_overlaps_sp", n4, n5)]
    steps = [{"step": s, "rows_in": int(a), "rows_out": int(b), "removed": int(a - b)} for s, a, b in counts]
    for s in steps:
        log.info("  %-22s %10d -> %10d", s["step"], s["rows_in"], s["rows_out"])
    con.execute("DROP VIEW t3; DROP VIEW t2; DROP TABLE t4; DROP TABLE t1")
    return steps


# ---------------------------------------------------------------- aggregation

def cell_month_query(src):
    parts = []
    for g, cond in GROUPS.items():
        parts.append(f"count(DISTINCT CASE WHEN {cond} THEN date END) AS n_{g}")
        parts.append(f"count(DISTINCT CASE WHEN {cond} AND daynight = 'D' THEN date END) AS n_{g}_d")
        parts.append(f"count(DISTINCT CASE WHEN {cond} AND daynight = 'N' THEN date END) AS n_{g}_n")
        parts.append(f"count(CASE WHEN {cond} THEN 1 END) AS p_{g}")
    return f"""
        SELECT h3_cell, CAST(year AS INTEGER) AS year, CAST(month AS INTEGER) AS month, {', '.join(parts)}
        FROM {src} GROUP BY 1, 2, 3 ORDER BY 1, 2, 3"""


def outage_fill(con, src, min_n20):
    """NOAA-20 cell-days per cell-month on S-NPP outage days, and the number of outage days."""
    days = outage_days_sql(src, min_n20)
    gap = con.execute(f"""
        SELECT h3_cell, CAST(year AS INTEGER) AS year, CAST(month AS INTEGER) AS month,
               count(DISTINCT date) AS n_viirs_noaa20_gap
        FROM {src} WHERE platform = 'NOAA20' AND date IN ({days}) GROUP BY 1, 2, 3""").df()
    return gap, con.execute(f"SELECT count(*) FROM ({days})").fetchall()[0][0]


def country_month_query(src, min_n20):
    """Country-month totals straight from points: cell-days = distinct (cell, day) per group, summed over cells.
    Equal to summing cell_month over cells, but never materialises cells (used for 20-50M-row countries)."""
    any_, sums = [], []
    for g, cond in GROUPS.items():
        any_ += [f"bool_or({cond}) AS {g}", f"bool_or({cond} AND daynight = 'D') AS {g}_d",
                 f"bool_or({cond} AND daynight = 'N') AS {g}_n", f"count(*) FILTER (WHERE {cond}) AS pc_{g}"]
        sums += [f"sum({g}::INTEGER) AS n_{g}", f"sum({g}_d::INTEGER) AS n_{g}_d", f"sum({g}_n::INTEGER) AS n_{g}_n",
                 f"sum(pc_{g}) AS p_{g}"]
    return f"""
        WITH gap AS ({outage_days_sql(src, min_n20)}),
        cd AS (SELECT h3_cell, date, CAST(year AS INTEGER) AS year, CAST(month AS INTEGER) AS month,
                      {', '.join(any_)}, bool_or(platform = 'NOAA20' AND date IN (SELECT date FROM gap)) AS gapday
               FROM {src} GROUP BY 1, 2, 3, 4)
        SELECT year, month, {', '.join(sums)}, sum(gapday::INTEGER) AS n_viirs_noaa20_gap,
               count(DISTINCT h3_cell) AS n_active_cells, (SELECT count(*) FROM gap
               WHERE year(date) = cd.year AND month(date) = cd.month) AS n_outage_days
        FROM cd GROUP BY year, month ORDER BY year, month"""


def daily_counts_sql(src):
    """Detections per day and satellite (points): the input of the outage threshold and outage checks."""
    plats = ["SNPP", "NOAA20", "NOAA21", "Terra", "Aqua"]
    cols = ", ".join(f"count(*) FILTER (WHERE platform = '{p}') AS n_{p.lower()}" for p in plats)
    return f"SELECT date, {cols} FROM {src} GROUP BY date ORDER BY date"


def outage_threshold(cfg, country, daily=None):
    """Per-country S-NPP outage threshold (see config `outage`). Returns (threshold, info dict)."""
    from pipeline.common import AGG
    o = cfg["outage"]

    def typical(df):
        d = df[(pd.to_datetime(df["date"]) >= pd.Timestamp(o["typical_from"])) & (df["n_noaa20"] > 0)]
        return float(d["n_noaa20"].median()) if len(d) else 0.0

    def read(c):
        p = AGG / "country_day" / f"{c}.parquet"
        if not p.exists():
            raise SystemExit(f"{p} missing: run 02_clean for {c} first (reference country goes first)")
        return pd.read_parquet(p)

    t_c = typical(read(country) if daily is None else daily)
    ref = o["reference_country"]
    t_ref = t_c if (country == ref and daily is not None) else typical(read(ref))
    thr = max(int(o["min_threshold"]), int(round(o["reference_threshold"] * t_c / t_ref))) if t_ref else int(o["min_threshold"])
    return thr, {"threshold": thr, "typical_daily_noaa20": t_c, "reference_country": ref,
                 "reference_typical_daily_noaa20": t_ref}


def cells_table(con, cells, coarse_res):
    """Centre lat/lon and coarse parent for H3 cells, vectorized in DuckDB."""
    con.register("cells_in", pd.DataFrame({"h3_cell": cells}))
    out = con.execute(f"""SELECT h3_cell, h3_cell_to_parent(h3_cell, {int(coarse_res)}) AS h3_coarse,
                                 h3_cell_to_lat(h3_cell) AS lat, h3_cell_to_lng(h3_cell) AS lon
                          FROM cells_in""").df()
    con.unregister("cells_in")
    return out


def remove_work(path):
    for p in (Path(path), Path(str(path) + ".wal")):
        if p.exists():
            os.remove(p)
    shutil.rmtree(Path(path).parent / "spill", ignore_errors=True)

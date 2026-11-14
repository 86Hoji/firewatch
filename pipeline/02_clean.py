"""Clean every country in the manifest: unify MODIS/VIIRS schemas, filter confidence/type, static-source mask.

Rules are implemented once, in SQL (pipeline/ingest.py). The pandas helpers below (confidence_filter, type_filter,
drop_nrt_overlap, clean) are thin wrappers over the same SQL, kept for the unit tests.

Outputs per country (country = ISO3 from pipeline/manifest.csv):
  cell-level roles: data/processed/hotspots/country=XXX/sensor=.../year=.../*.parquet
  totals-only roles: data/aggregated/country_month/XXX.parquet (cleaned points are not kept)
  all: data/reference/static_mask/XXX.parquet, reports/cleaning_summary.json
"""
import re
import shutil

import duckdb
import numpy as np
import pandas as pd

from pipeline import ingest
from pipeline.common import AGG, PROCESSED, REF, REPORTS, ensure_dirs, get_logger, load_config, write_json

log = get_logger("clean")

PLATFORMS = {"Terra": "Terra", "T": "Terra", "Aqua": "Aqua", "A": "Aqua",
             "N": "SNPP", "NPP": "SNPP", "Suomi NPP": "SNPP", "SNPP": "SNPP",
             "1": "NOAA20", "N20": "NOAA20", "NOAA-20": "NOAA20", "J1": "NOAA20",
             "2": "NOAA21", "N21": "NOAA21", "NOAA-21": "NOAA21", "J2": "NOAA21"}
NRT_VERSION = re.compile(r"NRT|^\d{2}\.\d+$")


def processing_from_version(v):
    return np.where(v.astype(str).str.contains(NRT_VERSION), "NRT", "SP")


def modis_conf_class(c):
    return np.select([c >= 80, c >= 30], ["h", "n"], "l")


def unify(df, is_modis=None):
    """FIRMS CSV (any product) -> common schema. Vectorized: dates via to_datetime + minute offsets.

    FIRMS archive-download VIIRS files also name the column "brightness", so callers that know the sensor
    (zip file name) pass is_modis; the column check is the fallback for yearly country CSVs."""
    if is_modis is None:
        is_modis = "brightness" in df.columns and "bright_ti4" not in df.columns
    hhmm = pd.to_numeric(df["acq_time"].astype(str).str.strip(), errors="coerce").astype("int64")
    date = pd.to_datetime(df["acq_date"], format="%Y-%m-%d")
    conf = df["confidence"].astype(str).str.strip().str.lower()
    out = pd.DataFrame({
        "sensor": "MODIS" if is_modis else "VIIRS",
        "platform": df["satellite"].astype(str).str.strip().map(PLATFORMS),
        "lat": df["latitude"].astype("float64"),
        "lon": df["longitude"].astype("float64"),
        "date": date,
        "datetime_utc": date + pd.to_timedelta((hhmm // 100) * 60 + hhmm % 100, unit="min"),
        "daynight": df["daynight"].astype(str).str[0],
        "confidence": conf,
        "frp": pd.to_numeric(df["frp"], errors="coerce"),
        "type": pd.to_numeric(df["type"], errors="coerce") if "type" in df else np.nan,
        "version": df["version"].astype(str),
    })
    out["confidence_norm"] = (modis_conf_class(pd.to_numeric(conf, errors="coerce").fillna(0)) if is_modis
                              else conf.str[0])
    out["processing"] = processing_from_version(out["version"])
    return out


# ---- thin wrappers over the SQL rules (tests) ----

def _sql(df, query):
    con = duckdb.connect()
    con.register("df", df.reset_index(drop=True).assign(_i=np.arange(len(df))))
    out = con.execute(query + " ORDER BY _i").df().drop(columns="_i")
    return out


def confidence_filter(df, cfg):
    return _sql(df, f"SELECT * FROM df WHERE {ingest.conf_ok_sql(cfg)}")


def type_filter(df, cfg):
    return _sql(df, f"SELECT * FROM df WHERE {ingest.type_ok_sql(cfg)}")


def drop_nrt_overlap(df):
    return _sql(df, """SELECT df.* FROM df LEFT JOIN (SELECT DISTINCT platform, date FROM df WHERE processing = 'SP') s
                       USING (platform, date) WHERE df.processing = 'SP' OR s.platform IS NULL""").drop(
        columns=[c for c in ("platform_1", "date_1") if c in df])


def clean(df, cfg, steps):
    """Run the pipeline's SQL cleaning on a pandas frame -> (clean rows, static mask)."""
    con = ingest.connect(cfg)
    d = df.reset_index(drop=True).copy()
    if "src_order" not in d:
        d["src_order"] = np.arange(len(d), dtype="int64")
    con.register("src", d)
    steps += ingest.clean(con, cfg, "src")
    out = con.execute("SELECT * FROM clean ORDER BY src_order").df()
    return out, con.execute("SELECT * FROM static_mask").df()


# ---- pipeline ----

def run_country(cfg, man, country):
    level = ingest.level_of(cfg, man, country)
    files = man[man["country"] == country]
    log.info("%s (%s, %s): %s", country, level, files["role"].iloc[0], files["request_id"].tolist())
    path = ingest.work_dir(cfg) / f"work_{country}.duckdb"
    ingest.remove_work(path)
    con = ingest.connect(cfg, path)
    try:
        per_file = ingest.stage(con, cfg, files, unify, cfg["inputs"]["sensors"])
        steps = ingest.clean(con, cfg)
        (REF / "static_mask").mkdir(parents=True, exist_ok=True)
        mask = con.execute("SELECT * FROM static_mask").df()
        mask.to_parquet(REF / "static_mask" / f"{country}.parquet", index=False)
        by_platform = dict(con.execute("SELECT platform, count(*) FROM clean GROUP BY 1 ORDER BY 1").fetchall())
        span = con.execute("SELECT min(date), max(date) FROM clean").fetchall()[0]
        if level == "cell":
            out = PROCESSED / "hotspots" / f"country={country}"
            shutil.rmtree(out, ignore_errors=True)
            out.mkdir(parents=True)
            cols = ", ".join(ingest.HOTSPOT_COLS)
            con.execute(f"""COPY (SELECT {cols} FROM clean ORDER BY src_order) TO '{out.as_posix()}'
                            (FORMAT parquet, PARTITION_BY (sensor, year))""")
        else:
            thr = cfg["calibration"]["snpp_gap_min_noaa20"]
            cm = con.execute(ingest.country_month_query("clean", thr)).df()
            cm.insert(0, "country", country)
            (AGG / "country_month").mkdir(parents=True, exist_ok=True)
            cm.to_parquet(AGG / "country_month" / f"{country}.parquet", index=False)
    finally:
        con.close()
        ingest.remove_work(path)
    return {"role": files["role"].iloc[0], "level": level, "files": per_file, "steps": steps,
            "static_mask_cells": len(mask), "rows_by_platform": by_platform,
            "first_date": str(span[0]), "last_date": str(span[1])}


def main(only=None):
    ensure_dirs()
    cfg = load_config()
    man = ingest.load_manifest(cfg)
    for legacy in (PROCESSED / "hotspots").glob("sensor=*"):      # single-country layout before Phase C
        shutil.rmtree(legacy)
    if (REF / "static_mask.parquet").exists():
        (REF / "static_mask.parquet").unlink()
    p = REPORTS / "cleaning_summary.json"
    summary = (__import__("json").loads(p.read_text(encoding="utf-8")).get("countries", {}) if p.exists() else {})
    for c in ingest.countries(cfg, man):
        if only and c not in only:
            continue
        summary[c] = run_country(cfg, man, c)
    write_json(p, {"countries": summary})


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or None)

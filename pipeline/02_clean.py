"""Unify MODIS/VIIRS schemas, filter confidence/type, build static-source mask."""
import re
import zipfile
import shutil

import h3
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds

from pipeline.common import PROCESSED, RAW, REF, REPORTS, ROOT, ensure_dirs, get_logger, load_config, write_json

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
    # FIRMS archive-download VIIRS files also name the column "brightness", so callers that know the
    # sensor (zip file name) pass it; the column check is the fallback for yearly country CSVs.
    if is_modis is None:
        is_modis = "brightness" in df.columns and "bright_ti4" not in df.columns
    out = pd.DataFrame({
        "sensor": "MODIS" if is_modis else "VIIRS",
        "platform": df["satellite"].astype(str).str.strip().map(PLATFORMS),
        "lat": df["latitude"].astype("float64"),
        "lon": df["longitude"].astype("float64"),
        "acq_time": df["acq_time"].astype(str).str.zfill(4),
        "date": pd.to_datetime(df["acq_date"]).dt.date,
        "daynight": df["daynight"].astype(str).str[0],
        "confidence": df["confidence"].astype(str).str.strip().str.lower(),
        "frp": pd.to_numeric(df["frp"], errors="coerce"),
        "type": pd.to_numeric(df["type"], errors="coerce") if "type" in df else np.nan,
        "version": df["version"].astype(str),
    })
    out["datetime_utc"] = pd.to_datetime(out["date"].astype(str) + " " + out["acq_time"], format="%Y-%m-%d %H%M")
    if is_modis:
        out["confidence_norm"] = modis_conf_class(pd.to_numeric(out["confidence"], errors="coerce").fillna(0))
    else:
        out["confidence_norm"] = out["confidence"].str[0]
    out["processing"] = processing_from_version(out["version"])
    return out


ZIP_NAME = re.compile(r"DL_FIRE_([A-Z0-9]+-C\d+)_(\d{6})")


def find_zips(cfg):
    """{request_id: (sensor_code, path)} for the configured ids; a duplicate id (e.g. 'x (2).zip') is an error."""
    inp = cfg["inputs"]
    d = ROOT / inp["zips_dir"]
    found = {}
    for p in sorted(d.glob("*.zip")):
        m = ZIP_NAME.match(p.name)
        if not m:
            continue
        sensor, rid = m.group(1), int(m.group(2))
        if rid in found:
            raise SystemExit(f"request id {rid} appears twice: {found[rid][1].name}, {p.name}")
        found[rid] = (sensor, p)
    want = [int(r) for r in inp["request_ids"]]
    missing = [r for r in want if r not in found]
    if missing:
        raise SystemExit(f"zips not found in {d} for request ids {missing}")
    return {r: found[r] for r in want}


def load_zips(cfg):
    """Read fire_archive_*.csv and fire_nrt_*.csv straight from the zips (raw files are never modified)."""
    frames = []
    for rid, (sensor, path) in find_zips(cfg).items():
        expected = set(cfg["inputs"]["sensors"][sensor])
        with zipfile.ZipFile(path) as z:
            for name in sorted(n for n in z.namelist() if n.endswith(".csv")):
                with z.open(name) as fh:
                    df = pd.read_csv(fh, dtype={"acq_time": str, "version": str, "confidence": str})
                if df.empty:
                    continue
                u = unify(df, is_modis=sensor.startswith("M-"))
                if "fire_nrt_" in name:
                    u["processing"] = "NRT"
                bad = set(u["platform"].dropna().unique()) - expected
                if bad:
                    raise SystemExit(f"{path.name}/{name}: platforms {bad} do not match sensor {sensor}")
                log.info("%s %-34s %9d rows (%s..%s)", rid, name, len(u), u["date"].min(), u["date"].max())
                frames.append(u)
    return pd.concat(frames, ignore_index=True)


def load_raw(cfg=None):
    if cfg is not None and cfg.get("inputs", {}).get("source") == "zips":
        return load_zips(cfg)
    frames = []
    for p in sorted(RAW.rglob("*.csv")):
        df = pd.read_csv(p, dtype={"acq_time": str, "version": str, "confidence": str})
        if df.empty:
            continue
        u = unify(df)
        if p.parent.name == "api":
            u["processing"] = "NRT" if "_NRT_" in p.name else "SP"
        frames.append(u)
    if not frames:
        raise SystemExit("no CSV in data/raw — run 01_download first")
    return pd.concat(frames, ignore_index=True)


def confidence_filter(df, cfg):
    c = cfg["cleaning"]
    keep_viirs = {s[0] for s in c["viirs_keep_confidence"]}
    modis_ok = pd.to_numeric(df["confidence"], errors="coerce") >= c["modis_min_confidence"]
    viirs_ok = df["confidence_norm"].isin(keep_viirs)
    return df[np.where(df["sensor"] == "MODIS", modis_ok, viirs_ok)]


def type_filter(df, cfg):
    return df[df["type"].isna() | (df["type"] == cfg["cleaning"]["keep_type"])]


def build_static_mask(df, cfg):
    m = cfg["cleaning"]["static_mask"]
    sp = df[df["type"].notna()]
    per_cell = sp.groupby("h3_cell").agg(n=("type", "size"), type2=("type", lambda s: (s == 2).mean()))
    by_type = per_cell[(per_cell["n"] >= m["min_detections"]) & (per_cell["type2"] >= m["min_type2_share"])].index
    months = (sp.assign(ym=pd.to_datetime(sp["date"]).dt.to_period("M"))
                .groupby(["h3_cell", sp["year"]])["ym"].nunique())
    persistent_years = (months >= m["min_months_per_year"]).groupby(level=0).sum()
    by_persist = persistent_years[persistent_years >= m["min_years_persistent"]].index
    cells = sorted(set(by_type) | set(by_persist))
    mask = pd.DataFrame({"h3_cell": cells})
    mask["reason"] = np.where(mask["h3_cell"].isin(by_type), "type2", "persistent")
    return mask


def drop_nrt_overlap(df):
    sp_days = df.loc[df["processing"] == "SP", ["platform", "date"]].drop_duplicates()
    sp_days["has_sp"] = True
    m = df.merge(sp_days, on=["platform", "date"], how="left")
    keep = (m["processing"] == "SP") | m["has_sp"].isna()
    return df[keep.to_numpy()]


def clean(df, cfg, steps):
    def step(name, new):
        steps.append({"step": name, "rows_in": len(df), "rows_out": len(new), "removed": len(df) - len(new)})
        log.info("%-22s %9d -> %9d", name, len(df), len(new))
        return new

    df = step("unknown_platform", df[df["platform"].notna()])
    df = step("confidence", confidence_filter(df, cfg))
    res = cfg["grid"]["h3_res"]
    df = df.assign(year=pd.to_datetime(df["date"]).dt.year, month=pd.to_datetime(df["date"]).dt.month)
    df["h3_cell"] = [h3.latlng_to_cell(a, b, res) for a, b in zip(df["lat"].to_numpy(), df["lon"].to_numpy())]
    mask = build_static_mask(df, cfg)
    df = step("type_not_vegetation", type_filter(df, cfg))
    nrt_static = (df["type"].isna()) & df["h3_cell"].isin(set(mask["h3_cell"]))
    df = step("nrt_static_mask", df[~nrt_static])
    df = step("exact_duplicates", df.drop_duplicates(["platform", "lat", "lon", "datetime_utc"]))
    df = step("nrt_overlaps_sp", drop_nrt_overlap(df))
    return df, mask


def main():
    ensure_dirs()
    cfg = load_config()
    raw = load_raw(cfg)
    log.info("loaded %d raw rows", len(raw))
    versions = raw.groupby(["sensor", "version", "processing"]).size().rename("rows").reset_index()
    steps = []
    df, mask = clean(raw, cfg, steps)
    mask.to_parquet(REF / "static_mask.parquet", index=False)
    out = PROCESSED / "hotspots"
    shutil.rmtree(out, ignore_errors=True)
    cols = ["sensor", "platform", "lat", "lon", "datetime_utc", "date", "year", "month", "daynight",
            "confidence", "confidence_norm", "frp", "type", "processing", "h3_cell"]
    ds.write_dataset(pa.Table.from_pandas(df[cols], preserve_index=False), out, format="parquet",
                     partitioning=["sensor", "year"], partitioning_flavor="hive",
                     existing_data_behavior="overwrite_or_ignore")
    summary = {"steps": steps, "static_mask_cells": len(mask),
               "rows_by_platform": df.groupby("platform").size().to_dict(),
               "versions": versions.to_dict(orient="records")}
    write_json(REPORTS / "cleaning_summary.json", summary)
    log.info("wrote %s (%d rows)", out, len(df))


if __name__ == "__main__":
    main()

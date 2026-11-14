"""Phase D: static-website data export -> web/public/data/ (config `web`).

  meta.json                     countries [{code, name, bbox, center}], first_ym, last_ym, model, generated_at
  series/{CC}.json              monthly country series, all countries
  regions/{CC}.json             monthly ADM1 series, cell-level countries
  hex/{CC}/r5|r7/{YYYY}.json    harmonized cell-days per H3 cell and month (config web.hex_countries)
  anomalies.json                top events (07b_validation_package) incl. the known events
  validation.json               copy of reports/validation.json
  boundaries/{CC}_adm1.geojson  simplified ADM1 polygons (shapeName, shapeISO)

Harmonized = the production model (fitted on Kazakhstan) exactly as in 06_harmonize: MODIS -> S-NPP equivalent before
2012, S-NPP (+ NOAA-20 on satellite-wide S-NPP outage days) from 2012. lo90/hi90: C3 intervals at the level shown
(country interval for series/, region interval for regions/); from 2012 the value is observed, so lo90 = hi90.
Numbers are rounded to <= 3 significant digits; coordinates to web.coord_decimals.   python -m pipeline.08_export_web
"""
import datetime as dt
import importlib
import json
import math
import shutil

import geopandas as gpd
import h3
import numpy as np
import pandas as pd

from pipeline import calib, ingest, intervals
from pipeline.common import AGG, REPORTS, ROOT, get_logger, load_config

CAL = importlib.import_module("pipeline.05_calibrate")
PKG = importlib.import_module("pipeline.07b_validation_package")
log = get_logger("export_web")


# ---------------------------------------------------------------- helpers

def sig(x, n=3):
    """Round to n significant digits; ints stay ints; NaN/None -> None."""
    if x is None:
        return None
    x = float(x)
    if not math.isfinite(x):
        return None
    if x == 0:
        return 0
    r = round(x, -int(math.floor(math.log10(abs(x)))) + (n - 1))
    return int(r) if float(r).is_integer() else r


def sig_list(a, n=3):
    return [sig(v, n) for v in a]


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def ym_range(first, last):
    p = pd.period_range(first, last, freq="M")
    return p, [str(x) for x in p]


def full_months(df, periods, cols):
    idx = pd.MultiIndex.from_arrays([periods.year, periods.month], names=["year", "month"])
    return df.groupby(["year", "month"])[cols].sum().reindex(idx, fill_value=0).reset_index()


def last_complete_month(cfg, countries):
    """Latest month that is complete in every exported country (from 02_clean's last_date)."""
    summ = json.loads((REPORTS / "cleaning_summary.json").read_text(encoding="utf-8"))["countries"]
    ends = []
    for c in countries:
        d = pd.Timestamp(summ[c]["last_date"])
        ends.append(d.to_period("M") if d.is_month_end else d.to_period("M") - 1)
    return min(ends)


# ---------------------------------------------------------------- parts

def country_info(cfg, c):
    w = cfg["web"]["countries"][c]
    p = ROOT / cfg["regions"]["boundaries_dir"] / f"{c}_ADM1.geojson"
    k = cfg["web"]["coord_decimals_meta"]
    if "bbox" in w:
        bb = w["bbox"]
    else:
        bb = list(gpd.read_file(p).total_bounds)
    bb = [math.floor(bb[0] * 10 ** k) / 10 ** k, math.floor(bb[1] * 10 ** k) / 10 ** k,
          math.ceil(bb[2] * 10 ** k) / 10 ** k, math.ceil(bb[3] * 10 ** k) / 10 ** k]     # rounded outward
    center = w.get("center") or [(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2]
    return {"code": c, "name": w["name"], "bbox": bb, "center": [round(center[0], k), round(center[1], k)]}


def series(cfg, c, coefs, iv, periods, yms):
    cut = cfg["calibration"]["period"][0]
    cm = PKG.country_months(c, cfg)
    h = calib.harmonize(cm.assign(h3_cell="country"), coefs, cfg)
    cm = cm.assign(n_harm=h["n_harm"].to_numpy())
    d = full_months(cm, periods, ["p_modis", "p_viirs_snpp", "n_modis", "n_viirs_snpp", "v_target", "n_harm"])
    pre = (d["year"] < cut).to_numpy()
    harm = np.where(pre, d["n_harm"], d["v_target"])
    lo, hi = intervals.bounds(harm, iv["country"])
    return {"ym": yms,
            "naive_points": sig_list(np.where(pre, d["p_modis"], d["p_viirs_snpp"])),
            "naive_celldays": sig_list(np.where(pre, d["n_modis"], d["n_viirs_snpp"])),
            "modis_only": sig_list(d["n_modis"]),
            "harmonized": sig_list(harm),
            "lo90": sig_list(np.where(pre, lo, harm)), "hi90": sig_list(np.where(pre, hi, harm)),
            "viirs": [None if p else sig(v) for p, v in zip(pre, d["v_target"])]}


def harmonized_cells(cfg, c, coefs):
    if c == cfg["train_country"]:
        return pd.read_parquet(AGG / "cell_month.parquet")
    return calib.harmonize(CAL.load_cell_month(c, cfg), coefs, cfg)


def regions(cfg, cm, iv, periods, yms):
    cut = cfg["calibration"]["period"][0]
    out = []
    for (iso, name), g in cm[cm["adm1_id"] != "outside"].groupby(["adm1_id", "adm1_name"]):
        d = full_months(g, periods, ["n_harm"])
        x = d["n_harm"].to_numpy(float)
        pre = (d["year"] < cut).to_numpy()
        lo, hi = intervals.bounds(x, iv["region"])
        out.append({"iso": iso, "name": name, "ym": yms, "harmonized": sig_list(x),
                    "lo90": sig_list(np.where(pre, lo, x)), "hi90": sig_list(np.where(pre, hi, x))})
    return {"regions": out}


def hexes(cfg, c, cm, out_dir, last):
    res_list = cfg["web"]["hex_res"]
    native = int(cfg["grid"]["h3_res"])
    cells = cm["h3_cell"].unique()
    files = 0
    for r in res_list:
        key = cm["h3_cell"] if r == native else cm["h3_cell"].map(dict(zip(cells, (h3.cell_to_parent(x, r) for x in cells))))
        g = cm.assign(cell=key).groupby(["cell", "year", "month"], as_index=False)["n_harm"].sum()
        for y, gy in g.groupby("year"):
            if y > last.year:
                continue
            months = [f"{y}-{m:02d}" for m in range(1, 13)]
            w = gy.pivot(index="cell", columns="month", values="n_harm").reindex(columns=range(1, 13)).fillna(0.0)
            w = w[(w > 0).any(axis=1)].sort_index()
            vals = w.to_numpy()
            valid = [y < last.year or m <= last.month for m in range(1, 13)]
            obj = {"months": months,
                   "cells": {cell: [sig(v) if ok else None for v, ok in zip(row, valid)]
                             for cell, row in zip(w.index, vals)}}
            dump(out_dir / c / f"r{r}" / f"{y}.json", obj)
            files += 1
    return files


def anomalies(cfg, val, cells_by_country):
    k = cfg["web"]["coord_decimals_meta"]
    known = {(e.get("adm1"), e["year"], e["month"]): e["name"] for e in cfg["validation"].get("known_events", [])}
    rows = []
    for c, ev in val["events"].items():
        items = list(ev["top"])
        for kn in ev.get("known_events", []):
            if not any(i["adm1_id"] == kn["adm1_id"] and i["year"] == kn["year"] and i["month"] == kn["month"]
                       for i in items):
                items.append({**kn, "adm1_name": None})
        cm = cells_by_country.get(c)
        import h3
        for i in items:
            name = i.get("adm1_name") or cm.loc[cm["adm1_id"] == i["adm1_id"], "adm1_name"].iloc[0]
            if i.get("lat") is None or (isinstance(i.get("lat"), float) and not math.isfinite(i["lat"])):
                i["lat"], i["lon"] = h3.cell_to_latlng(i["hex"])                       # hexagon centre
            ym = f"{i['year']}-{i['month']:02d}"
            title = known.get((i["adm1_id"], i["year"], i["month"])) or \
                f"{name}: {pd.Timestamp(year=i['year'], month=i['month'], day=1):%B %Y} fires"
            # anomaly vs the hexagon's normal for that month; normal floored (a quiet place would give 38,000%)
            rows.append({"country": c, "region": name, "ym": ym, "value": sig(i["n_harm"]),
                         "anomaly_pct": sig(100 * (i["n_harm"] - i["expected"]) / max(i["expected"], cfg["web"]["anomaly_normal_floor"])),
                         "lat": round(float(i["lat"]), k), "lon": round(float(i["lon"]), k), "title": title})
    return sorted(rows, key=lambda r: (r["country"], -(r["anomaly_pct"] or 0)))


def boundaries(cfg, out_dir):
    w = cfg["web"]
    n = 0
    for p in sorted((ROOT / cfg["regions"]["boundaries_dir"]).glob("*_ADM1.geojson")):
        g = gpd.read_file(p)[["shapeName", "shapeISO", "geometry"]]
        g["geometry"] = g.geometry.simplify(w["simplify_deg"], preserve_topology=True)
        js = json.loads(g.to_json(drop_id=True))
        k = w["coord_decimals_geom"]

        def rnd(c):
            return [rnd(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], k), round(c[1], k)]
        for f in js["features"]:
            f["geometry"]["coordinates"] = rnd(f["geometry"]["coordinates"])
        dump(out_dir / f"{p.stem.split('_')[0]}_adm1.geojson", js)
        n += 1
    return n


def sizes(root, warn_mb):
    rep = {}
    for d in sorted([root] + [p for p in root.rglob("*") if p.is_dir()]):
        if d.parent == root or d == root:
            files = [f for f in d.rglob("*") if f.is_file()] if d != root else [f for f in d.iterdir() if f.is_file()]
            rep[str(d.relative_to(root.parent)).replace("\\", "/")] = sum(f.stat().st_size for f in files)
    big = [(str(f.relative_to(root)), f.stat().st_size) for f in root.rglob("*") if f.is_file()
           and f.stat().st_size > warn_mb * 1e6]
    return rep, big


# ---------------------------------------------------------------- main

def main():
    cfg = load_config()
    w = cfg["web"]
    man = ingest.load_manifest(cfg)
    out = ROOT / w["out_dir"]
    out.mkdir(parents=True, exist_ok=True)
    for x in out.iterdir():          # empty it (removing the folder itself fails if a shell / OneDrive holds it)
        shutil.rmtree(x) if x.is_dir() else x.unlink()
    card = CAL.read_model_card()
    iv = card["intervals"]
    coefs = PKG.kz_coefs()
    val = json.loads((REPORTS / "validation.json").read_text(encoding="utf-8"))
    countries = [c for c in ingest.countries(cfg, man) if c not in val.get("pending_countries", [])]
    last = last_complete_month(cfg, countries)
    periods, yms = ym_range(w["first_ym"], str(last))
    log.info("export %s .. %s for %s", yms[0], yms[-1], countries)

    meta = {"countries": [country_info(cfg, c) for c in countries], "first_ym": yms[0], "last_ym": yms[-1],
            "model": {"name": f"{card['selected']} — {card['label']}", "id": card["production_model"],
                      "trained_on": card["train_country"],
                      "calibration": f"{cfg['calibration']['period'][0]}–{cfg['calibration']['period'][1]}",
                      "holdout": f"{cfg['calibration']['holdout_start']}–{last.year}",
                      "interval": f"{int(100 * iv['level'])}% conformal, sized at country / region level"},
            "pending_countries": val.get("pending_countries", []),
            "generated_at": dt.datetime.now().isoformat(timespec="seconds")}
    dump(out / "meta.json", meta)
    for c in countries:
        dump(out / "series" / f"{c}.json", series(cfg, c, coefs, iv, periods, yms))
    cells = {}
    for c in ingest.countries(cfg, man, "cell"):
        cm = harmonized_cells(cfg, c, coefs)
        cm = cm[(cm["year"] * 100 + cm["month"]).between(periods[0].year * 100 + periods[0].month,
                                                         last.year * 100 + last.month)]
        cells[c] = cm
        dump(out / "regions" / f"{c}.json", regions(cfg, cm, iv, periods, yms))
        if c in w["hex_countries"]:
            n = hexes(cfg, c, cm, out / "hex", last)
            log.info("%s: %d hex files", c, n)
    dump(out / "anomalies.json", anomalies(cfg, val, cells))
    shutil.copyfile(REPORTS / "validation.json", out / "validation.json")
    nb = boundaries(cfg, out / "boundaries")
    rep, big = sizes(out, w["warn_file_mb"])
    print("size per folder:")
    for k, v in rep.items():
        print(f"  {k:<32} {v / 1e6:8.2f} MB")
    for f, s in big:
        print(f"WARNING: {f} is {s / 1e6:.1f} MB (> {w['warn_file_mb']} MB)")
    log.info("boundaries: %d files; files > %s MB: %d", nb, w["warn_file_mb"], len(big))
    return rep, big


if __name__ == "__main__":
    main()

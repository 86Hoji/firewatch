"""Phase D: static-website data export -> web/public/data/ (config `web`).

  meta.json                     countries [{code, name, bbox, center}], first_ym, last_ym, model, generated_at
  series/{CC}.json              monthly country series, all countries
  regions/{CC}.json             monthly ADM1 series, cell-level countries
  hex/{CC}/r5|r7/{YYYY}.json    harmonized cell-days per H3 cell and month (config web.hex_countries)
  anomalies.json                top events (07b_validation_package) incl. the known events
  validation.json               copy of reports/validation.json
  boundaries/{CC}_adm1.geojson  simplified ADM1 polygons (shapeName, shapeISO)

Harmonized = the production model form (selected in experiments, reports/model_card.json): MODIS -> S-NPP equivalent
before 2012, S-NPP (+ NOAA-20 on satellite-wide S-NPP outage days) from 2012. Coefficients: Kazakhstan = production
coefficients (06_harmonize); every other country = the same model REFITTED on its own 2012-2019 overlap, because C4
showed the KZ coefficients do not transfer (validation.json keeps the KZ-as-is numbers for the transfer table).
lo90/hi90: country series = each country's own leave-one-year-out interval (KZ: the C3 country interval); regions =
the C3 region interval (from KZ leave-one-region-out). From 2012 the value is observed, so lo90 = hi90.
Also writes docs/EVENTS.md: top events per country (07b metric, same coefficients as the site).
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
JAN_2012_NOTE = ("January 2012 is incomplete: the S-NPP archive starts on 2012-01-20, so that month has about a third "
                 "of its observations")
EVENTS_DOC = {"countries": ["KAZ", "UZB"], "top_n": 5}     # docs/EVENTS.md (demo-event shortlist)
# heat sources found in this project that are NOT fires (docs/PHASE_C.md, C2); flagged in docs/EVENTS.md
NOT_FIRE = [{"lat": 38.1, "lon": 67.3, "radius_deg": 0.25, "from_year": 2025,
             "note": "NOT A FIRE: new industrial heat source found in C2 (FIRMS labels it vegetation)"}]


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


def country_coefs(cfg, c, kz, iv, model):
    """(coefficients, country-interval params) used on the site for country c.
    KZ: production coefficients + C3 country interval. Others: terra, NOAA-20 and main model refitted on c's own data
    (same model form and periods as production), interval from c's own leave-one-year-out errors."""
    if c == cfg["train_country"]:
        return kz, iv["country"], "production (fitted on Kazakhstan)"
    cm = PKG.country_months(c, cfg)
    ov = tuple(cfg["package"]["overlap"])
    loyo = PKG.local_loyo(cm, cfg, model, ov)
    ivc = intervals.fit_hetero(loyo["actual"], loyo["pred"], iv["level"], cfg["intervals"]["zero_min_n"])
    return PKG.own_coefs(cm, cfg, model), ivc, f"refitted on own {ov[0]}–{ov[1]} overlap"


def series(cfg, c, coefs, ivc, periods, yms):
    cut = cfg["calibration"]["period"][0]
    cm = PKG.country_months(c, cfg)
    h = calib.harmonize(cm.assign(h3_cell="country"), coefs, cfg)
    cm = cm.assign(n_harm=h["n_harm"].to_numpy())
    d = full_months(cm, periods, ["p_modis", "p_viirs_snpp", "n_modis", "n_viirs_snpp", "v_target", "n_harm"])
    pre = (d["year"] < cut).to_numpy()
    harm = np.where(pre, d["n_harm"], d["v_target"])
    lo, hi = intervals.bounds(harm, ivc)
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


def anomalies(cfg, events, cells_by_country):
    k = cfg["web"]["coord_decimals_meta"]
    known = {(e.get("adm1"), e["year"], e["month"]): e["name"] for e in cfg["validation"].get("known_events", [])}
    rows = []
    for c, ev in events.items():
        items = [i for i in ev["top"] if not _note(i, [], {}).startswith("**NOT A FIRE")][:cfg["package"]["events"]["top_n"]]
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


def _note(e, rows, known):
    for x in NOT_FIRE:
        if e["year"] >= x["from_year"] and abs(e["lat"] - x["lat"]) <= x["radius_deg"] \
                and abs(e["lon"] - x["lon"]) <= x["radius_deg"]:
            return f"**{x['note']}**"
    k = known.get((e["adm1_id"], e["year"], e["month"]))
    if k:
        return k
    same = sorted({int(r["year"]) for r in rows if r["hex"] == e["hex"] and r["year"] != e["year"]})
    return f"same hexagon also in {', '.join(map(str, same))} (recurring burn?)" if same else ""


def _event_rows(rows, n, cut, known):
    L = ["| # | place (ADM1) | month | lat, lon | cell-days | normal | excess | overall rank | data | note |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for i, e in enumerate(rows[:n], 1):
        m = pd.Timestamp(year=int(e["year"]), month=int(e["month"]), day=1)
        L.append(f"| {i} | {e['adm1_name']} | {m:%B %Y} | {e['lat']:.2f}, {e['lon']:.2f} | {e['n_harm']:.0f} | "
                 f"{e['expected']:.0f} | {e['excess']:.0f} | {e['rank']} | "
                 f"{'S-NPP observed' if e['year'] >= cut else 'MODIS → S-NPP (model)'} | {_note(e, rows[:n], known)} |")
    return L


def events_md(cfg, events, countries, n):
    """docs/EVENTS.md: top-n events per country for choosing the demo event."""
    cut = cfg["calibration"]["period"][0]
    ev_cfg = cfg["package"]["events"]
    known = {(e.get("adm1"), e["year"], e["month"]): e["name"] for e in cfg["validation"].get("known_events", [])}
    L = ["# Fire events — candidates for the demo", "",
         f"Metric (pipeline/07b_validation_package.py `events`): harmonized cell-days in an H3 res-{ev_cfg['h3_res']} "
         "hexagon (~40 km across) in one month, minus that hexagon's normal for the same calendar month (median "
         f"{ev_cfg['years'][0]}–{ev_cfg['years'][1]}); ranked by the excess; one event per region and year. Same "
         "coefficients as the website (Kazakhstan: production; other countries: refitted on their own 2012–2019 overlap).",
         "", "*Place* = ADM1 region (geoBoundaries, pre-2022: Abai oblast is inside East Kazakhstan, Jetisu inside "
         "Almaty Region, Ulytau inside Karaganda). lat/lon = fire-weighted centre of the hexagon that month. "
         f"*Data*: before {cut} = MODIS converted to S-NPP equivalent (modelled); from {cut} = S-NPP observed — "
         "observed events are easier to defend in front of judges.", ""]
    for c in countries:
        ev = events[c]
        name = cfg["web"]["countries"][c]["name"]
        allev = pd.DataFrame(ev["all"])
        names = dict(zip(allev["adm1_id"], allev["adm1_name"]))
        obs = allev[allev["year"] >= cut].drop_duplicates(["adm1_id", "year"]).to_dict(orient="records")
        L += [f"## {name}", "", f"### Top {n}, all years", ""] + _event_rows(ev["top"], n, cut, known)
        L += ["", f"### Top {n} since {cut} (observed S-NPP only — same metric and normal, filtered)", ""] \
            + _event_rows(obs, n, cut, known)
        if ev.get("known_events"):
            L += ["", f"### Known events in {name} (rank among all {ev['candidates']} region-month events)", "",
                  "| event | place (ADM1) | month | cell-days | normal | excess | rank |", "|---|---|---|---|---|---|---|"]
            for kn in ev["known_events"]:
                m = pd.Timestamp(year=kn["year"], month=kn["month"], day=1)
                L.append(f"| {kn['name']} | {names.get(kn['adm1_id'], kn['adm1_id'])} | {m:%B %Y} | {kn['n_harm']:.0f} | {kn['expected']:.0f} | "
                         f"{kn['excess']:.0f} | {kn['rank'] if kn['rank'] else '–'} |")
        L.append("")
    L += ["Rank 1 is the largest local excess of fire *counts*. Big wildfires in forest (Abai 2023) rank lower than "
          "large steppe/farm burns because the metric counts detections, not intensity or damage. Check any candidate "
          "against news or burned-area imagery before the demo."]
    (ROOT / "docs" / "EVENTS.md").write_text("\n".join(L) + "\n", encoding="utf-8")


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
    kz = PKG.kz_coefs()
    val = json.loads((REPORTS / "validation.json").read_text(encoding="utf-8"))
    countries = [c for c in ingest.countries(cfg, man) if c not in val.get("pending_countries", [])]
    last = last_complete_month(cfg, countries)
    periods, yms = ym_range(w["first_ym"], str(last))
    log.info("export %s .. %s for %s", yms[0], yms[-1], countries)

    meta = {"countries": [country_info(cfg, c) for c in countries], "first_ym": yms[0], "last_ym": yms[-1],
            "model": {"name": f"{card['selected']} — {card['label']}", "id": card["production_model"],
                      "trained_on": card["train_country"],
                      "calibration": f"{cfg['calibration']['period'][0]}–{cfg['calibration']['period'][1]}",
                      "holdout": f"{cfg['package']['holdout'][0]}–{cfg['package']['holdout'][1]}",
                      "interval": f"{int(100 * iv['level'])}% conformal, sized at country / region level",
                      "coefficients": {}},
            "pending_countries": val.get("pending_countries", []),
            "notes": [JAN_2012_NOTE],
            "generated_at": dt.datetime.now().isoformat(timespec="seconds")}
    coefs, ivc = {}, {}
    for c in countries:
        coefs[c], ivc[c], meta["model"]["coefficients"][c] = country_coefs(cfg, c, kz, iv, card["production_model"])
        log.info("%s coefficients: %s", c, meta["model"]["coefficients"][c])
    dump(out / "meta.json", meta)
    for c in countries:
        dump(out / "series" / f"{c}.json", series(cfg, c, coefs[c], ivc[c], periods, yms))
    cells, events = {}, {}
    ecfg = {**cfg, "package": {**cfg["package"], "events": {**cfg["package"]["events"], "top_n": EVENTS_DOC["top_n"]}}}
    for c in ingest.countries(cfg, man, "cell"):
        events.update(PKG.events(ecfg, coefs[c], [c], return_all=True))
        cm = harmonized_cells(cfg, c, coefs[c])
        cm = cm[(cm["year"] * 100 + cm["month"]).between(periods[0].year * 100 + periods[0].month,
                                                         last.year * 100 + last.month)]
        cells[c] = cm
        dump(out / "regions" / f"{c}.json", regions(cfg, cm, iv, periods, yms))
        if c in w["hex_countries"]:
            n = hexes(cfg, c, cm, out / "hex", last)
            log.info("%s: %d hex files", c, n)
    dump(out / "anomalies.json", anomalies(cfg, events, cells))
    events_md(cfg, events, EVENTS_DOC["countries"], EVENTS_DOC["top_n"])
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

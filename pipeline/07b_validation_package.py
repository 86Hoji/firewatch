"""C4 validation package -> reports/validation.json + reports/VALIDATION.md.

Everything uses the PRODUCTION model exactly as harmonization does: the coefficients fitted on Kazakhstan
(data/aggregated/coefficients.parquet, model named in reports/model_card.json) and calib.predict / calib.harmonize.
No land-cover strata exist, so a country's monthly totals are predicted directly (the multiplier is set by that
country's own monthly MODIS total, as for any region in production).

Target ("actual") for every country = its S-NPP cell-days + its own NOAA-20 fill on satellite-wide outage days
(NOAA-20 -> S-NPP ratio fitted on that country, config calibration.noaa20_period from noaa20_start).

Tests
  1 UZ independent test   KZ model applied to UZ: 2012 step ratios naive vs harmonized; overlap 2012-2019; holdout
  2 TM stress test        same as UZ, plus how much of TM's signal is static sources (flares)
  3 KG/TJ annual totals   tiny countries: annual sums only
  4 transfer table        every country: KZ model as-is vs a local refit (leave-one-year-out), overlap + holdout
  5 burned area           monthly burned area vs cell-days; is the relation continuous across 2012?
  6 events                region-month anomalies (robust z of log counts vs the same region and calendar month)
"""
import importlib
import json

import numpy as np
import pandas as pd
from scipy import stats

from pipeline import calib, ingest, intervals
from pipeline.common import AGG, REPORTS, ROOT, get_logger, load_config, write_json
from pipeline.metrics import series_metrics, step_test

CAL = importlib.import_module("pipeline.05_calibrate")
log = get_logger("package")


# ---------------------------------------------------------------- data

def kz_coefs():
    return calib.coefs_from_table(pd.read_parquet(AGG / "coefficients.parquet"))


def country_months(c, cfg):
    """Monthly totals of one country with v_target (its own NOAA-20 fill)."""
    cm = pd.read_parquet(AGG / "country_month" / f"{c}.parquet").sort_values(["year", "month"]).reset_index(drop=True)
    cm = cm.drop(columns=[x for x in ("country",) if x in cm])
    n20, _ = calib.fit_noaa20(cm, cfg)
    cm["v_target"] = cm["n_viirs_snpp"] + calib.predict(cm, "n_viirs_noaa20_gap", n20)["pred"]
    return cm


def own_coefs(cm, cfg, model):
    """The production model form with ALL coefficients refitted on one country (what the website uses outside KZ):
    Terra->Terra+Aqua, NOAA-20->S-NPP and the main MODIS->VIIRS model on the country's own overlap."""
    k = cfg["calibration"]
    terra, _ = calib.fit(cm, "n_modis", "n_modis_terra", tuple(k["terra_aqua_period"]), cfg, intervals=False)
    n20, _ = calib.fit_noaa20(cm, cfg)
    main, _ = calib.fit_point(cm, "v_target", "n_modis", tuple(cfg["package"]["overlap"]), cfg, model, n_boot=0)
    return {"main": main, "terra": terra, "noaa20": n20}


def last_full_year(cm):
    return CAL.last_full_year(cm)


def between(cm, yrs):
    return cm[cm["year"].between(*yrs)]


# ---------------------------------------------------------------- building blocks

def as_is(cm, coefs, iv):
    """KZ model applied to this country's MODIS: pred + C3 country interval."""
    p = calib.predict(cm, "n_modis", coefs["main"])["pred"].to_numpy()
    lo, hi = intervals.bounds(p, iv["country"])
    return pd.DataFrame({"year": cm["year"], "month": cm["month"], "actual": cm["v_target"], "pred": p,
                         "low": lo, "high": hi, "n_modis": cm["n_modis"]})


def local_loyo(cm, cfg, model, yrs):
    """Local refit, honest: each year predicted by a model fitted on the country's OTHER overlap years."""
    out = []
    for y in range(yrs[0], yrs[1] + 1):
        coef, _ = calib.fit_point(cm[cm["year"] != y], "v_target", "n_modis", tuple(yrs), cfg, model, n_boot=0)
        t = cm[cm["year"] == y]
        out.append(pd.DataFrame({"year": t["year"], "month": t["month"], "actual": t["v_target"],
                                 "pred": calib.predict(t, "n_modis", coef)["pred"].to_numpy()}))
    return pd.concat(out, ignore_index=True)


def local_holdout(cm, cfg, model, fit_yrs, test_yrs):
    coef, _ = calib.fit_point(cm, "v_target", "n_modis", tuple(fit_yrs), cfg, model, n_boot=0)
    t = between(cm, test_yrs)
    return pd.DataFrame({"year": t["year"], "month": t["month"], "actual": t["v_target"],
                         "pred": calib.predict(t, "n_modis", coef)["pred"].to_numpy()})


def m(df, with_iv=True):
    if df.empty:
        return None
    r = series_metrics(df["actual"], df["pred"], df["low"] if with_iv and "low" in df else None,
                       df["high"] if with_iv and "high" in df else None)
    return {k: r[k] for k in ("n_months", "mae_pct_of_mean", "bias_total_pct", "pearson_r", "coverage") if k in r}


def local_coefs(cm, coefs, cfg, model):
    """KZ coefficient set with the main MODIS->VIIRS model refitted on this country's overlap years."""
    main, _ = calib.fit_point(cm, "v_target", "n_modis", tuple(cfg["package"]["overlap"]), cfg, model, n_boot=0)
    return {**coefs, "main": main}


def steps(cm, coefs, cfg, y1, model=None):
    """2012 jump of naive vs harmonized series (same definitions as the KZ report, 07_validate).
    model given -> also the series harmonized with a LOCAL refit (does the method work with local coefficients?)."""
    v, cut = cfg["validation"], cfg["calibration"]["period"][0]
    h = calib.harmonize(cm.assign(h3_cell="country"), coefs, cfg)
    d = cm[["year", "month", "n_modis", "n_viirs_snpp", "v_target"]].assign(n_harm=h["n_harm"].to_numpy())
    if model:
        hl = calib.harmonize(cm.assign(h3_cell="country"), local_coefs(cm, coefs, cfg, model), cfg)
        d["n_harm_local"] = hl["n_harm"].to_numpy()
    d = d[d["year"].between(2001, y1)]
    pre = d["year"] < cut
    series = {"naive": np.where(pre, d["n_modis"], d["n_viirs_snpp"]), "harmonized": d["n_harm"].to_numpy(),
              "modis_only": d["n_modis"].to_numpy()}
    if model:
        series["harmonized_local"] = d["n_harm_local"].to_numpy()
    out = {}
    a, b = v["pre_jump"], v["post_jump"]
    ms = cfg["package"]["step_monthly"]
    win = d["year"].between(*ms).to_numpy()
    for k, x in series.items():
        s = pd.Series(x, index=d.index).groupby(d["year"]).sum()
        out[k] = {"step_ratio": float(s.loc[b[0]:b[1]].mean() / s.loc[a[0]:a[1]].mean()),
                  "monthly_step": step_test(d["year"][win], d["month"][win], x[win], cut)}
    for k in out:
        out[k]["excess_vs_modis"] = out[k]["step_ratio"] / out["modis_only"]["step_ratio"]
    return out, d


def country_test(c, coefs, cfg, iv, model):
    pk = cfg["package"]
    cm = country_months(c, cfg)
    y1 = min(last_full_year(cm), pk["holdout"][1])
    ai = as_is(cm, coefs, iv)
    st, series = steps(cm, coefs, cfg, y1, model)
    ho = (pk["holdout"][0], y1)
    res = {"steps": st,
           "overlap_as_is": m(between(ai, pk["overlap"])),
           "holdout_as_is": m(between(ai, ho)),
           "holdout_as_is_to_2024": m(between(ai, (ho[0], min(y1, 2024)))),
           "overlap_local_loyo": m(local_loyo(cm, cfg, model, pk["overlap"]), False),
           "holdout_local": m(local_holdout(cm, cfg, model, pk["overlap"], ho), False),
           "ratio_observed": float(between(cm, pk["overlap"])["v_target"].sum() /
                                   between(cm, pk["overlap"])["n_modis"].sum()),
           "ratio_kz_model": float(between(ai, pk["overlap"])["pred"].sum() / between(ai, pk["overlap"])["n_modis"].sum()),
           "holdout_years": list(ho)}
    return res, cm, ai, series


# ---------------------------------------------------------------- tests

def _annual(df):
    a = df.groupby("year")[["actual", "pred"]].sum()
    r = series_metrics(a["actual"], a["pred"])
    return {"years": [int(a.index.min()), int(a.index.max())], "mae_pct_of_mean": r["mae_pct_of_mean"],
            "bias_total_pct": r["bias_total_pct"]}


def annual_test(c, coefs, cfg, iv, model):
    """KZ coefficients as-is (headline, unchanged) + 'local': the country's own refit, as on the website —
    leave-one-year-out inside the overlap and fit-on-overlap -> holdout, both scored on annual totals."""
    pk = cfg["package"]
    cm = country_months(c, cfg)
    y1 = min(last_full_year(cm), pk["holdout"][1])
    ai = between(as_is(cm, coefs, iv), (pk["overlap"][0], y1))
    a = ai.groupby("year")[["actual", "pred", "n_modis"]].sum()
    r = series_metrics(a["actual"], a["pred"])
    local = {"loyo": _annual(local_loyo(cm, cfg, model, pk["overlap"])),
             "holdout": _annual(local_holdout(cm, cfg, model, pk["overlap"], (pk["holdout"][0], y1)))}
    return {"years": [int(a.index.min()), int(a.index.max())], "local": local,
            "mae_pct_of_mean": r["mae_pct_of_mean"], "bias_total_pct": r["bias_total_pct"],
            "pearson_r": r["pearson_r"], "naive_modis_bias_pct": float(100 * (a["n_modis"].sum() / a["actual"].sum() - 1)),
            "mean_annual_cell_days": float(a["actual"].mean()),
            "annual": [{"year": int(y), "actual": float(r_.actual), "harmonized": float(r_.pred), "modis": float(r_.n_modis)}
                       for y, r_ in a.iterrows()]}


def flare_load(cfg, countries):
    summ = json.loads((REPORTS / "cleaning_summary.json").read_text(encoding="utf-8"))["countries"]
    mask = json.loads((REPORTS / "static_mask_check.json").read_text(encoding="utf-8"))["countries"] \
        if (REPORTS / "static_mask_check.json").exists() else {}
    out = {}
    for c in countries:
        st = {s["step"]: s for s in summ[c]["steps"]}
        t = st["type_not_vegetation"]
        out[c] = {"static_share_removed_pct": 100 * t["removed"] / t["rows_in"],
                  "mask_test": mask.get(c, {}).get("detection", {}).get("mask")}
    return out


def ready_countries(cfg, man):
    """Countries included in the current satellite-wide outage list (a provisional list may lack some)."""
    rep = json.loads((REPORTS / "outage_days.json").read_text(encoding="utf-8"))
    return [c for c in ingest.countries(cfg, man) if c in rep["countries"]]


def transfer_table(cfg, coefs, iv, model, man):
    pk, tr = cfg["package"], cfg["package"]["transfers_if"]
    rows = {}
    for c in ready_countries(cfg, man):
        cm = country_months(c, cfg)
        y1 = min(last_full_year(cm), pk["holdout"][1])
        ai = as_is(cm, coefs, iv)
        if c == cfg["train_country"]:       # as-is on KZ itself would be in-sample: use its own LOYO
            ov_as_is = m(local_loyo(cm, cfg, model, pk["overlap"]), False)
        else:
            ov_as_is = m(between(ai, pk["overlap"]))
        ov_loc = m(local_loyo(cm, cfg, model, pk["overlap"]), False)
        ho = (pk["holdout"][0], y1)
        r = {"role": man.loc[man["country"] == c, "role"].iloc[0], "overlap_as_is": ov_as_is, "overlap_local": ov_loc,
             "holdout_as_is": m(between(ai, ho)), "holdout_local": m(local_holdout(cm, cfg, model, pk["overlap"], ho), False),
             "ratio_observed": float(between(cm, pk["overlap"])["v_target"].sum() / between(cm, pk["overlap"])["n_modis"].sum()),
             "ratio_kz_model": float(between(ai, pk["overlap"])["pred"].sum() / between(ai, pk["overlap"])["n_modis"].sum()),
             "mean_monthly_modis": float(between(cm, pk["overlap"])["n_modis"].mean())}
        r["mae_ratio_as_is_vs_local"] = ov_as_is["mae_pct_of_mean"] / ov_loc["mae_pct_of_mean"]
        r["transfers"] = bool(r["mae_ratio_as_is_vs_local"] <= tr["max_mae_ratio"]
                              and abs(ov_as_is["bias_total_pct"]) <= tr["max_abs_bias_pct"])
        rows[c] = r
        log.info("transfer %s: as-is %.1f%% (bias %+.1f%%) vs local %.1f%% -> %s", c, ov_as_is["mae_pct_of_mean"],
                 ov_as_is["bias_total_pct"], ov_loc["mae_pct_of_mean"], r["transfers"])
    return rows


def burned_area(cfg, harm_series):
    ba_cfg = cfg["package"]["burned_area"]
    ba = pd.read_csv(ROOT / ba_cfg["file"], sep=ba_cfg["sep"], encoding="utf-8-sig")
    ba["country"] = ba["region"].map(ba_cfg["names"])
    ba["year"], ba["month"] = ba["ym"].str[:4].astype(int), ba["ym"].str[5:7].astype(int)
    cut = cfg["calibration"]["period"][0]
    out = {}
    for c, g in ba.dropna(subset=["country"]).groupby("country"):
        if c not in harm_series:
            continue
        d = harm_series[c].merge(g[["year", "month", "burned_ha"]], on=["year", "month"], how="inner")
        d = d[d["year"].between(*ba_cfg["years"])].sort_values(["year", "month"])
        pre = d["year"] < cut
        naive = np.where(pre, d["n_modis"], d["n_viirs_snpp"])
        r = {"months": int(len(d))}
        for name, x in (("naive", naive), ("harmonized", d["n_harm"].to_numpy()),
                        ("harmonized_local", d["n_harm_local"].to_numpy()), ("modis_only", d["n_modis"].to_numpy())):
            lx, lb = np.log1p(x), np.log1p(d["burned_ha"].to_numpy())
            r[name] = {"r_log_all": float(stats.pearsonr(lb, lx)[0]),
                       "r_log_pre2012": float(stats.pearsonr(lb[pre], lx[pre])[0]),
                       "r_log_post2012": float(stats.pearsonr(lb[~pre], lx[~pre])[0]),
                       "step_given_burned_area": step_test(d["year"], d["month"], x, cut,
                                                           covariate=d["burned_ha"].to_numpy())}
        # MODIS alone has no sensor change at 2012: its step is the fire-regime change; the seam is the excess over it
        r["excess_vs_modis"] = float(r["harmonized_local"]["step_given_burned_area"]["step_factor"]
                                     / r["modis_only"]["step_given_burned_area"]["step_factor"])
        out[c] = r
    return out


def events(cfg, coefs, countries, return_all=False):
    """Events = far more fire than usual for that PLACE and calendar month.

    Unit: H3 res-4 hexagon (~1,770 km2, ~40 km across: the size of a large fire) and month. Normal = median of the
    same hexagon and calendar month over the event years; excess = harmonized cell-days - normal; ranked by excess.
    One entry per region-month (best hexagon), top list one per region-year. Why not region-month z-scores: tried
    first, it ranked early-season farm burning in months whose normal is 0 (z blows up) and cannot see wildfires,
    which are small next to the region's farm burning (see docs/DECISIONS.md)."""
    import h3
    e = cfg["package"]["events"]
    train, r = cfg["train_country"], int(e["h3_res"])
    res = {}
    for c in countries:
        cm = pd.read_parquet(AGG / "cell_month.parquet") if c == train else \
            calib.harmonize(CAL.load_cell_month(c, cfg), coefs, cfg)
        cm = cm[(cm["adm1_id"] != "outside") & cm["year"].between(*e["years"])]
        cells = cm["h3_cell"].unique()
        cm = cm.assign(hex=cm["h3_cell"].map(dict(zip(cells, (h3.cell_to_parent(x, r) for x in cells)))))
        # region of a hexagon = region with most of its fire
        reg = (cm.groupby(["hex", "adm1_id", "adm1_name"])["n_harm"].sum().reset_index()
               .sort_values(["hex", "n_harm", "adm1_id"], ascending=[True, False, True]).drop_duplicates("hex"))
        g = cm.groupby(["hex", "year", "month"], as_index=False)["n_harm"].sum()
        yrs = np.arange(e["years"][0], e["years"][1] + 1)
        grid = pd.DataFrame({"hex": g["hex"].unique()}).merge(
            pd.DataFrame({"year": np.repeat(yrs, 12), "month": np.tile(np.arange(1, 13), len(yrs))}), how="cross")
        g = grid.merge(g, on=["hex", "year", "month"], how="left").fillna({"n_harm": 0.0})
        g["expected"] = g.groupby(["hex", "month"])["n_harm"].transform("median")
        g["excess"] = g["n_harm"] - g["expected"]
        g = g.merge(reg[["hex", "adm1_id", "adm1_name"]], on="hex")
        lat_lon = cm.assign(w_lat=cm["lat"] * cm["n_harm"], w_lon=cm["lon"] * cm["n_harm"]) \
            .groupby(["hex", "year", "month"])[["w_lat", "w_lon", "n_harm"]].sum()
        cand = g[g["excess"] >= e["min_excess_cell_days"]].sort_values(["excess", "hex"], ascending=[False, True])
        cand = cand.drop_duplicates(["adm1_id", "year", "month"]).reset_index(drop=True)
        cand["rank"] = np.arange(1, len(cand) + 1)
        ll = lat_lon.reindex(pd.MultiIndex.from_frame(cand[["hex", "year", "month"]]))
        cand["lat"] = (ll["w_lat"] / ll["n_harm"]).to_numpy()
        cand["lon"] = (ll["w_lon"] / ll["n_harm"]).to_numpy()
        cols = ["rank", "adm1_id", "adm1_name", "hex", "year", "month", "n_harm", "expected", "excess", "lat", "lon"]
        top = cand.drop_duplicates(["adm1_id", "year"]).head(e["top_n"])
        out = {"unit": f"H3 res-{r} hexagon-month", "top": top[cols].to_dict(orient="records"),
               "candidates": int(len(cand))}
        if return_all:                      # every region-month event, ranked (docs/EVENTS.md filters it)
            out["all"] = cand[cols].to_dict(orient="records")
        checks = []
        for k in cfg["validation"].get("known_events", []):
            if c != train or "adm1" not in k:
                continue
            hit = cand[(cand["adm1_id"] == k["adm1"]) & (cand["year"] == k["year"]) & (cand["month"] == k["month"])]
            row = g[(g["adm1_id"] == k["adm1"]) & (g["year"] == k["year"]) & (g["month"] == k["month"])] \
                .sort_values("excess", ascending=False).iloc[0]
            checks.append({"name": k["name"], "adm1_id": k["adm1"], "year": k["year"], "month": k["month"],
                           "hex": row["hex"], "n_harm": float(row["n_harm"]), "expected": float(row["expected"]),
                           "excess": float(row["excess"]), "rank": int(hit["rank"].iloc[0]) if len(hit) else None,
                           "of": int(len(cand))})
        out["known_events"] = checks
        res[c] = out
    return res


# ---------------------------------------------------------------- report

def f(x, d=1, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    return f"{x:+.{d}f}" if sign else f"{x:.{d}f}"


def pct(x):
    return "–" if x is None else f"{100 * x:.0f}%"


def write_md(R, cfg):
    pk = cfg["package"]
    L = ["# FIREWATCH — validation package (C4)", "",
         f"Model: **{R['model']['selected']} — {R['model']['label']}** (`{R['model']['production_model']}`), fitted on "
         f"Kazakhstan {pk['overlap'][0]}–{pk['overlap'][1]} and applied unchanged everywhere below unless a row says "
         "\"local\". Error = mean absolute error as % of the mean month (MAE %); bias = total predicted vs actual. "
         "Actual = S-NPP cell-days (+ NOAA-20 on satellite-wide S-NPP outage days). Machine-readable: "
         "[validation.json](validation.json). Kazakhstan technical report: [validation_kz.md](validation_kz.md).", "",
         "*January 2012 is incomplete:* the S-NPP archive starts on 2012-01-20, so that month has about a third of its "
         "observations (it is inside the 2012 step windows and the 2012–2019 overlap as recorded).", ""]
    if R["pending_countries"]:
        L += [f"> **Provisional:** {', '.join(R['pending_countries'])} still re-ingesting; their rows are missing and the "
              "S-NPP outage list was built without them.", ""]

    def country_block(title, c, r, extra=None):
        st = r["steps"]
        L.extend([f"## {title}", "",
                  "| series | step 2009–11 → 2012–14 | vs MODIS alone | monthly step (95% CI), 2003–2019 |",
                  "|---|---|---|---|"])
        for k, lab in (("naive", "naive splice (MODIS → S-NPP)"), ("harmonized", "harmonized (KZ model)"),
                       ("harmonized_local", "harmonized (local refit)"), ("modis_only", "MODIS alone (reference)")):
            if k not in st:
                continue
            ms = st[k]["monthly_step"]
            L.append(f"| {lab} | ×{f(st[k]['step_ratio'], 2)} | ×{f(st[k]['excess_vs_modis'], 2)} | "
                     f"×{f(ms['step_factor'], 2)} ({f(ms['ci_low'], 2)}–{f(ms['ci_high'], 2)}) |")
        ho = r["holdout_years"]
        L.extend(["", "| period | model | MAE % | bias % | R | 90% interval coverage |", "|---|---|---|---|---|---|"])
        for lab, k, mod in ((f"overlap {pk['overlap'][0]}–{pk['overlap'][1]}", "overlap_as_is", "KZ as-is"),
                            (f"overlap {pk['overlap'][0]}–{pk['overlap'][1]}", "overlap_local_loyo", "local refit (LOYO)"),
                            (f"holdout {ho[0]}–{ho[1]}", "holdout_as_is", "KZ as-is"),
                            (f"holdout {ho[0]}–{min(ho[1], 2024)}", "holdout_as_is_to_2024", "KZ as-is"),
                            (f"holdout {ho[0]}–{ho[1]}", "holdout_local", "local refit")):
            x = r[k]
            if x:
                L.append(f"| {lab} | {mod} | {f(x['mae_pct_of_mean'])} | {f(x['bias_total_pct'], 1, True)} | "
                         f"{f(x.get('pearson_r'), 3)} | {pct(x.get('coverage'))} |")
        L.extend(["", f"VIIRS/MODIS ratio {pk['overlap'][0]}–{pk['overlap'][1]}: observed ×{f(r['ratio_observed'], 2)}, "
                      f"KZ model gives ×{f(r['ratio_kz_model'], 2)}.", ""])
        if extra:
            L.extend(extra)

    u = R["uz_test"]
    country_block("1. Uzbekistan — independent test (model never saw UZ)", "UZB", u, [
        f"**Takeaway.** {TAKE['uz']}", ""])
    t = R["tm_stress"]
    fl = R["flare_load"]
    extra = ["| country | detections removed as static (type ≠ 0) | mask test: precision / recall |", "|---|---|---|"]
    for c, x in fl.items():
        mt = x["mask_test"] or {}
        extra.append(f"| {c} | {f(x['static_share_removed_pct'])}% | {pct(mt.get('precision'))} / {pct(mt.get('recall'))} |")
    extra += ["", f"**Takeaway.** {TAKE['tm']}", ""]
    country_block("2. Turkmenistan — stress test (gas flares)", "TKM", t, extra)

    L.extend(["## 3. Kyrgyzstan and Tajikistan — annual totals", "",
              "KZ coefficients as-is, and *local* = the country's own refit (what the website uses): leave-one-year-out "
              f"in {pk['overlap'][0]}–{pk['overlap'][1]} and fit on the overlap → holdout.", "",
              "| country | years | mean actual cell-days / year | MAE % (annual), KZ as-is | bias % | R | naive MODIS bias % "
              "| local LOYO MAE % / bias % | local holdout MAE % / bias % |",
              "|---|---|---|---|---|---|---|---|---|"])
    for c, x in R["annual"].items():
        lo, ho = x["local"]["loyo"], x["local"]["holdout"]
        L.append(f"| {c} | {x['years'][0]}–{x['years'][1]} | {f(x['mean_annual_cell_days'], 0)} | "
                 f"{f(x['mae_pct_of_mean'])} | {f(x['bias_total_pct'], 1, True)} | {f(x['pearson_r'], 3)} | "
                 f"{f(x['naive_modis_bias_pct'], 0, True)} | {f(lo['mae_pct_of_mean'])} / {f(lo['bias_total_pct'], 1, True)} "
                 f"| {f(ho['mae_pct_of_mean'])} / {f(ho['bias_total_pct'], 1, True)} ({ho['years'][0]}–{ho['years'][1]}) |")
    L.extend(["", f"**Takeaway.** {TAKE['annual']}", ""])

    L.extend(["## 4. Transfer table — does the Kazakh model work elsewhere?", "",
              f"Overlap {pk['overlap'][0]}–{pk['overlap'][1]}. *As-is* = KZ coefficients unchanged (for KZ itself: "
              "leave-one-year-out, so it is not in-sample). *Local* = the same model refitted on that country, each "
              "year predicted from the other years. \"Transfers\" = as-is error ≤ "
              f"{pk['transfers_if']['max_mae_ratio']}× local and |bias| ≤ {pk['transfers_if']['max_abs_bias_pct']}%.", "",
              "| country | role | VIIRS/MODIS observed | KZ model | as-is MAE % | as-is bias % | local MAE % | "
              "holdout as-is MAE % / bias % | holdout local MAE % | transfers? |",
              "|---|---|---|---|---|---|---|---|---|---|"])
    for c, x in sorted(R["transfer"].items(), key=lambda kv: kv[1]["ratio_observed"]):
        ha, hl = x["holdout_as_is"] or {}, x["holdout_local"] or {}
        L.append(f"| {c} | {x['role']} | ×{f(x['ratio_observed'], 2)} | ×{f(x['ratio_kz_model'], 2)} | "
                 f"{f(x['overlap_as_is']['mae_pct_of_mean'])} | {f(x['overlap_as_is']['bias_total_pct'], 1, True)} | "
                 f"{f(x['overlap_local']['mae_pct_of_mean'])} | {f(ha.get('mae_pct_of_mean'))} / "
                 f"{f(ha.get('bias_total_pct'), 1, True)} | {f(hl.get('mae_pct_of_mean'))} | "
                 f"{'yes' if x['transfers'] else '**no**'} |")
    L.extend(["", f"**Takeaway.** {TAKE['transfer']}", ""])

    L.extend(["## 5. Burned area cross-check", "",
              f"Monthly burned area (`{pk['burned_area']['file']}`) vs monthly cell-days, {pk['burned_area']['years'][0]}–"
              f"{pk['burned_area']['years'][1]}. Burned area does not change sensor in 2012, so a fire-count series that "
              "is consistent across 2012 should show **no step once burned area is accounted for** (factor ≈ 1).", "",
              "| country | series | R (log) all | R before 2012 | R from 2012 | step at 2012 given burned area (95% CI) |",
              "|---|---|---|---|---|---|"])
    for c, x in R["burned_area"].items():
        for k in ("naive", "harmonized", "harmonized_local", "modis_only"):
            y = x[k]
            s = y["step_given_burned_area"]
            L.append(f"| {c} | {k} | {f(y['r_log_all'], 2)} | {f(y['r_log_pre2012'], 2)} | {f(y['r_log_post2012'], 2)} | "
                     f"×{f(s['step_factor'], 2)} ({f(s['ci_low'], 2)}–{f(s['ci_high'], 2)}) |")
    L.extend(["", "MODIS alone has no sensor change at 2012, so its step is the change in fire regime; the seam test for "
                  "the harmonized series is its step relative to MODIS alone.",
              "", f"**Takeaway.** {TAKE['ba']}", ""])

    ev = cfg["package"]["events"]
    L.extend(["## 6. Events for the demo", "",
              f"Event = far more fire than usual for that place and month: harmonized cell-days in an H3 res-{ev['h3_res']} "
              "hexagon (~40 km across) minus its normal (median of the same hexagon and calendar month, "
              f"{ev['years'][0]}–{ev['years'][1]}); ranked by that excess; one per region and year in the top list. "
              "Region = ADM1 (pre-2022 boundaries). Coefficients as on the website: Kazakhstan production, every other "
              "country its own refit.", "",
              "| country | rank | region | month | cell-days | normal | excess |", "|---|---|---|---|---|---|---|"])
    for c, x in R["events"].items():
        for e in x["top"]:
            L.append(f"| {c} | {e['rank']} | {e['adm1_name']} | {e['year']}-{e['month']:02d} | {f(e['n_harm'], 0)} | "
                     f"{f(e['expected'], 0)} | {f(e['excess'], 0)} |")
    L.extend(["", "Known events (Kazakhstan), rank among all hexagon-month events:", "",
              "| event | region | month | cell-days (best hexagon) | normal | excess | rank |",
              "|---|---|---|---|---|---|---|"])
    for k in R["events"].get(cfg["train_country"], {}).get("known_events", []):
        L.append(f"| {k['name']} | {k['adm1_id']} | {k['year']}-{k['month']:02d} | {f(k['n_harm'], 0)} | "
                 f"{f(k['expected'], 0)} | {f(k['excess'], 0)} | "
                 f"{str(k['rank']) + ' of ' + str(k['of']) if k['rank'] else '–'} |")
    L.extend(["", f"**Takeaway.** {TAKE['events']}", ""])
    (REPORTS / "VALIDATION.md").write_text("\n".join(L), encoding="utf-8")


TAKE = {}   # plain-language takeaways, filled by takeaways() from the numbers


def takeaways(R, cfg):
    u, t = R["uz_test"], R["tm_stress"]
    tr = R["transfer"]

    def step_txt(r):
        st = r["steps"]
        x = (f"the naive splice jumps ×{f(st['naive']['step_ratio'], 2)} at 2012, the KZ-harmonized series "
             f"×{f(st['harmonized']['step_ratio'], 2)}")
        if "harmonized_local" in st:
            x += f", a locally refitted one ×{f(st['harmonized_local']['step_ratio'], 2)}"
        return x + f" (MODIS alone ×{f(st['modis_only']['step_ratio'], 2)})"
    TAKE["uz"] = (f"Applied to Uzbekistan without any Uzbek data, {step_txt(u)}. In 2012–2019 the KZ model is off by "
                  f"{f(u['overlap_as_is']['mae_pct_of_mean'])}% a month and {f(u['overlap_as_is']['bias_total_pct'], 1, True)}% "
                  f"in total; the same model refitted on Uzbekistan: {f(u['overlap_local_loyo']['mae_pct_of_mean'])}% and "
                  f"{f(u['overlap_local_loyo']['bias_total_pct'], 1, True)}%. Uzbekistan's VIIRS/MODIS ratio is "
                  f"×{f(u['ratio_observed'], 2)}, the KZ model implies ×{f(u['ratio_kz_model'], 2)}: VIIRS sees relatively more "
                  "fires there (C1: small agricultural burns). 2025 contains the new industrial source near 38.1°N 67.3°E "
                  "(C2), so the holdout is also shown to 2024 — it changes little.")
    fl = R["flare_load"]
    TAKE["tm"] = (f"{step_txt(t)[0].upper() + step_txt(t)[1:]}. Overlap error as-is "
                  f"{f(t['overlap_as_is']['mae_pct_of_mean'])}% (bias {f(t['overlap_as_is']['bias_total_pct'], 1, True)}%), "
                  f"local refit {f(t['overlap_local_loyo']['mae_pct_of_mean'])}%. "
                  f"{f(fl['TKM']['static_share_removed_pct'], 0)}% of Turkmenistan's confident detections are static "
                  f"sources (Kazakhstan {f(fl[cfg['train_country']]['static_share_removed_pct'], 0)}%); FIRMS `type` removes "
                  "them in archive data and the mask in recent data (precision/recall above). The remaining error is the "
                  f"same kind as Uzbekistan's: VIIRS/MODIS ×{f(t['ratio_observed'], 2)} vs ×{f(t['ratio_kz_model'], 2)} "
                  "from the KZ model. TM's monthly R is the lowest of the cell-level countries.")
    a = R["annual"]
    TAKE["annual"] = ("Kyrgyzstan and Tajikistan have only a few hundred fire cell-days a year, so only annual totals are "
                      "meaningful. " + "; ".join(f"{c}: annual error {f(x['mae_pct_of_mean'])}%, bias "
                                                 f"{f(x['bias_total_pct'], 1, True)}% (raw MODIS: "
                                                 f"{f(x['naive_modis_bias_pct'], 0, True)}%)" for c, x in a.items())
                      + ". The harmonized totals are usable for a yearly trend, not for single months.")
    yes = sorted(c for c, x in tr.items() if x["transfers"])
    no = sorted(c for c, x in tr.items() if not x["transfers"])
    loc = [x["overlap_local"]["mae_pct_of_mean"] for x in tr.values()]
    TAKE["transfer"] = (f"Transfers as-is: {', '.join(yes) or 'none'}; does not: {', '.join(no) or 'none'}. The observed "
                        "VIIRS/MODIS ratio ranges from ×" + f(min(x['ratio_observed'] for x in tr.values()), 2) + " to ×"
                        + f(max(x['ratio_observed'] for x in tr.values()), 2) + "; the KZ model cannot know a country's ratio "
                        "and errs in the direction of the difference (too high for Portugal, too low for India). "
                        f"Refitted locally, the same model gets {f(min(loc))}–{f(max(loc))}% monthly error. Honest "
                        "conclusion: the METHOD transfers across biomes, the COEFFICIENTS do not — every country needs its "
                        "own 2012–2019 overlap fit (which FIRMS provides everywhere).")
    ba = R["burned_area"]

    def ci1(s):
        return s["ci_low"] <= 1 <= s["ci_high"]
    lines = []
    for k, lab in (("naive", "naive"), ("harmonized", "KZ-harmonized"), ("harmonized_local", "locally harmonized")):
        cont = [c for c, x in ba.items() if ci1(x[k]["step_given_burned_area"])]
        lines.append(f"{lab}: continuous (95% CI includes 1) in {', '.join(cont) or 'none'}")
    TAKE["ba"] = ("Holding burned area fixed, " + "; ".join(lines) + ". The naive series jumps ×"
                  + f(min(x['naive']['step_given_burned_area']['step_factor'] for x in ba.values()), 1) + "–×"
                  + f(max(x['naive']['step_given_burned_area']['step_factor'] for x in ba.values()), 1)
                  + " everywhere. Correlation with burned area is high in Kazakhstan and weak in Kyrgyzstan/Tajikistan "
                    "(few fires; much burned area there is not seen as active fire).")
    ev = R["events"].get(cfg["train_country"], {}).get("known_events", [])
    TAKE["events"] = " ".join(
        f"{k['name']} ({k['year']}-{k['month']:02d}): {f(k['n_harm'], 0)} cell-days in one hexagon vs a normal of "
        f"{f(k['expected'], 0)}, " + (f"rank {k['rank']} of {k['of']}" if k["rank"] else "below the event threshold")
        + "." for k in ev) + (" The top events are the largest local excesses; check them against news before the demo.")
    return TAKE


# ---------------------------------------------------------------- main

def main():
    cfg = load_config()
    pk = cfg["package"]
    man = ingest.load_manifest(cfg)
    card = CAL.read_model_card()
    iv, model = card["intervals"], card["production_model"]
    coefs = kz_coefs()
    if coefs["main"]["model"].iloc[0] != model:
        raise SystemExit("coefficients and model card disagree: rerun 05_calibrate")
    R = {"model": {k: card[k] for k in ("selected", "label", "production_model", "train_country")},
         "pending_countries": sorted(set(ingest.countries(cfg, man)) - set(ready_countries(cfg, man)))}
    harm = {}
    R["uz_test"], _, _, harm[pk["test_country"]] = country_test(pk["test_country"], coefs, cfg, iv, model)
    R["tm_stress"], _, _, harm[pk["stress_country"]] = country_test(pk["stress_country"], coefs, cfg, iv, model)
    R["flare_load"] = flare_load(cfg, [cfg["train_country"], pk["test_country"], pk["stress_country"]])
    R["annual"] = {c: annual_test(c, coefs, cfg, iv, model) for c in pk["annual_countries"]}
    R["transfer"] = transfer_table(cfg, coefs, iv, model, man)
    for c in pk["burned_area"]["names"].values():
        if c not in harm:
            cm = country_months(c, cfg)
            _, harm[c] = steps(cm, coefs, cfg, min(last_full_year(cm), pk["holdout"][1]), model)
    R["burned_area"] = burned_area(cfg, harm)
    R["events"] = {}
    for c in ingest.countries(cfg, man, "cell"):     # each country with the coefficients the website uses
        R["events"].update(events(cfg, coefs if c == cfg["train_country"] else own_coefs(country_months(c, cfg), cfg, model),
                                  [c]))
    takeaways(R, cfg)
    R["takeaways"] = TAKE
    write_json(REPORTS / "validation.json", R)
    write_md(R, cfg)
    log.info("wrote reports/validation.json and reports/VALIDATION.md")
    return R


if __name__ == "__main__":
    main()

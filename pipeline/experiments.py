"""Model selection + interval calibration -> reports/model_comparison.{md,json} and reports/model_card.json.

The model card is the ONE source of truth read by 05_calibrate / 06_harmonize / 07_validate: which model won, its
scores, the single leave-one-region-out number, and the interval parameters (country and region).

Tests (protocol: reports/baseline/model_protocol.md, with ADM1 regions instead of H3 res-1 hexagons since C3):
  T1 backcast  fit 2016-19 -> predict 2012-15      T2 forecast fit 2012-19 -> 2020..last full year (drift)
  T3 LORO      fit 2012-19 without one ADM1 region -> predict that region 2012-19
  T4 LOYO      each year of 2012-19 from the other seven
Score = mean MAE% of T1, T3, T4 (T3 = median over regions holding >= validation.loro_min_share of MODIS activity).
"""
import importlib

import numpy as np
import pandas as pd

from pipeline import calib, intervals, models
from pipeline.common import REPORTS, get_logger, load_config, write_json
from pipeline.metrics import series_metrics

log = get_logger("experiments")
CAL = importlib.import_module("pipeline.05_calibrate")
# spec link (on Terra∪Aqua cell-days) -> production model name in calib.py
PRODUCTION = {"identity": "ratio", "log": "poisson_log", "ols_log1p": "loglog"}


def prepare(cfg):
    cm = CAL.load_cell_month()
    n20, _ = calib.fit(cm, "n_viirs_snpp", "n_viirs_noaa20", tuple(cfg["calibration"]["noaa20_period"]), cfg,
                       intervals=False)
    cm["v_target"] = CAL.target_viirs(cm, n20)
    cm["sub"] = cm["adm1_id"]
    return cm, CAL.last_full_year(cm)


def cols_all():
    return sorted({c for s in models.SPECS.values() for c in s["cols"]})


def run_test(spec, train, test, full, cfg):
    p = models.fit(spec, train, cfg)
    return test.assign(pred=models.predict(spec, p, test, full))


def region_table(cm, cfg):
    """ADM1 regions with their share of MODIS cell-days 2012-2019; 'outside' cells are never held out."""
    c = cfg["calibration"]["period"]
    s = cm[cm["year"].between(*c)].groupby(["sub", "adm1_name"])["n_modis"].sum().reset_index()
    s["share"] = s["n_modis"] / s["n_modis"].sum()
    s = s[s["sub"] != "outside"].sort_values("share", ascending=False)
    s["included"] = s["share"] >= cfg["validation"]["loro_min_share"]
    return s.reset_index(drop=True)


def loro(spec, cm, full, cfg, regs):
    """Leave-one-region-out predictions (region x month, 2012-19). Multipliers use whole-country MODIS totals
    (input data, exactly as in production); the held-out region's VIIRS is never used."""
    cols = cols_all()
    y0, y1 = cfg["calibration"]["period"]
    out = []
    for s in regs["sub"]:
        tr = models.monthly_totals(cm[(cm["sub"] != s) & cm["year"].between(y0, y1)], cols)
        te = models.monthly_totals(cm[(cm["sub"] == s) & cm["year"].between(y0, y1)], cols)
        p = models.fit(spec, tr, cfg)
        f = full[full["year"].between(y0, y1)].reset_index(drop=True)
        te = te.merge(f[["year", "month"]], how="right", on=["year", "month"]).fillna(0)  # months with no fire too
        te["pred"] = models.predict(spec, p, te, full)
        cty = f.assign(pred_country=models.predict(spec, p, f, full))[["year", "month", "pred_country"]]
        out.append(te.merge(cty, on=["year", "month"]).assign(sub=s))
    return pd.concat(out, ignore_index=True)


def loro_summary(t3, regs):
    rows = []
    for s, g in t3.groupby("sub"):
        rows.append({"sub": s, **series_metrics(g["v_target"], g["pred"])})
    L = regs.merge(pd.DataFrame(rows), on="sub")
    inc = L[L["included"]]
    return {"mae_pct_of_mean": float(inc["mae_pct_of_mean"].median()),
            "bias_total_pct": float(inc["bias_total_pct"].median()),
            "abs_bias_median": float(inc["bias_total_pct"].abs().median()),
            "pearson_r": float(inc["pearson_r"].median()),
            "regions_included": int(len(inc)), "regions_total": int(len(L)),
            "by_subregion": L.to_dict(orient="records")}


def evaluate(cm, y1, cfg):
    cols = cols_all()
    full = models.monthly_totals(cm, cols)
    yr = lambda a, b: full[full["year"].between(a, b)]  # noqa: E731
    regs = region_table(cm, cfg)
    out, preds = {}, {}
    for cid, spec in models.SPECS.items():
        r = {}
        t1 = run_test(spec, yr(2016, 2019), yr(2012, 2015), full, cfg)
        r["T1_backcast"] = series_metrics(t1["v_target"], t1["pred"])
        t2 = run_test(spec, yr(2012, 2019), yr(2020, y1), full, cfg)
        r["T2_forecast"] = series_metrics(t2["v_target"], t2["pred"])
        t3 = loro(spec, cm, full, cfg, regs)
        r["T3_loro"] = loro_summary(t3, regs)
        t4 = pd.concat([run_test(spec, yr(2012, 2019)[lambda d: d["year"] != y], yr(y, y), full, cfg)
                        for y in range(2012, 2020)])
        r["T4_loyo"] = series_metrics(t4["v_target"], t4["pred"])
        r["score"] = float(np.mean([r["T1_backcast"]["mae_pct_of_mean"], r["T3_loro"]["mae_pct_of_mean"],
                                    r["T4_loyo"]["mae_pct_of_mean"]]))
        r["n_params"] = models.N_PARAMS[spec["link"]] * len(spec["cols"])
        out[cid] = r
        preds[cid] = {"T1": t1, "T2": t2, "T3": t3, "T4": t4}
        log.info("%s %-38s score %.2f | T1 %.1f T3 %.1f T4 %.1f | T2 %.1f bias %.1f", cid, spec["label"], r["score"],
                 r["T1_backcast"]["mae_pct_of_mean"], r["T3_loro"]["mae_pct_of_mean"],
                 r["T4_loyo"]["mae_pct_of_mean"], r["T2_forecast"]["mae_pct_of_mean"], r["T2_forecast"]["bias_total_pct"])
    return out, preds, regs


def loyo_residuals(spec, train, full, cfg):
    """Each training year predicted from the other training years (country totals)."""
    return pd.concat([run_test(spec, train[train["year"] != y], train[train["year"] == y], full, cfg)
                      for y in sorted(train["year"].unique())])


def interval_study(spec, preds, cm, cfg):
    """Coverage of the 90% interval, before (baseline: country interval applied to every area) and after
    (country interval for the country, size-binned region interval for regions). All coverage is cross-fitted."""
    lvl = cfg["calibration"]["interval_level"]
    ic = cfg["intervals"]

    def fit_c(a, p):
        return intervals.fit_hetero(a, p, lvl)

    def fit_r(a, p):
        return intervals.fit_binned(a, p, ic["region_bin_edges"], lvl, ic["min_bin_n"])

    full = models.monthly_totals(cm, cols_all())
    yr = lambda a, b: full[full["year"].between(a, b)]  # noqa: E731
    t1, t2, t3, t4 = (preds[k] for k in ("T1", "T2", "T3", "T4"))
    res_all = loyo_residuals(spec, yr(2012, 2019), full, cfg)
    res_1619 = loyo_residuals(spec, yr(2016, 2019), full, cfg)
    p_country = fit_c(res_all["v_target"], res_all["pred"])
    p_1619 = fit_c(res_1619["v_target"], res_1619["pred"])

    # before: the country interval, its width set by the COUNTRY prediction, applied to the region prediction
    sc = np.sqrt(p_country["median_pred"] / np.maximum(t3["pred_country"].to_numpy(), 1e-9))
    pr = t3["pred"].to_numpy()
    lo_b = np.floor(np.where(pr > 0, pr * np.exp(p_country["q_lo"] * sc), 0))
    hi_b = np.ceil(np.where(pr > 0, pr * np.exp(p_country["q_hi"] * sc), 0))
    act = t3["v_target"].to_numpy()
    t3 = t3.assign(in_before=(act >= lo_b) & (act <= hi_b))
    cf4 = pd.DataFrame(intervals.cross_fitted(t4.rename(columns={"v_target": "actual"}), "year", fit_c))
    country = {"T1_backcast_country": intervals.coverage(t1["v_target"], t1["pred"], p_1619),
               "T2_holdout_country": intervals.coverage(t2["v_target"], t2["pred"], p_country),
               "T4_loyo_country": float(cf4["covered"].sum() / cf4["n"].sum())}
    before = {"T3_loro_region": float(t3["in_before"].mean()), **country}
    # after: size-binned region interval, fitted on the OTHER regions' leave-one-region-out errors
    cf3 = pd.DataFrame(intervals.cross_fitted(t3.rename(columns={"v_target": "actual"}), "sub", fit_r))
    after = {"T3_loro_region": float(cf3["covered"].sum() / cf3["n"].sum()), **country}
    per_region = cf3.rename(columns={"coverage": "coverage_after", "median_width_pct": "median_width_pct_after"}) \
        .merge(t3.groupby("sub")["in_before"].mean().rename("coverage_before").reset_index(), on="sub")
    p_region = fit_r(t3["v_target"].to_numpy(), t3["pred"].to_numpy())
    out = {"level": lvl, "country": p_country, "region": p_region,
           "coverage_before": before, "coverage_after": after, "per_region": per_region.to_dict(orient="records"),
           "median_region_coverage_before": float(per_region["coverage_before"].median()),
           "median_region_coverage_after": float(per_region["coverage_after"].median()),
           "min_region_coverage_after": float(per_region["coverage_after"].min())}
    log.info("coverage before %s", {k: round(v, 3) for k, v in before.items()})
    log.info("coverage after  %s", {k: round(v, 3) for k, v in after.items()})
    return out


def select(out):
    best = min(out, key=lambda c: out[c]["score"])
    close = [c for c in out if out[c]["score"] <= out[best]["score"] + 0.5]
    return min(close, key=lambda c: (out[c]["n_params"], out[c]["score"]))


def fmt(x, d=1):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def write(out, chosen, iv, regs, cfg):
    L = ["# Model comparison (protocol: baseline/model_protocol.md; regions = ADM1 since C3)", "",
         "MAE as % of the mean monthly total; bias = total over the test period. Score = mean MAE % of T1, T3, T4. "
         f"T3 = median over the {int(regs['included'].sum())} ADM1 regions with ≥ "
         f"{100 * cfg['validation']['loro_min_share']:.0f}% of MODIS activity (of {len(regs)}).", "",
         "| id | model | params | **score** | T1 backcast MAE / bias | T3 LORO MAE / median bias | T4 LOYO MAE / bias | T2 forecast MAE / bias (drift) |",
         "|---|---|---|---|---|---|---|---|"]
    for c, r in sorted(out.items(), key=lambda kv: kv[1]["score"]):
        L.append(f"| {c}{' ✔' if c == chosen else ''} | {models.SPECS[c]['label']} | {r['n_params']} | **{fmt(r['score'], 2)}** | "
                 f"{fmt(r['T1_backcast']['mae_pct_of_mean'])} / {fmt(r['T1_backcast']['bias_total_pct'])} | "
                 f"{fmt(r['T3_loro']['mae_pct_of_mean'])} / {fmt(r['T3_loro']['bias_total_pct'])} | "
                 f"{fmt(r['T4_loyo']['mae_pct_of_mean'])} / {fmt(r['T4_loyo']['bias_total_pct'])} | "
                 f"{fmt(r['T2_forecast']['mae_pct_of_mean'])} / {fmt(r['T2_forecast']['bias_total_pct'])} |")
    L += ["", f"Selected by the protocol rule: **{chosen}** ({models.SPECS[chosen]['label']}).", "",
          "## 90% intervals: before (baseline) vs after (negative binomial at the predicted level)", "",
          "Country: baseline interval (leave-one-year-out log errors, width shrinking with size). Region: percentiles "
          "of leave-one-region-out errors for predictions of similar size. Coverage is cross-fitted: the interval for "
          "a held-out year/region is fitted on the others only.", "",
          "| test | before | after |", "|---|---|---|"]
    keys = [("T3_loro_region", "T3 leave-one-region-out, region-months"), ("T1_backcast_country", "T1 backcast, country"),
            ("T2_holdout_country", "T2 holdout 2020+ (drift), country"), ("T4_loyo_country", "T4 leave-one-year-out, country")]
    for k, lab in keys:
        L.append(f"| {lab} | {fmt(100 * iv['coverage_before'][k], 0) + '%' if k in iv['coverage_before'] else '90% (by construction of the old protocol)'} | "
                 f"{fmt(100 * iv['coverage_after'][k], 0)}% |")
    (REPORTS / "model_comparison.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def model_card(out, chosen, iv, regs, cfg, y1):
    spec = models.SPECS[chosen]
    prod = PRODUCTION.get(spec["link"]) if spec["cols"] == ["n_modis"] else None
    if prod is None:
        raise SystemExit(f"selected {chosen} ({spec['label']}) has no production implementation in calib.py")
    r = out[chosen]
    return {"selected": chosen, "label": spec["label"], "link": spec["link"], "cols": spec["cols"],
            "production_model": prod, "train_country": cfg["train_country"],
            "calibration_period": cfg["calibration"]["period"], "holdout": [cfg["calibration"]["holdout_start"], y1],
            "scores": {"score": r["score"], "T1_backcast_mae_pct": r["T1_backcast"]["mae_pct_of_mean"],
                       "T3_loro_mae_pct": r["T3_loro"]["mae_pct_of_mean"],
                       "T4_loyo_mae_pct": r["T4_loyo"]["mae_pct_of_mean"],
                       "T2_forecast_mae_pct": r["T2_forecast"]["mae_pct_of_mean"],
                       "T2_forecast_bias_pct": r["T2_forecast"]["bias_total_pct"]},
            "loro": {"unit": "ADM1 region-month", "years": cfg["calibration"]["period"],
                     "mae_pct_median": r["T3_loro"]["mae_pct_of_mean"],
                     "regions_included": r["T3_loro"]["regions_included"], "regions_total": r["T3_loro"]["regions_total"],
                     "min_share": cfg["validation"]["loro_min_share"]},
            "intervals": {k: iv[k] for k in ("level", "country", "region", "coverage_before", "coverage_after",
                                             "median_region_coverage_before", "median_region_coverage_after",
                                             "min_region_coverage_after")}}


def main():
    cfg = load_config()
    cm, y1 = prepare(cfg)
    out, preds, regs = evaluate(cm, y1, cfg)
    chosen = select(out)
    iv = interval_study(models.SPECS[chosen], preds[chosen], cm, cfg)
    card = model_card(out, chosen, iv, regs, cfg, y1)
    write_json(REPORTS / "model_card.json", card)
    write_json(REPORTS / "model_comparison.json", {"selected": chosen, "results": out, "intervals": iv,
                                                   "regions": regs.to_dict(orient="records"),
                                                   "specs": {c: s for c, s in models.SPECS.items()}})
    write(out, chosen, iv, regs, cfg)
    log.info("selected %s -> production model %s; LORO MAE %.1f%%", chosen, card["production_model"],
             card["loro"]["mae_pct_median"])


if __name__ == "__main__":
    main()

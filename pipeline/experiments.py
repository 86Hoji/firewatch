"""Model selection + interval calibration -> reports/model_comparison.{md,json} and reports/model_card.json.

The model card is the ONE source of truth read by 05_calibrate / 06_harmonize / 07_validate: which model won, its
scores, the single leave-one-region-out number, and the interval parameters (country and region).

Tests (protocol: reports/baseline/model_protocol.md, with ADM1 regions instead of H3 res-1 hexagons since C3):
  T1 backcast  fit 2016-19 -> predict 2012-15      T2 forecast fit 2012-19 -> 2020..last full year (drift)
  T3 LORO      fit 2012-19 without one ADM1 region -> predict that region 2012-19
  T4 LOYO      each year of 2012-19 from the other seven
  T5 extrap.   per calendar month, fit on the 2012-19 years whose MODIS total is <= its p75, predict the busier years
               (the product predicts 2000-2011, busier than any calibration year: T1-T4 never leave the fitted range)
Score = mean MAE% of T1, T3, T4 (T3 = median over regions holding >= validation.loro_min_share of MODIS activity).
T5 is reported, not scored (protocol unchanged). Also reported: how far 2003-2011 lies outside the calibration range,
and the 2003-2011 annual totals each candidate would produce (structural sensitivity of the product).
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
    n20, _ = calib.fit_noaa20(cm, cfg)
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


def predictor_total(spec, d):
    return d[spec["cols"]].sum(axis=1)


def extrapolation_split(spec, cal, q=0.75):
    """Per calendar month: rows whose predictor total is <= that month's q-quantile train, the rest test."""
    x = predictor_total(spec, cal)
    thr = x.groupby(cal["month"]).transform(lambda s: s.quantile(q))
    test = x > thr
    return cal[~test], cal[test]


def extrapolation_test(spec, full, cfg, years=None):
    """T5: fit on the quieter years of each calendar month, predict the busier ones (country totals)."""
    y0, y1 = years or cfg["calibration"]["period"]
    q = cfg["validation"].get("extrapolation_quantile", 0.75)
    cal = full[full["year"].between(y0, y1)].reset_index(drop=True)
    train, test = extrapolation_split(spec, cal, q)
    t5 = run_test(spec, train, test.reset_index(drop=True), full, cfg)
    tmax = predictor_total(spec, train).groupby(train["month"]).max()
    t5["range_ratio"] = predictor_total(spec, t5).to_numpy() / t5["month"].map(tmax).to_numpy()
    return t5


def range_stats(spec, full, cal_years, years):
    """How far the predicted years lie outside the calibration range: predictor total / same-month calibration max.
    The max is floored at 1 cell-day, so a calendar month with no fire in any calibration year (small countries)
    gives a finite ratio instead of a division by zero."""
    cal = full[full["year"].between(*cal_years)]
    cmax = predictor_total(spec, cal).groupby(cal["month"]).max().clip(lower=1.0)
    d = full[full["year"].between(*years)]
    r = predictor_total(spec, d).to_numpy() / d["month"].map(cmax).to_numpy()
    yearly = d.assign(x=predictor_total(spec, d)).groupby("year")["x"].sum()
    return {"years": list(years), "months": int(len(d)), "share_months_above_max": float(np.mean(r > 1)),
            "median_ratio": float(np.median(r)), "max_ratio": float(np.max(r)),
            "max_calibration_year_total": float(predictor_total(spec, cal).groupby(cal["year"]).sum().max()),
            "max_predicted_year_total": float(yearly.max())}


def sensitivity(specs, full, cfg, years, selected):
    """Annual totals each candidate gives for `years` (fit on the calibration period) and % vs the selected one.
    Years with Terra-only months (before July 2002) need the Terra->Terra+Aqua bridge, so `years` should start 2003."""
    cal = full[full["year"].between(*cfg["calibration"]["period"])]
    d = full[full["year"].between(*years)]
    tot = {}
    for cid, spec in specs.items():
        p = models.fit(spec, cal, cfg)
        tot[cid] = d.assign(pred=models.predict(spec, p, d, full)).groupby("year")["pred"].sum()
    t = pd.DataFrame(tot)
    rows = [{"year": int(y), **{c: float(t.loc[y, c]) for c in t},
             **{f"{c}_vs_selected_pct": float(100 * (t.loc[y, c] / t.loc[y, selected] - 1)) for c in t}}
            for y in t.index]
    total = t.sum()
    return {"years": list(years), "selected": selected, "by_year": rows,
            "total": {c: float(total[c]) for c in t},
            "total_vs_selected_pct": {c: float(100 * (total[c] / total[selected] - 1)) for c in t}}


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
        t5 = extrapolation_test(spec, full, cfg)
        r["T5_extrapolation"] = {**series_metrics(t5["v_target"], t5["pred"]),
                                 "median_range_ratio": float(np.median(t5["range_ratio"]))}
        r["score"] = float(np.mean([r["T1_backcast"]["mae_pct_of_mean"], r["T3_loro"]["mae_pct_of_mean"],
                                    r["T4_loyo"]["mae_pct_of_mean"]]))
        r["n_params"] = models.N_PARAMS[spec["link"]] * len(spec["cols"])
        out[cid] = r
        preds[cid] = {"T1": t1, "T2": t2, "T3": t3, "T4": t4, "T5": t5}
        log.info("%s %-38s score %.2f | T1 %.1f T3 %.1f T4 %.1f | T2 %.1f bias %.1f | T5 %.1f bias %.1f", cid,
                 spec["label"], r["score"], r["T1_backcast"]["mae_pct_of_mean"], r["T3_loro"]["mae_pct_of_mean"],
                 r["T4_loyo"]["mae_pct_of_mean"], r["T2_forecast"]["mae_pct_of_mean"], r["T2_forecast"]["bias_total_pct"],
                 r["T5_extrapolation"]["mae_pct_of_mean"], r["T5_extrapolation"]["bias_total_pct"])
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


class _YearIndex:
    """Fast resampling of a prediction table by year: row indices per year, absolute errors and actuals as arrays."""

    def __init__(self, df, group=None):
        self.err = np.abs(df["pred"].to_numpy(float) - df["v_target"].to_numpy(float))
        self.act = df["v_target"].to_numpy(float)
        self.rows = {y: np.flatnonzero(df["year"].to_numpy() == y) for y in np.unique(df["year"])}
        self.g, self.ng = (pd.factorize(df[group])[0], df[group].nunique()) if group else (None, 0)

    def mae_pct(self, years):
        idx = np.concatenate([self.rows[y] for y in years if y in self.rows] or [np.array([], int)])
        if self.g is None:
            return 100 * self.err[idx].mean() / self.act[idx].mean() if len(idx) and self.act[idx].mean() > 0 \
                else np.nan
        g = self.g[idx]
        e, a, n = (np.bincount(g, w, self.ng) for w in (self.err[idx], self.act[idx], np.ones(len(idx))))
        ok = (n > 0) & (a > 0)
        return float(np.median(100 * e[ok] / a[ok])) if ok.any() else np.nan   # per-group MAE % of mean, median


def score_bootstrap(preds, regs, chosen, years=(2012, 2019), n=1000, seed=42, level=0.90):
    """Paired bootstrap over calibration years of the protocol score (mean MAE% of T1, T3, T4) for every candidate
    minus the selected one. Answers "is the winner's margin real?": interval of the difference and how often each
    candidate would have won. Same years for all models in a draw (paired). T1 tests 2012-15 only, so it uses the
    drawn years that fall there. T3 = median over the included regions, as in the protocol."""
    rng = np.random.default_rng(seed)
    pool = np.arange(years[0], years[1] + 1)
    inc = set(regs.loc[regs["included"], "sub"])
    lo, hi = (1 - level) / 2, 1 - (1 - level) / 2
    ix = {c: (_YearIndex(pr["T1"]), _YearIndex(pr["T3"][pr["T3"]["sub"].isin(inc)], "sub"), _YearIndex(pr["T4"]))
          for c, pr in preds.items()}
    S = np.empty((n, len(ix)))
    for k in range(n):
        ys = rng.choice(pool, len(pool), replace=True)
        for m, (t1, t3, t4) in enumerate(ix.values()):
            S[k, m] = np.nanmean([t1.mae_pct(ys), t3.mae_pct(ys), t4.mae_pct(ys)])
    S = pd.DataFrame(S, columns=list(ix))
    win = S.idxmin(axis=1).value_counts(normalize=True)
    out = {}
    for c in S:
        d = S[c] - S[chosen]
        out[c] = {"diff_vs_selected_median": float(d.median()), "diff_ci_low": float(d.quantile(lo)),
                  "diff_ci_high": float(d.quantile(hi)), "share_wins": float(win.get(c, 0.0))}
    return {"n": n, "seed": seed, "level": level, "years": list(years), "by_model": out}


def select(out):
    best = min(out, key=lambda c: out[c]["score"])
    close = [c for c in out if out[c]["score"] <= out[best]["score"] + 0.5]
    return min(close, key=lambda c: (out[c]["n_params"], out[c]["score"]))


def fmt(x, d=1):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def write(out, chosen, iv, regs, cfg, sb, ex):
    L = ["# Model comparison (protocol: baseline/model_protocol.md; regions = ADM1 since C3)", "",
         "MAE as % of the mean monthly total; bias = total over the test period. Score = mean MAE % of T1, T3, T4. "
         f"T3 = median over the {int(regs['included'].sum())} ADM1 regions with ≥ "
         f"{100 * cfg['validation']['loro_min_share']:.0f}% of MODIS activity (of {len(regs)}).", "",
         "T5 (extrapolation, reported only): per calendar month, fit on the 2012–2019 years whose MODIS total is at or "
         "below the month's 75th percentile, predict the busier years.", "",
         "| id | model | params | **score** | T1 backcast MAE / bias | T3 LORO MAE / median bias | T4 LOYO MAE / bias | T2 forecast MAE / bias (drift) | T5 extrapolation MAE / bias |",
         "|---|---|---|---|---|---|---|---|---|"]
    for c, r in sorted(out.items(), key=lambda kv: kv[1]["score"]):
        L.append(f"| {c}{' ✔' if c == chosen else ''} | {models.SPECS[c]['label']} | {r['n_params']} | **{fmt(r['score'], 2)}** | "
                 f"{fmt(r['T1_backcast']['mae_pct_of_mean'])} / {fmt(r['T1_backcast']['bias_total_pct'])} | "
                 f"{fmt(r['T3_loro']['mae_pct_of_mean'])} / {fmt(r['T3_loro']['bias_total_pct'])} | "
                 f"{fmt(r['T4_loyo']['mae_pct_of_mean'])} / {fmt(r['T4_loyo']['bias_total_pct'])} | "
                 f"{fmt(r['T2_forecast']['mae_pct_of_mean'])} / {fmt(r['T2_forecast']['bias_total_pct'])} | "
                 f"{fmt(r['T5_extrapolation']['mae_pct_of_mean'])} / {fmt(r['T5_extrapolation']['bias_total_pct'])} |")
    L += ["", f"Selected by the protocol rule: **{chosen}** ({models.SPECS[chosen]['label']}).", "",
          "## 90% intervals: before (baseline) vs after (conformal, sized at the predicted level)", "",
          "Country: baseline interval (leave-one-year-out log errors, width shrinking with size). Region: percentiles "
          "of leave-one-region-out errors for predictions of similar size. Coverage is cross-fitted: the interval for "
          "a held-out year/region is fitted on the others only.", "",
          "| test | before | after |", "|---|---|---|"]
    keys = [("T3_loro_region", "T3 leave-one-region-out, region-months"), ("T1_backcast_country", "T1 backcast, country"),
            ("T2_holdout_country", "T2 holdout 2020+ (drift), country"), ("T4_loyo_country", "T4 leave-one-year-out, country")]
    for k, lab in keys:
        L.append(f"| {lab} | {fmt(100 * iv['coverage_before'][k], 0) + '%' if k in iv['coverage_before'] else '90% (by construction of the old protocol)'} | "
                 f"{fmt(100 * iv['coverage_after'][k], 0)}% |")
    L += _selection_section(sb, chosen) + _extrapolation_section(ex, chosen)
    (REPORTS / "model_comparison.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def _selection_section(sb, chosen):
    L = ["", "## How sure is the choice?", "",
         f"Paired bootstrap over calibration years ({sb['n']} draws): score of each model minus the selected "
         f"**{chosen}**, with a {100 * sb['level']:.0f}% interval, and how often each model would have the best score. "
         "An interval that contains 0 means the data cannot tell the two apart; the parsimony rule then decides.", "",
         "| id | score − selected (median) | interval | wins |", "|---|---|---|---|"]
    for c, r in sorted(sb["by_model"].items(), key=lambda kv: kv[1]["diff_vs_selected_median"]):
        L.append(f"| {c} | {fmt(r['diff_vs_selected_median'], 2)} | {fmt(r['diff_ci_low'], 2)} … "
                 f"{fmt(r['diff_ci_high'], 2)} | {fmt(100 * r['share_wins'], 0)}% |")
    return L


def _extrapolation_section(ex, chosen):
    rs, se = ex["range"], ex["sensitivity"]
    L = ["", "## Extrapolation: the product predicts busier years than it was fitted on", "",
         f"{rs['years'][0]}–{rs['years'][1]}: {fmt(100 * rs['share_months_above_max'], 0)}% of months have more MODIS "
         f"cell-days than the same calendar month in any calibration year (median ratio to that maximum "
         f"{fmt(rs['median_ratio'], 2)}, largest {fmt(rs['max_ratio'], 2)}); busiest year "
         f"{fmt(rs['max_predicted_year_total'], 0)} vs busiest calibration year {fmt(rs['max_calibration_year_total'], 0)}.",
         "", f"Annual totals each candidate would give for {se['years'][0]}–{se['years'][1]} "
         f"(VIIRS S-NPP-equivalent cell-days; % = difference from the selected {chosen}). "
         "The spread is model (structural) uncertainty that the 90% interval does not contain. Computed with "
         "`pipeline/models.py` on country totals, like T1–T5; the published series comes from `calib.py` "
         "(same model, plus land-cover strata if present), so the selected column can differ slightly from `n_harm`.",
         ""]
    cols = [c for c in ("C0", "C1", "C2", chosen) if c in se["total"]]
    cols = list(dict.fromkeys(cols))
    L += ["| year | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for r in se["by_year"]:
        L.append(f"| {r['year']} | " + " | ".join(
            fmt(r[c], 0) + ("" if c == chosen else f" ({r[c + '_vs_selected_pct']:+.1f}%)") for c in cols) + " |")
    L.append("| **total** | " + " | ".join(
        fmt(se["total"][c], 0) + ("" if c == chosen else f" ({se['total_vs_selected_pct'][c]:+.1f}%)")
        for c in cols) + " |")
    span = [v for c, v in se["total_vs_selected_pct"].items()]
    L += ["", f"All {len(span)} candidates: total from {min(span):+.1f}% to {max(span):+.1f}% vs the selected model."]
    return L


def model_card(out, chosen, iv, regs, cfg, y1, sb=None, ex=None):
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
                       "T2_forecast_bias_pct": r["T2_forecast"]["bias_total_pct"],
                       "T5_extrapolation_mae_pct": r["T5_extrapolation"]["mae_pct_of_mean"],
                       "T5_extrapolation_bias_pct": r["T5_extrapolation"]["bias_total_pct"]},
            "selection_bootstrap": sb,
            "extrapolation": None if ex is None else {
                "range": ex["range"], "sensitivity_years": ex["sensitivity"]["years"],
                "total_vs_selected_pct": ex["sensitivity"]["total_vs_selected_pct"]},
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
    sb = score_bootstrap(preds, regs, chosen, tuple(cfg["calibration"]["period"]),
                         n=cfg["validation"].get("selection_bootstrap_iter", 1000),
                         seed=cfg["calibration"]["bootstrap_seed"])
    full = models.monthly_totals(cm, cols_all())
    yrs = tuple(cfg["validation"].get("sensitivity_years", [2003, 2011]))
    ex = {"range": range_stats(models.SPECS[chosen], full, tuple(cfg["calibration"]["period"]), yrs),
          "sensitivity": sensitivity(models.SPECS, full, cfg, yrs, chosen)}
    card = model_card(out, chosen, iv, regs, cfg, y1, sb, ex)
    write_json(REPORTS / "model_card.json", card)
    write_json(REPORTS / "model_comparison.json", {"selected": chosen, "results": out, "intervals": iv,
                                                   "selection_bootstrap": sb, "extrapolation": ex,
                                                   "regions": regs.to_dict(orient="records"),
                                                   "specs": {c: s for c, s in models.SPECS.items()}})
    write(out, chosen, iv, regs, cfg, sb, ex)
    log.info("selected %s -> production model %s; LORO MAE %.1f%%", chosen, card["production_model"],
             card["loro"]["mae_pct_median"])


if __name__ == "__main__":
    main()

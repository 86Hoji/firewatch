"""Validation: temporal holdout, leave-one-region-out, 2012 jump test, seasonality, synthetic recovery, events."""
import importlib
import json

import h3
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from pipeline import calib  # noqa: E402
from pipeline.common import AGG, REF, REPORTS, SEASONS, ensure_dirs, get_logger, load_config, write_json  # noqa: E402
from pipeline.metrics import pettitt, series_metrics, step_test  # noqa: E402
from scipy import stats  # noqa: E402

log = get_logger("validate")
CAL = importlib.import_module("pipeline.05_calibrate")
INK, MOD, VII, HARM, BAND = "#1d1d1f", "#d95f02", "#1b9e77", "#3b2f8f", "#b8b0e8"


def monthly(df, cols):
    return df.groupby(["year", "month"])[cols].sum().reset_index()


def predict_months(cm, coefs, model, years, totals, draws=None, cfg=None):
    h = cm[cm["year"].between(*years)].copy()
    h["actual"] = CAL.target_viirs(h, coefs["noaa20"])
    p = calib.predict(h, "n_modis", coefs[model], totals=totals, draws=draws, cfg=cfg)
    return pd.concat([h[["year", "month", "actual", "n_modis"]], p], axis=1).groupby(["year", "month"]).sum().reset_index()


def temporal_holdout(cm, coefs, draws, cfg, y1, best):
    c = cfg["calibration"]
    tot = calib.regional_totals(cm, "n_modis")
    out = {"in_sample": {}, "holdout": {}, "holdout_by_season": {}, "holdout_by_year": {}}
    for model in c["models"]:
        ins = predict_months(cm, coefs, model, tuple(c["period"]), tot, draws[model], cfg)
        ho = predict_months(cm, coefs, model, (c["holdout_start"], y1), tot, draws[model], cfg)
        out["in_sample"][model] = series_metrics(ins["actual"], ins["pred"], ins["low"], ins["high"])
        m = series_metrics(ho["actual"], ho["pred"], ho["low"], ho["high"])
        m["coverage_ci"] = float(np.mean((ho["actual"] >= ho["ci_low"]) & (ho["actual"] <= ho["ci_high"])))
        out["holdout"][model] = m
        if model == best:
            ho_best = ho
    for s, g in ho_best.groupby(ho_best["month"].map(SEASONS)):
        out["holdout_by_season"][s] = series_metrics(g["actual"], g["pred"], g["low"], g["high"])
    for y, g in ho_best.groupby("year"):
        out["holdout_by_year"][int(y)] = {"actual": float(g["actual"].sum()), "pred": float(g["pred"].sum()),
                                          "bias_pct": float(100 * (g["pred"].sum() / g["actual"].sum() - 1))}
    t = pd.to_datetime(dict(year=ho_best["year"], month=ho_best["month"], day=1))
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.6), gridspec_kw={"width_ratios": [2.4, 1]})
    ax[0].fill_between(t, ho_best["low"], ho_best["high"], color=BAND, alpha=.6, lw=0, label="90% predictive interval")
    ax[0].plot(t, ho_best["actual"], color=VII, lw=1.8, label="VIIRS S-NPP (observed)")
    ax[0].plot(t, ho_best["pred"], color=HARM, lw=1.4, ls="--", label="MODIS → harmonized")
    ax[0].set_yscale("symlog", linthresh=10)
    ax[0].set_title(f"Holdout {c['holdout_start']}–{y1}: unseen years", loc="left")
    ax[0].legend(frameon=False, loc="upper left")
    mx = max(ho_best["actual"].max(), ho_best["pred"].max()) * 1.1
    ax[1].loglog(ho_best["actual"].clip(lower=1), ho_best["pred"].clip(lower=1), "o", ms=4, color=HARM, alpha=.7)
    ax[1].plot([1, mx], [1, mx], color=INK, lw=.8)
    ax[1].set_xlabel("observed VIIRS cell-days / month")
    ax[1].set_ylabel("harmonized MODIS")
    r = out["holdout"][best]
    ax[1].set_title(f"R = {r['pearson_r']:.3f}, bias = {r['bias_total_pct']:+.1f}%", loc="left")
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(REPORTS / "holdout.png", dpi=140)
    plt.close(fig)
    return out


def subregions(cm, cfg):
    res = cfg["validation"]["subregion_h3_res"]
    cells = pd.DataFrame({"h3_cell": cm["h3_cell"].unique()})
    cells["sub"] = [h3.cell_to_parent(c, res) for c in cells["h3_cell"]]
    w = cm.merge(cells, on="h3_cell").groupby("sub")["n_modis"].sum()
    small = w[w / w.sum() < cfg["validation"]["subregion_min_share"]].index
    cells.loc[cells["sub"].isin(small), "sub"] = "merged_small"
    return cm.merge(cells, on="h3_cell")


def spatial_cv(cm, cfg, y1):
    """Leave-one-region-out. The log-log multiplier is set by whole-region MODIS totals (input data, as in
    production); VIIRS of the held-out region is never used for fitting."""
    d = subregions(cm, cfg)
    tot = calib.regional_totals(cm, "n_modis")
    rows = []
    for s in sorted(d["sub"].unique()):
        train, test = d[d["sub"] != s], d[d["sub"] == s]
        coefs, _ = CAL.fit_all(train, cfg, totals=tot)
        lat, lon = h3.cell_to_latlng(s) if s != "merged_small" else (np.nan, np.nan)
        for model in cfg["calibration"]["models"]:
            p = predict_months(test, coefs, model, (cfg["calibration"]["period"][0], y1), tot)
            m = series_metrics(p["actual"], p["pred"], p["low"], p["high"])
            rows.append({"subregion": s, "model": model, "center_lat": lat, "center_lon": lon,
                         "modis_cell_days": int(test["n_modis"].sum()), **m})
    return pd.DataFrame(rows)


def jump_test(cm, cfg, y1):
    v = cfg["validation"]
    cut = cfg["calibration"]["period"][0]
    a = cm[cm["year"].between(2001, y1)].groupby("year")[
        ["p_modis", "p_viirs_snpp", "n_modis", "n_viirs_snpp", "n_harm", "n_harm_low", "n_harm_high"]].sum()
    pre = a.index < cut
    series = {
        "naive_points": np.where(pre, a["p_modis"], a["p_viirs_snpp"]),
        "naive_cell_days": np.where(pre, a["n_modis"], a["n_viirs_snpp"]),
        "harmonized": a["n_harm"].to_numpy(),
        "modis_only_reference": a["n_modis"].to_numpy(),
    }
    years = a.index.to_numpy()
    out = {}
    for name, x in series.items():
        s = pd.Series(x, index=years)
        step = s.loc[v["post_jump"][0]:v["post_jump"][1]].mean() / s.loc[v["pre_jump"][0]:v["pre_jump"][1]].mean()
        t, K, p = pettitt(np.log1p(x))
        out[name] = {"step_ratio": float(step), "pettitt_change_after_year": int(years[t]), "pettitt_p": p}
    # monthly step regression (season dummies + trend + step), drift-free years only
    m = monthly(cm[cm["year"].between(2003, cfg["calibration"]["period"][1])],
                ["p_modis", "p_viirs_snpp", "n_modis", "n_harm"])
    pre_m = m["year"] < cut
    monthly_series = {"naive_points": np.where(pre_m, m["p_modis"], m["p_viirs_snpp"]),
                      "harmonized": m["n_harm"], "modis_only_reference": m["n_modis"]}
    for name, x in monthly_series.items():
        out[name]["monthly_step"] = step_test(m["year"], m["month"], x, cut)
    ref = out["modis_only_reference"]["step_ratio"]
    for name in out:
        out[name]["excess_jump_vs_modis"] = out[name]["step_ratio"] / ref
    fig, ax = plt.subplots(1, 2, figsize=(14, 5), sharey=False)
    ax[0].bar(years[pre], series["naive_points"][pre], color=MOD, width=.8, label="MODIS points")
    ax[0].bar(years[~pre], series["naive_points"][~pre], color=VII, width=.8, label="VIIRS S-NPP points")
    ax[0].set_title(f"BEFORE · naive splice — jump ×{out['naive_points']['step_ratio']:.2f} at 2012\n"
                    f"(MODIS alone changes ×{ref:.2f})", loc="left")
    ax[1].fill_between(years, a["n_harm_low"], a["n_harm_high"], color=BAND, alpha=.7, lw=0, step="mid",
                       label="90% interval (calibrated years)")
    ax[1].bar(years[pre], series["harmonized"][pre], color=HARM, alpha=.55, width=.8, label="MODIS → S-NPP equivalent")
    ax[1].bar(years[~pre], series["harmonized"][~pre], color=HARM, width=.8, label="VIIRS S-NPP")
    ax[1].set_title(f"AFTER · harmonized cell-days — ×{out['harmonized']['step_ratio']:.2f} at 2012\n"
                    f"(excess vs MODIS: ×{out['harmonized']['excess_jump_vs_modis']:.2f})", loc="left")
    for a_ in ax:
        a_.axvline(cut - .5, color=INK, ls="--", lw=.9)
        a_.legend(frameon=False, loc="upper left")
        a_.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(REPORTS / "before_after.png", dpi=140)
    plt.close(fig)
    return out


def seasonality(cm, cfg, y1):
    m = monthly(cm[cm["year"] >= cfg["calibration"]["period"][0]], ["n_modis", "n_viirs_snpp"])
    rows = []
    for y, g in m.groupby("year"):
        if y > y1:
            continue
        pm, pv = int(g.loc[g["n_modis"].idxmax(), "month"]), int(g.loc[g["n_viirs_snpp"].idxmax(), "month"])
        rows.append({"year": int(y), "peak_modis": pm, "peak_viirs": pv})
    t = pd.DataFrame(rows)
    cal = t[t["year"] <= cfg["calibration"]["period"][1]]
    near = lambda d: (abs(d["peak_modis"] - d["peak_viirs"]) % 12).isin([0, 1, 11]).mean()  # noqa: E731
    return {"table": rows, "agree_exact_2012_2019": float((cal["peak_modis"] == cal["peak_viirs"]).mean()),
            "agree_within_1_2012_2019": float(near(cal)), "agree_exact_all": float((t["peak_modis"] == t["peak_viirs"]).mean())}


def synthetic_check(cfg):
    from tests.conftest import synthetic_cell_month
    cm = synthetic_cell_month({"A": 3.2, "B": 2.1})
    coef, _ = calib.fit(cm, "n_viirs_snpp", "n_modis", (2012, 2019), cfg)
    rec = coef.groupby("land_cover")["k"].agg(["min", "max"]).to_dict(orient="index")
    true = {"A": 3.2, "B": 2.1}
    err = max(abs(rec[k][s] / true[k] - 1) for k in true for s in ("min", "max"))
    return {"true": true, "recovered_min_max": rec, "max_rel_error": float(err), "passed": bool(err < 0.05)}


def burned_area_check(cm, cfg):
    """Independent check vs MCD64A1 burned area: correlation and fire-days per km² burned, before vs after 2012."""
    p = REF / "burned_area_monthly.parquet"
    if not p.exists():
        return None
    ba = pd.read_parquet(p)
    ba = ba[ba["tiles"] == ba["tiles"].max()]          # only months with the full tile set
    cut = cfg["calibration"]["period"][0]
    m = monthly(cm, ["n_harm", "p_modis", "p_viirs_snpp"]).merge(ba, on=["year", "month"])
    m["naive_points"] = np.where(m["year"] < cut, m["p_modis"], m["p_viirs_snpp"])
    out = {"tiles": int(ba["tiles"].max()), "years": [int(m["year"].min()), int(m["year"].max())], "series": {}}
    for name in ("n_harm", "naive_points"):
        rows = {}
        for side, g in (("before_2012", m[m["year"] < cut]), ("from_2012", m[m["year"] >= cut])):
            g = g[g["burned_km2"] > 0]
            rows[side] = {"months": int(len(g)),
                          "spearman": float(stats.spearmanr(g[name], g["burned_km2"])[0]) if len(g) > 2 else None,
                          "pearson_log": float(stats.pearsonr(np.log1p(g[name]), np.log1p(g["burned_km2"]))[0]) if len(g) > 2 else None,
                          "per_km2": float(g[name].sum() / g["burned_km2"].sum()) if len(g) else None}
        b, a = rows["before_2012"]["per_km2"], rows["from_2012"]["per_km2"]
        rows["per_km2_step"] = a / b if a and b else None
        out["series"]["harmonized" if name == "n_harm" else name] = rows
    return out


def known_events(cm, cfg):
    rows = []
    for e in cfg["validation"].get("known_events", []):
        w, s, ea, n = e["bbox"]
        d = cm[cm["lon"].between(w, ea) & cm["lat"].between(s, n)]
        m = monthly(d, ["n_harm"])
        same = m[m["month"] == e["month"]].sort_values("n_harm", ascending=False).reset_index(drop=True)
        allm = m.sort_values("n_harm", ascending=False).reset_index(drop=True)
        hit = (same["year"] == e["year"])
        rows.append({"name": e["name"], "year": e["year"], "month": e["month"],
                     "value": float(same.loc[hit, "n_harm"].sum()),
                     "median_same_month": float(same["n_harm"].median()),
                     "rank_among_same_month": int(hit.idxmax() + 1) if hit.any() else None, "of_years": len(same),
                     "rank_among_all_months": int(((allm["year"] == e["year"]) & (allm["month"] == e["month"])).idxmax() + 1),
                     "of_months": len(allm)})
    return rows


def coef_plot(coefs, best):
    fig, ax = plt.subplots(figsize=(10, 3.8))
    for model, color in (("ratio", MOD), ("loglog", "#888888"), ("poisson_log", HARM)):
        t = coefs[coefs["role"].eq("main") & coefs["model"].eq(model)].sort_values("month")
        if t.empty:
            continue
        ax.fill_between(t["month"], t["k"] * np.exp(t["pi_lo"]), t["k"] * np.exp(t["pi_hi"]), color=color, alpha=.12,
                        lw=0, label=f"{model}: 90% prediction (LOYO)")
        ax.fill_between(t["month"], t["k_p05"], t["k_p95"], color=color, alpha=.35, lw=0, label=f"{model}: 90% bootstrap CI")
        ax.plot(t["month"], t["k"], "o-", color=color, label=f"{model}: multiplier at typical month")
    ax.set_xticks(range(1, 13), list("JFMAMJJASOND"))
    ax.set_title(f"VIIRS / MODIS cell-day multiplier by month (selected: {best})", loc="left")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(REPORTS / "coefficients.png", dpi=140)
    plt.close(fig)


def fmt(x, d=1):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def write_report(M, cfg):
    c = cfg["calibration"]
    best = M["selected_model"]
    h = M["temporal_holdout"]["holdout"][best]
    j = M["jump"]
    mc = json.loads((REPORTS / "model_comparison.json").read_text(encoding="utf-8")) \
        if (REPORTS / "model_comparison.json").exists() else None
    L = [f"# Validation — {cfg['region']['name']}", "",
         f"Calibration {c['period'][0]}–{c['period'][1]}, holdout {c['holdout_start']}–{M['last_full_year']}. "
         f"Unit: H3 res {cfg['grid']['h3_res']} cell-days, VIIRS S-NPP equivalent. Selected model: **{best}**.", "",
         "## Summary / Вывод", "",
         f"**EN.** On years the model never saw ({c['holdout_start']}–{M['last_full_year']}), harmonized MODIS reproduces "
         f"observed VIIRS S-NPP monthly fire activity with R = {fmt(h['pearson_r'], 3)} and total bias {fmt(h['bias_total_pct'])}%. "
         f"The naive MODIS→VIIRS splice jumps ×{fmt(j['naive_points']['step_ratio'], 2)} at 2012, while MODIS alone changes "
         f"×{fmt(j['modis_only_reference']['step_ratio'], 2)}; after harmonization the step is ×{fmt(j['harmonized']['step_ratio'], 2)}.", "",
         f"**RU.** На годах, которых модель не видела ({c['holdout_start']}–{M['last_full_year']}), гармонизированный MODIS "
         f"воспроизводит наблюдаемую активность VIIRS S-NPP по месяцам с R = {fmt(h['pearson_r'], 3)} и суммарным смещением "
         f"{fmt(h['bias_total_pct'])}%. Наивная склейка MODIS→VIIRS даёт скачок ×{fmt(j['naive_points']['step_ratio'], 2)} в 2012 году, "
         f"хотя сам MODIS меняется лишь в ×{fmt(j['modis_only_reference']['step_ratio'], 2)}; после гармонизации скачок ×"
         f"{fmt(j['harmonized']['step_ratio'], 2)}.", "",
         "![before/after](before_after.png)", ""]
    if mc:
        sel = mc["selected"]
        r = mc["results"][sel]
        iv = mc["intervals"]
        L += ["## 0. Model choice", "",
              f"Protocol fixed before running: [model_protocol.md](model_protocol.md); all candidates: "
              f"[model_comparison.md](model_comparison.md). Selected **{sel}** ({mc['specs'][sel]['label']}): "
              f"backcast 2016–19→2012–15 MAE {fmt(r['T1_backcast']['mae_pct_of_mean'])}%, leave-one-region-out "
              f"{fmt(r['T3_loro']['mae_pct_of_mean'])}%, leave-one-year-out {fmt(r['T4_loyo']['mae_pct_of_mean'])}%. "
              f"Intervals: **{iv['selected']}**, coverage of the nominal 90% on drift-free tests "
              f"{fmt(100 * iv[iv['selected']]['coverage'], 0)}%.", ""]
    L += ["## 1. Temporal holdout", "",
         "| model | period | MAE | MAE % mean | bias % | median rel. bias % | Pearson R | Spearman ρ | coverage (pred. 90%) | coverage (bootstrap CI) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for per in ("in_sample", "holdout"):
        for mdl, r in M["temporal_holdout"][per].items():
            L.append(f"| {mdl} | {per} | {fmt(r['mae'])} | {fmt(r['mae_pct_of_mean'])} | {fmt(r['bias_total_pct'])} | "
                     f"{fmt(r['bias_median_rel_pct'])} | {fmt(r['pearson_r'], 3)} | {fmt(r['spearman_rho'], 3)} | "
                     f"{fmt(100 * r['coverage'], 0)}% | {fmt(100 * r['coverage_ci'], 0) + '%' if 'coverage_ci' in r else '—'} |")
    L += ["", "Holdout by season (selected model):", "", "| season | MAE % mean | bias % | R | coverage |", "|---|---|---|---|---|"]
    for s, r in M["temporal_holdout"]["holdout_by_season"].items():
        L.append(f"| {s} | {fmt(r['mae_pct_of_mean'])} | {fmt(r['bias_total_pct'])} | {fmt(r['pearson_r'], 3)} | {fmt(100 * r['coverage'], 0)}% |")
    L += ["", "Holdout by year (watch for MODIS orbit drift):", "", "| year | observed | harmonized MODIS | bias % |", "|---|---|---|---|"]
    for y, r in M["temporal_holdout"]["holdout_by_year"].items():
        L.append(f"| {y} | {fmt(r['actual'], 0)} | {fmt(r['pred'], 0)} | {fmt(r['bias_pct'])} |")
    L += ["", "![holdout](holdout.png)", "",
          "Intervals. `n_harm_low/high` = prediction interval: leave-one-year-out residuals log(VIIRS/pred) of regional "
          "monthly totals inside 2012–2019, 5th–95th percentile per season (cross-conformal). `n_harm_ci_*` = bootstrap "
          "over years of the coefficients only, so it is expected to under-cover single months. Intervals are calibrated "
          "for regional monthly totals; for small areas true uncertainty is wider.", "",
          "## 2. Spatial cross-validation (leave-one-region-out)", "",
          f"Subregions: H3 res {cfg['validation']['subregion_h3_res']} parents; ones with < "
          f"{100 * cfg['validation']['subregion_min_share']:.0f}% of MODIS cell-days merged. Calibrated without the region, "
          f"tested on it over {c['period'][0]}–{M['last_full_year']}. Log-log multipliers use whole-region MODIS totals "
          "(input data, exactly as in production). Median over subregions: "
          + "; ".join(f"{k}: MAE {fmt(v['mae_pct_of_mean'])}%, bias {fmt(v['bias_total_pct'])}%, coverage "
                      f"{fmt(100 * v['coverage'], 0)}%" for k, v in M['spatial_cv_median'].items()) + ".", "",
          "| subregion | model | center | MODIS cell-days | MAE % mean | bias % | R | coverage |", "|---|---|---|---|---|---|---|---|"]
    for r in M["spatial_cv"]:
        L.append(f"| `{r['subregion']}` | {r['model']} | {fmt(r['center_lat'])}, {fmt(r['center_lon'])} | {r['modis_cell_days']} | "
                 f"{fmt(r['mae_pct_of_mean'])} | {fmt(r['bias_total_pct'])} | {fmt(r['pearson_r'], 3)} | {fmt(100 * r['coverage'], 0)}% |")
    L += ["", "## 3. The 2012 jump", "",
          f"Step ratio = mean({cfg['validation']['post_jump'][0]}–{cfg['validation']['post_jump'][1]}) / "
          f"mean({cfg['validation']['pre_jump'][0]}–{cfg['validation']['pre_jump'][1]}) of annual totals. "
          "MODIS-only is the same instrument on both sides, so its step is the real change; excess = series step / MODIS step. "
          "Pettitt test on log annual totals.", "",
          "| series | step ratio | excess vs MODIS | Pettitt change after | Pettitt p |", "|---|---|---|---|---|"]
    for k, r in j.items():
        L.append(f"| {k} | ×{fmt(r['step_ratio'], 2)} | ×{fmt(r['excess_jump_vs_modis'], 2)} | {r['pettitt_change_after_year']} | {fmt(r['pettitt_p'], 4)} |")
    L += ["", "Monthly step regression, 2003–2019 (log1p series ~ month dummies + linear trend + step at 2012; "
          "Newey-West 95% CI, 12 lags). A sensor artefact shows as a step whose CI excludes 1; MODIS-only is the "
          "same-instrument reference.", "", "| series | step factor | 95% CI | CI includes 1 |", "|---|---|---|---|"]
    for k, r in j.items():
        s = r.get("monthly_step")
        if s:
            L.append(f"| {k} | ×{fmt(s['step_factor'], 2)} | {fmt(s['ci_low'], 2)}–{fmt(s['ci_high'], 2)} | "
                     f"{'yes' if s['ci_includes_1'] else 'no'} |")
    s = M["seasonality"]
    L += ["", "## 4. Seasonality", "",
          f"Peak month MODIS = VIIRS in {fmt(100 * s['agree_exact_2012_2019'], 0)}% of years 2012–2019 "
          f"(within ±1 month: {fmt(100 * s['agree_within_1_2012_2019'], 0)}%); all overlap years: {fmt(100 * s['agree_exact_all'], 0)}%.", "",
          "| year | peak MODIS | peak VIIRS |", "|---|---|---|"]
    L += [f"| {r['year']} | {r['peak_modis']} | {r['peak_viirs']} |" for r in s["table"]]
    sy = M["synthetic"]
    L += ["", "## 5. Synthetic recovery (sanity check, synthetic data only)", "",
          f"True k: {sy['true']}. Recovered (min–max over months): "
          + ", ".join(f"{k}: {fmt(v['min'], 3)}–{fmt(v['max'], 3)}" for k, v in sy["recovered_min_max"].items())
          + f". Max relative error {fmt(100 * sy['max_rel_error'], 2)}% → {'PASS' if sy['passed'] else 'FAIL'} (< 5%). "
          "Also covered by `tests/test_calibration.py`.", "",
          "## 6. Burned area (MCD64A1)", ""]
    ba = M.get("burned_area")
    if ba is None:
        L += ["Not run: put MCD64A1 tiles into `data/reference/mcd64a1/` (NASA Earthdata, see README).", ""]
    else:
        L += [f"MCD64A1 C6.1 burned area inside the region ({ba['tiles']} tiles, {ba['years'][0]}–{ba['years'][1]}, "
              "months with all tiles only). An independent sensor product: if harmonization holds, the link between fire "
              "counts and burned area should look the same on both sides of 2012, and fire-days per km² burned should not jump.", "",
              "| series | side | months | Spearman ρ | Pearson r (log) | per km² burned |", "|---|---|---|---|---|---|"]
        for name, rows in ba["series"].items():
            for side in ("before_2012", "from_2012"):
                r = rows[side]
                L.append(f"| {name} | {side} | {r['months']} | {fmt(r['spearman'], 3)} | {fmt(r['pearson_log'], 3)} | {fmt(r['per_km2'], 3)} |")
            L.append(f"| {name} | step after/before | | | | ×{fmt(rows['per_km2_step'], 2)} |")
        L.append("")
    L += [
          "## 7. Known events", "", "| event | year-month | value | median same month | rank (same month) | rank (all months) |",
          "|---|---|---|---|---|---|"]
    for e in M["known_events"]:
        L.append(f"| {e['name']} | {e['year']}-{e['month']:02d} | {fmt(e['value'], 0)} | {fmt(e['median_same_month'], 0)} | "
                 f"{e['rank_among_same_month']} / {e['of_years']} | {e['rank_among_all_months']} / {e['of_months']} |")
    L += ["", "## Coefficients", "", "![coefficients](coefficients.png)", "", "![raw series](raw_series.png)", ""]
    (REPORTS / "validation.md").write_text("\n".join(L), encoding="utf-8")


def main():
    ensure_dirs()
    cfg = load_config()
    cm = CAL.load_cell_month()
    harm = pd.read_parquet(AGG / "cell_month.parquet", columns=["h3_cell", "year", "month", "n_harm", "n_harm_low", "n_harm_high"])
    cm = cm.drop(columns=[c for c in ("n_harm", "n_harm_low", "n_harm_high") if c in cm]).merge(harm, on=["h3_cell", "year", "month"])
    coef_t = pd.read_parquet(AGG / "coefficients.parquet")
    dr = pd.read_parquet(AGG / "coefficient_draws.parquet")
    draws = {m: calib.draws_from_table(g) for m, g in dr.groupby("model")}
    best = coef_t.loc[coef_t["role"].eq("main") & coef_t["selected"], "model"].iloc[0]
    coefs = {r: g.drop(columns=["role", "selected"]).dropna(axis=1, how="all").reset_index(drop=True)
             for r, g in coef_t[coef_t["role"] != "main"].groupby("role")}
    for mdl, g in coef_t[coef_t["role"] == "main"].groupby("model"):
        coefs[mdl] = g.drop(columns=["role", "selected"]).dropna(axis=1, how="all").reset_index(drop=True)
    y1 = CAL.last_full_year(cm)
    M = {"selected_model": best, "last_full_year": y1}
    log.info("temporal holdout")
    M["temporal_holdout"] = temporal_holdout(cm, coefs, draws, cfg, y1, best)
    log.info("spatial CV")
    cv = spatial_cv(cm, cfg, y1)
    M["spatial_cv"] = cv.to_dict(orient="records")
    M["spatial_cv_median"] = cv.groupby("model")[["mae_pct_of_mean", "bias_total_pct", "pearson_r", "coverage"]] \
        .median().to_dict(orient="index")
    log.info("jump test")
    M["jump"] = jump_test(cm, cfg, y1)
    M["seasonality"] = seasonality(cm, cfg, y1)
    M["synthetic"] = synthetic_check(cfg)
    M["known_events"] = known_events(cm, cfg)
    M["burned_area"] = burned_area_check(cm, cfg)
    coef_plot(coef_t, best)
    write_json(REPORTS / "metrics.json", M)
    write_report(M, cfg)
    log.info("wrote reports/validation.md")


if __name__ == "__main__":
    main()

"""Model comparison per reports/model_protocol.md -> reports/model_comparison.{md,json}."""
import importlib

import h3
import numpy as np
import pandas as pd

from pipeline import calib, models
from pipeline.common import REPORTS, get_logger, load_config, write_json
from pipeline.metrics import series_metrics

log = get_logger("experiments")
CAL = importlib.import_module("pipeline.05_calibrate")


def prepare(cfg):
    cm = CAL.load_cell_month()
    n20, _ = calib.fit(cm, "n_viirs_snpp", "n_viirs_noaa20", tuple(cfg["calibration"]["noaa20_period"]), cfg,
                       intervals=False)
    cm["v_target"] = CAL.target_viirs(cm, n20)
    res = cfg["validation"]["subregion_h3_res"]
    cells = pd.DataFrame({"h3_cell": cm["h3_cell"].unique()})
    cells["sub"] = [h3.cell_to_parent(c, res) for c in cells["h3_cell"]]
    w = cm.merge(cells, on="h3_cell").groupby("sub")["n_modis"].sum()
    small = w[w / w.sum() < cfg["validation"]["subregion_min_share"]].index
    cells.loc[cells["sub"].isin(small), "sub"] = "merged_small"
    return cm.merge(cells, on="h3_cell"), CAL.last_full_year(cm)


def cols_all():
    return sorted({c for s in models.SPECS.values() for c in s["cols"]})


def run_test(spec, train, test, full, cfg):
    p = models.fit(spec, train, cfg)
    return test.assign(pred=models.predict(spec, p, test, full))


def evaluate(cm, y1, cfg):
    cols = cols_all()
    full = models.monthly_totals(cm, cols)
    yr = lambda a, b: full[full["year"].between(a, b)]  # noqa: E731
    subs = sorted(cm["sub"].unique())
    sub_tot = {s: models.monthly_totals(cm[cm["sub"] == s], cols) for s in subs}
    rest_tot = {s: models.monthly_totals(cm[cm["sub"] != s], cols) for s in subs}
    out, preds = {}, {}
    for cid, spec in models.SPECS.items():
        r = {}
        t1 = run_test(spec, yr(2016, 2019), yr(2012, 2015), full, cfg)
        r["T1_backcast"] = series_metrics(t1["v_target"], t1["pred"])
        t2 = run_test(spec, yr(2012, 2019), yr(2020, y1), full, cfg)
        r["T2_forecast"] = series_metrics(t2["v_target"], t2["pred"])
        loro = []
        for s in subs:
            tr = rest_tot[s][rest_tot[s]["year"].between(2012, 2019)]
            te = sub_tot[s][sub_tot[s]["year"].between(2012, 2019)]
            t = run_test(spec, tr, te, full, cfg)
            loro.append({"sub": s, **series_metrics(t["v_target"], t["pred"])})
        L = pd.DataFrame(loro)
        r["T3_loro"] = {"mae_pct_of_mean": float(L["mae_pct_of_mean"].median()),
                        "bias_total_pct": float(L["bias_total_pct"].median()),
                        "abs_bias_median": float(L["bias_total_pct"].abs().median()),
                        "pearson_r": float(L["pearson_r"].median()), "by_subregion": loro}
        t4 = pd.concat([run_test(spec, yr(2012, 2019)[lambda d: d["year"] != y], yr(y, y), full, cfg)
                        for y in range(2012, 2020)])
        r["T4_loyo"] = series_metrics(t4["v_target"], t4["pred"])
        r["score"] = float(np.mean([r["T1_backcast"]["mae_pct_of_mean"], r["T3_loro"]["mae_pct_of_mean"],
                                    r["T4_loyo"]["mae_pct_of_mean"]]))
        r["n_params"] = models.N_PARAMS[spec["link"]] * len(spec["cols"])
        out[cid] = r
        preds[cid] = {"T1": t1, "T4": t4}
        log.info("%s %-38s score %.2f | T1 %.1f T3 %.1f T4 %.1f | T2 %.1f bias %.1f", cid, spec["label"], r["score"],
                 r["T1_backcast"]["mae_pct_of_mean"], r["T3_loro"]["mae_pct_of_mean"],
                 r["T4_loyo"]["mae_pct_of_mean"], r["T2_forecast"]["mae_pct_of_mean"], r["T2_forecast"]["bias_total_pct"])
    return out, preds


def loyo_residuals(spec, train, full, cfg):
    """log(V / pred) for each training year predicted from the other training years."""
    rows = []
    for y in sorted(train["year"].unique()):
        t = run_test(spec, train[train["year"] != y], train[train["year"] == y], full, cfg)
        t = t[(t["v_target"] > 0) & (t["pred"] > 0)]
        rows.append(t.assign(r=np.log(t["v_target"] / t["pred"])))
    return pd.concat(rows)


def interval_bounds(method, res, test, cfg):
    lvl = cfg["calibration"]["interval_level"]
    q = [(1 - lvl) / 2, 1 - (1 - lvl) / 2]
    if method == "season":
        s = res.assign(season=res["month"].map(models.SEASONS))
        qs = s.groupby("season")["r"].quantile(q).unstack()
        lo = test["month"].map(models.SEASONS).map(qs[q[0]]).fillna(res["r"].quantile(q[0]))
        hi = test["month"].map(models.SEASONS).map(qs[q[1]]).fillna(res["r"].quantile(q[1]))
        return test["pred"] * np.exp(lo), test["pred"] * np.exp(hi)
    med = res["pred"].median()
    z = res["r"] * np.sqrt(res["pred"] / med)            # larger months -> smaller relative error
    ql, qh = z.quantile(q)
    scale = np.sqrt(med / np.maximum(test["pred"], 1e-9))
    return test["pred"] * np.exp(ql * scale), test["pred"] * np.exp(qh * scale)


def interval_check(spec, cm, cfg):
    full = models.monthly_totals(cm, cols_all())
    yr = lambda a, b: full[full["year"].between(a, b)]  # noqa: E731
    out = {}
    for method in ("season", "hetero"):
        tests = []
        tr = yr(2016, 2019)
        t = run_test(spec, tr, yr(2012, 2015), full, cfg)
        tests.append(t.assign(test="T1", lo=None, hi=None))
        tests[-1]["lo"], tests[-1]["hi"] = interval_bounds(method, loyo_residuals(spec, tr, full, cfg), t, cfg)
        for y in range(2012, 2020):
            tr = yr(2012, 2019)[lambda d: d["year"] != y]
            t = run_test(spec, tr, yr(y, y), full, cfg)
            lo, hi = interval_bounds(method, loyo_residuals(spec, tr, full, cfg), t, cfg)
            tests.append(t.assign(test="T4", lo=lo, hi=hi))
        T = pd.concat(tests)
        inside = (T["v_target"] >= T["lo"]) & (T["v_target"] <= T["hi"])
        out[method] = {"coverage": float(inside.mean()), "by_test": inside.groupby(T["test"]).mean().to_dict(),
                       "median_width_pct": float(((T["hi"] - T["lo"]) / T["pred"]).median() * 100)}
        log.info("interval %-6s coverage %.0f%% (T1 %.0f%%, T4 %.0f%%), median width %.0f%% of pred", method,
                 100 * out[method]["coverage"], 100 * out[method]["by_test"]["T1"], 100 * out[method]["by_test"]["T4"],
                 out[method]["median_width_pct"])
    target = cfg["calibration"]["interval_level"]
    out["selected"] = min(("season", "hetero"), key=lambda k: abs(out[k]["coverage"] - target))
    return out


def select(out):
    best = min(out, key=lambda c: out[c]["score"])
    close = [c for c in out if out[c]["score"] <= out[best]["score"] + 0.5]
    return min(close, key=lambda c: (out[c]["n_params"], out[c]["score"]))


def fmt(x, d=1):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def write(out, chosen):
    L = ["# Model comparison (protocol: model_protocol.md)", "",
         "MAE as % of the mean monthly total; bias = total over the test period. Score = mean MAE % of T1, T3, T4.", "",
         "| id | model | params | **score** | T1 backcast MAE / bias | T3 LORO MAE / median bias | T4 LOYO MAE / bias | T2 forecast MAE / bias (drift) |",
         "|---|---|---|---|---|---|---|---|"]
    for c, r in sorted(out.items(), key=lambda kv: kv[1]["score"]):
        L.append(f"| {c}{' ✔' if c == chosen else ''} | {models.SPECS[c]['label']} | {r['n_params']} | **{fmt(r['score'], 2)}** | "
                 f"{fmt(r['T1_backcast']['mae_pct_of_mean'])} / {fmt(r['T1_backcast']['bias_total_pct'])} | "
                 f"{fmt(r['T3_loro']['mae_pct_of_mean'])} / {fmt(r['T3_loro']['bias_total_pct'])} | "
                 f"{fmt(r['T4_loyo']['mae_pct_of_mean'])} / {fmt(r['T4_loyo']['bias_total_pct'])} | "
                 f"{fmt(r['T2_forecast']['mae_pct_of_mean'])} / {fmt(r['T2_forecast']['bias_total_pct'])} |")
    L += ["", f"Selected by the protocol rule: **{chosen}** ({models.SPECS[chosen]['label']}).", ""]
    (REPORTS / "model_comparison.md").write_text("\n".join(L), encoding="utf-8")


def main():
    cfg = load_config()
    cm, y1 = prepare(cfg)
    out, _ = evaluate(cm, y1, cfg)
    chosen = select(out)
    iv = interval_check(models.SPECS[chosen], cm, cfg)
    write_json(REPORTS / "model_comparison.json", {"selected": chosen, "results": out, "intervals": iv,
                                                   "specs": {c: s for c, s in models.SPECS.items()}})
    write(out, chosen)
    with open(REPORTS / "model_comparison.md", "a", encoding="utf-8") as f:
        f.write("## Prediction intervals for the selected model (T1 + T4)\n\n| method | coverage of 90% | T1 | T4 | "
                "median width, % of prediction |\n|---|---|---|---|---|\n")
        for m in ("season", "hetero"):
            r = iv[m]
            f.write(f"| {m}{' ✔' if m == iv['selected'] else ''} | {100 * r['coverage']:.0f}% | "
                    f"{100 * r['by_test']['T1']:.0f}% | {100 * r['by_test']['T4']:.0f}% | {r['median_width_pct']:.0f}% |\n")
    log.info("selected %s, intervals %s", chosen, iv["selected"])


if __name__ == "__main__":
    main()

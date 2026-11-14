"""Phase B: our run vs the baseline (Elbek) numbers -> reports/reproduction.md + reports/reproduction.json.

Reads reports/{metrics,model_comparison}.json (ours) and reports/baseline/ (his), plus the Terra/Aqua yearly
cell-day ratio computed here from data/aggregated/cell_month.parquet (his README quotes it, his code never computed it).

    python -m pipeline.compare_baseline
"""
import json

import pandas as pd

from pipeline.common import AGG, REPORTS, load_config, write_json

TOL_PCT = 2.0


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def headline(M, MC):
    j, h = M["jump"], M["temporal_holdout"]["holdout"][M["selected_model"]]
    t1 = MC["results"][MC["selected"]]["T1_backcast"]
    return {
        "naive points step": j["naive_points"]["step_ratio"],
        "naive cell-day step": j["naive_cell_days"]["step_ratio"],
        "MODIS-only step": j["modis_only_reference"]["step_ratio"],
        "harmonized step": j["harmonized"]["step_ratio"],
        "monthly step regression, naive": j["naive_points"]["monthly_step"]["step_factor"],
        "monthly step regression, harmonized": j["harmonized"]["monthly_step"]["step_factor"],
        "backcast MAE % (T1)": t1["mae_pct_of_mean"],
        "holdout MAE %": h["mae_pct_of_mean"],
        "holdout bias %": h["bias_total_pct"],
        "holdout Pearson R": h["pearson_r"],
        "LORO median MAE %": M["spatial_cv_median"][M["selected_model"]]["mae_pct_of_mean"],
        "LORO interval coverage": M["spatial_cv_median"][M["selected_model"]]["coverage"],
    }


def terra_aqua(years=(2003, 2021)):
    cm = pd.read_parquet(AGG / "cell_month.parquet", columns=["year", "n_modis_terra", "n_modis_aqua"])
    y = cm.groupby("year")[["n_modis_terra", "n_modis_aqua"]].sum()
    y = y[y["n_modis_aqua"] > 0]
    r = (y["n_modis_terra"] / y["n_modis_aqua"])
    win = r.loc[years[0]:years[1]]
    return {"by_year": {int(k): float(v) for k, v in r.items()},
            "range": [float(win.min()), float(win.max())], "years": list(years)}


def main():
    cfg = load_config()
    ours = headline(_load(REPORTS / "metrics.json"), _load(REPORTS / "model_comparison.json"))
    his = headline(_load(REPORTS / "baseline" / "metrics.json"), _load(REPORTS / "baseline" / "model_comparison.json"))
    ta = terra_aqua()
    rows = []
    for k in ours:
        a, b = his[k], ours[k]
        d = 100 * (b / a - 1) if a else None
        rows.append({"metric": k, "his": a, "ours": b, "diff_pct": d,
                     "flag": d is not None and abs(d) > TOL_PCT})
    rows.append({"metric": "Terra/Aqua cell-day ratio 2003–2021 (min)", "his": 0.86, "ours": ta["range"][0],
                 "diff_pct": 100 * (ta["range"][0] / 0.86 - 1), "flag": abs(ta["range"][0] / 0.86 - 1) > TOL_PCT / 100})
    rows.append({"metric": "Terra/Aqua cell-day ratio 2003–2021 (max)", "his": 1.02, "ours": ta["range"][1],
                 "diff_pct": 100 * (ta["range"][1] / 1.02 - 1), "flag": abs(ta["range"][1] / 1.02 - 1) > TOL_PCT / 100})
    write_json(REPORTS / "reproduction.json", {"region": cfg["region"]["name"], "rows": rows, "terra_aqua": ta,
                                               "tolerance_pct": TOL_PCT})
    L = [f"# Reproduction of the baseline — {cfg['region']['name']}", "",
         f"His numbers: `reports/baseline/`. Ours: `reports/`. Flag = difference > {TOL_PCT:.0f}%.", "",
         "| metric | his | ours | diff % | > 2% |", "|---|---|---|---|---|"]
    for r in rows:
        d = "—" if r["diff_pct"] is None else f"{r['diff_pct']:+.2f}"
        L.append(f"| {r['metric']} | {r['his']:.3f} | {r['ours']:.3f} | {d} | {'⚠' if r['flag'] else ''} |")
    L += ["", "Terra/Aqua cell-day ratio by year (ours):", "", "| year | Terra / Aqua |", "|---|---|"]
    L += [f"| {y} | {v:.3f} |" for y, v in ta["by_year"].items()]
    (REPORTS / "reproduction.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:len(rows) + 5]))


if __name__ == "__main__":
    main()

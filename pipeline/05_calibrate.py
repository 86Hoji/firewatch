"""Fit MODIS->VIIRS S-NPP coefficients (ratio and log-log), choose model on the temporal holdout."""
import numpy as np
import pandas as pd

from pipeline import calib
from pipeline.common import AGG, REF, REPORTS, ensure_dirs, get_logger, load_config, write_json
from pipeline.metrics import series_metrics

log = get_logger("calibrate")


def load_cell_month():
    cm = pd.read_parquet(AGG / "cell_month.parquet")
    lc = REF / "landcover_cells.parquet"
    cm = cm.drop(columns=[c for c in ("land_cover",) if c in cm])
    if lc.exists():
        cm = cm.merge(pd.read_parquet(lc)[["h3_cell", "land_cover"]], on="h3_cell", how="left")
        cm["land_cover"] = cm["land_cover"].fillna("other")
        log.info("land cover strata: %s", sorted(cm["land_cover"].unique()))
    else:
        cm["land_cover"] = "all"
        log.info("no land cover file, strata = month/season/region")
    return cm


def last_full_year(cm):
    last = cm[["year", "month"]].drop_duplicates().sort_values(["year", "month"]).iloc[-1]
    return int(last["year"]) if int(last["month"]) == 12 else int(last["year"]) - 1


def target_viirs(cm, noaa20_coef):
    return cm["n_viirs_snpp"] + calib.predict(cm, "n_viirs_noaa20_gap", noaa20_coef)["pred"]


def fit_all(cm, cfg, years=None, totals=None):
    """totals: whole-region MODIS totals per (land_cover, year, month) — input data, so legal at prediction time."""
    c = cfg["calibration"]
    years = years or tuple(c["period"])
    coefs, draws = {}, {}
    coefs["terra"], _ = calib.fit(cm, "n_modis", "n_modis_terra", tuple(c["terra_aqua_period"]), cfg, intervals=False)
    coefs["noaa20"], _ = calib.fit(cm, "n_viirs_snpp", "n_viirs_noaa20", tuple(c["noaa20_period"]), cfg, intervals=False)
    cm = cm.assign(v_target=target_viirs(cm, coefs["noaa20"]))
    for model in c["models"]:
        coefs[model], draws[model] = calib.fit(cm, "v_target", "n_modis", years, cfg, model=model, totals=totals)
    return coefs, draws


def holdout_eval(cm, coefs, draws, cfg, y1):
    y0 = cfg["calibration"]["holdout_start"]
    totals = calib.regional_totals(cm, "n_modis")
    h = cm[cm["year"].between(y0, y1)].copy()
    h["actual"] = target_viirs(h, coefs["noaa20"])
    res = {}
    for model in cfg["calibration"]["models"]:
        p = calib.predict(h, "n_modis", coefs[model], totals=totals, draws=draws[model], cfg=cfg)
        m = pd.concat([h[["year", "month", "actual"]], p], axis=1).groupby(["year", "month"]).sum()
        res[model] = series_metrics(m["actual"], m["pred"], m["low"], m["high"])
        res[model]["coverage_ci"] = float(np.mean((m["actual"] >= m["ci_low"]) & (m["actual"] <= m["ci_high"])))
    return res


def main():
    ensure_dirs()
    cfg = load_config()
    cm = load_cell_month()
    y1 = last_full_year(cm)
    coefs, draws = fit_all(cm, cfg)
    ho = holdout_eval(cm, coefs, draws, cfg, y1)
    v1 = min(ho, key=lambda k: ho[k]["mae_pct_of_mean"])
    best = cfg["calibration"].get("selected_model") or v1
    for k, v in ho.items():
        log.info("holdout %s: MAE%%=%.1f bias=%.1f%% R=%.3f PI cov=%.0f%% CI cov=%.0f%%", k, v["mae_pct_of_mean"],
                 v["bias_total_pct"], v["pearson_r"], 100 * v["coverage"], 100 * v["coverage_ci"])
    log.info("selected model: %s", best)
    tables = [coefs[m].assign(role="main", selected=m == best) for m in cfg["calibration"]["models"]]
    tables += [coefs[r].assign(role=r, selected=True) for r in ("terra", "noaa20")]
    pd.concat(tables, ignore_index=True).to_parquet(AGG / "coefficients.parquet", index=False)
    rows = [pd.DataFrame({"model": m, "draw_key": k, "d0": v[:, 0], "d1": v[:, 1]})
            for m, dd in draws.items() for k, v in dd.items() if len(v)]
    pd.concat(rows, ignore_index=True).to_parquet(AGG / "coefficient_draws.parquet", index=False)
    write_json(REPORTS / "model_selection.json", {
        "criterion": "v2: reports/model_protocol.md (backcast, LORO, LOYO); v1: holdout MAE % of mean",
        "holdout_years": [cfg["calibration"]["holdout_start"], y1], "results": ho,
        "selected": best, "v1_choice": v1, "interval_method": cfg["calibration"].get("interval_method", "season")})


if __name__ == "__main__":
    main()

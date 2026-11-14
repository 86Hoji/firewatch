"""Apply selected coefficients: 2000-2011 MODIS -> S-NPP equivalent, 2012+ S-NPP (+NOAA-20 outage fill).

Intervals (C3): n_harm_low/high per cell-month = the region-level interval applied to THAT cell-month alone.
Do not add them up over cells: for any area, sum n_harm and apply intervals.bounds(sum, params) with
params = intervals.country for the whole country and intervals.region for anything smaller
(parameters in meta.json / reports/model_card.json).
"""
import datetime as dt
import importlib

import duckdb
import pandas as pd

from pipeline import calib, intervals
from pipeline.common import AGG, PROCESSED, ensure_dirs, get_logger, load_config, write_json

log = get_logger("harmonize")
CAL = importlib.import_module("pipeline.05_calibrate")


def main():
    ensure_dirs()
    cfg = load_config()
    cm = CAL.load_cell_month()
    coefs = calib.coefs_from_table(pd.read_parquet(AGG / "coefficients.parquet"))
    model = coefs["main"]["model"].iloc[0]
    d = pd.read_parquet(AGG / "coefficient_draws.parquet")
    draws = calib.draws_from_table(d[d["model"] == model])
    out = calib.harmonize(cm, coefs, cfg, draws=draws)
    card = CAL.read_model_card()
    if card["production_model"] != model:
        raise SystemExit(f"coefficients are for {model} but model_card says {card['production_model']}: rerun 05")
    iv = card["intervals"]
    pre = out["source"].eq("MODIS_calibrated").to_numpy()
    lo, hi = intervals.bounds(out.loc[pre, "n_harm"], iv["region"])
    out.loc[pre, "n_harm_low"], out.loc[pre, "n_harm_high"] = lo, hi
    out.to_parquet(AGG / "cell_month.parquet", index=False)
    src = (f"read_parquet('{(PROCESSED / 'hotspots' / ('country=' + cfg['train_country'])).as_posix()}/**/*.parquet', "
           "hive_partitioning = true)")
    first, last = duckdb.connect().execute(f"SELECT min(date), max(date) FROM {src}").fetchall()[0]
    write_json(AGG / "meta.json", {
        "region": cfg["region"]["name"], "first_date": first, "last_date": last, "model": model,
        "h3_res": cfg["grid"]["h3_res"], "calibration_period": cfg["calibration"]["period"],
        "country": cfg["train_country"], "selected": card["selected"],
        "intervals": {k: iv[k] for k in ("level", "country", "region")},
        "updated": dt.datetime.now().isoformat(timespec="seconds"),
        "coef_version": pd.Timestamp.now().strftime("%Y%m%d%H%M")})
    pre = out[out["year"] < cfg["calibration"]["period"][0]]
    log.info("cell-months in: %d, out: %d; pre-2012 MODIS %d -> harmonized %.0f", len(cm), len(out),
             pre["n_modis"].sum(), pre["n_harm"].sum())


if __name__ == "__main__":
    main()

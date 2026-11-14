"""Apply selected coefficients: 2000-2011 MODIS -> S-NPP equivalent, 2012+ S-NPP (+NOAA-20 outage fill)."""
import datetime as dt
import importlib

import duckdb
import pandas as pd

from pipeline import calib
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
    out.to_parquet(AGG / "cell_month.parquet", index=False)
    src = (f"read_parquet('{(PROCESSED / 'hotspots' / ('country=' + cfg['train_country'])).as_posix()}/**/*.parquet', "
           "hive_partitioning = true)")
    first, last = duckdb.connect().execute(f"SELECT min(date), max(date) FROM {src}").fetchall()[0]
    write_json(AGG / "meta.json", {
        "region": cfg["region"]["name"], "first_date": first, "last_date": last, "model": model,
        "h3_res": cfg["grid"]["h3_res"], "calibration_period": cfg["calibration"]["period"],
        "updated": dt.datetime.now().isoformat(timespec="seconds"),
        "coef_version": pd.Timestamp.now().strftime("%Y%m%d%H%M")})
    pre = out[out["year"] < cfg["calibration"]["period"][0]]
    log.info("cell-months in: %d, out: %d; pre-2012 MODIS %d -> harmonized %.0f [%.0f, %.0f]", len(cm), len(out),
             pre["n_modis"].sum(), pre["n_harm"].sum(), pre["n_harm_low"].sum(), pre["n_harm_high"].sum())


if __name__ == "__main__":
    main()

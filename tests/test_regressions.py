"""Cases found by mutation testing (each mutation used to pass the suite). SYNTHETIC data only."""
import importlib

import duckdb
import h3
import numpy as np
import pandas as pd

from pipeline import calib
from tests.conftest import synthetic_cell_month

clean = importlib.import_module("pipeline.02_clean")
grid = importlib.import_module("pipeline.03_grid")


def test_step_test_finds_artificial_jump_and_not_a_trend():
    from pipeline.metrics import step_test
    rng = np.random.default_rng(0)
    yrs, mo = np.repeat(np.arange(2003, 2020), 12), np.tile(np.arange(1, 13), 17)
    base = np.exp(3 + 2 * np.sin(mo / 12 * 2 * np.pi) - 0.02 * (yrs - 2003))
    assert step_test(yrs, mo, rng.poisson(base), 2012)["ci_includes_1"]
    jump = step_test(yrs, mo, rng.poisson(base * np.where(yrs >= 2012, 3, 1)), 2012)
    assert not jump["ci_includes_1"] and jump["step_factor"] > 2


def test_poisson_multiplier_matches_model_formula(cfg):
    cm = synthetic_cell_month({"all": 3.0}, cells=150)
    coef, _ = calib.fit(cm, "n_viirs_snpp", "n_modis", (2012, 2019), cfg, model="poisson_log", intervals=False)
    p = calib.predict(cm, "n_modis", coef)
    tot = cm.assign(pred=p["pred"]).groupby(["year", "month"])[["n_modis", "pred"]].sum().reset_index()
    c = coef.set_index("month")
    expected = np.exp(c.loc[tot["month"], "a"].to_numpy() + c.loc[tot["month"], "b"].to_numpy() * np.log1p(tot["n_modis"]))
    assert np.allclose(tot["pred"], expected, rtol=1e-9)


def test_terra_only_months_are_scaled_to_terra_plus_aqua(cfg):
    df = pd.DataFrame({"h3_cell": ["a", "a"], "year": [2001, 2005], "month": [7, 7],
                       "n_modis": [10, 10], "n_modis_terra": [10, 6]})
    terra = pd.DataFrame({"land_cover": ["all"] * 12, "month": range(1, 13), "k": [1.7] * 12, "model": "ratio"})
    m = calib.modis_effective(df, terra, cfg)
    assert m[0] == 17.0          # 2001: Terra only -> scaled
    assert m[1] == 10.0          # 2005: Terra+Aqua as observed


def test_outage_fill_uses_global_days_and_skips_cells_snpp_saw(tmp_path):
    rows = [("c1", "2026-11-05", "NOAA20"), ("c2", "2026-11-05", "NOAA20"), ("c2", "2026-11-05", "SNPP"),
            ("c3", "2026-11-06", "NOAA20")]                       # 11-06 is not an outage day
    df = pd.DataFrame(rows, columns=["h3_cell", "date", "platform"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["year"], df["month"] = 2026, 11
    p = tmp_path / "h.parquet"
    df.to_parquet(p)
    gap, n_days = grid.outage_fill(duckdb.connect(), f"read_parquet('{p.as_posix()}')",
                                   [pd.Timestamp("2026-11-05").date()])
    assert n_days == 1
    assert gap.set_index("h3_cell")["n_viirs_noaa20_gap"].to_dict() == {"c1": 1}   # c2 already has S-NPP


def test_global_outage_rule():
    from pipeline import outage
    cfg = {"outage": {"max_snpp_share": 0.01, "min_noaa20_total": 500}}
    d = pd.DataFrame({"date": pd.to_datetime(["2026-01-01"] * 2 + ["2026-01-02"] * 2 + ["2026-01-03"] * 2),
                      "country": ["A", "B"] * 3,
                      "n_snpp": [0, 0, 3, 0, 0, 0], "n_noaa20": [900, 5, 900, 5, 100, 50]})
    days, _ = outage.global_days(cfg, d)
    # day 1: S-NPP 0 vs 905 -> outage; day 2: 3/905 = 0.3% -> outage; day 3: too few NOAA-20 to tell
    assert days["date"].dt.strftime("%m-%d").tolist() == ["01-01", "01-02"]


def test_standard_processing_replaces_nrt_on_same_day():
    df = pd.DataFrame({"platform": ["SNPP", "SNPP", "SNPP"], "processing": ["SP", "NRT", "NRT"],
                       "date": pd.to_datetime(["2026-07-01", "2026-07-01", "2026-08-01"]).date})
    out = clean.drop_nrt_overlap(df)
    assert list(zip(out["processing"], out["date"].astype(str))) == [("SP", "2026-07-01"), ("NRT", "2026-08-01")]


def test_static_mask_removes_nrt_detections_at_flares(cfg):
    flare, field = (47.10, 51.90), (52.0, 64.0)
    n = 12
    rows = {"sensor": ["VIIRS"] * (n + 2), "platform": ["SNPP"] * (n + 2),
            "lat": [flare[0]] * (n + 1) + [field[0]], "lon": [flare[1]] * (n + 1) + [field[1]],
            "datetime_utc": pd.date_range("2025-01-01", periods=n + 2, freq="D"),
            "confidence": ["n"] * (n + 2), "confidence_norm": ["n"] * (n + 2), "frp": [5.0] * (n + 2),
            "type": [2.0] * n + [np.nan, np.nan], "processing": ["SP"] * n + ["NRT", "NRT"], "daynight": ["N"] * (n + 2)}
    df = pd.DataFrame(rows)
    df["date"] = df["datetime_utc"].dt.date
    out, mask = clean.clean(df, cfg, [])
    assert h3.latlng_to_cell(*flare, cfg["grid"]["h3_res"]) in set(mask["h3_cell"])
    assert len(out) == 1 and out["lat"].iloc[0] == field[0]   # NRT at the flare dropped, field fire kept

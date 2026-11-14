"""Candidate models on SYNTHETIC monthly totals with known parameters."""
import numpy as np
import pandas as pd

from pipeline import calib, models
from tests.conftest import synthetic_cell_month


def power_law_totals(a=1.2, b=0.85, years=range(2012, 2020), seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for y in years:
        for m in range(1, 13):
            M = rng.integers(50, 20000)
            rows.append((y, m, M, rng.poisson(np.exp(a) * (M + 1) ** b)))
    return pd.DataFrame(rows, columns=["year", "month", "n_modis", "v_target"])


def test_poisson_log_link_recovers_power_law():
    t = power_law_totals()
    a, b = models.fit_rows("log", t[["n_modis"]].to_numpy(float), t["v_target"].to_numpy(float))
    assert abs(a - 1.2) < 0.05 and abs(b - 0.85) < 0.01


def test_identity_two_predictors_recovers_day_night_weights():
    rng = np.random.default_rng(2)
    X = rng.integers(100, 5000, size=(200, 2)).astype(float)
    v = rng.poisson(X @ np.array([2.0, 6.0]))
    k = models.fit_rows("identity", X, v.astype(float))
    assert np.allclose(k, [2.0, 6.0], rtol=0.03)


def test_log_link_multiplier_applies_to_subareas_additively(cfg):
    t = power_law_totals()
    p = models.fit({"cols": ["n_modis"], "link": "log"}, t, cfg)
    half = t.assign(n_modis=t["n_modis"] / 2)
    whole = models.predict({"cols": ["n_modis"], "link": "log"}, p, t)
    parts = 2 * models.predict({"cols": ["n_modis"], "link": "log"}, p, half, full=t)
    assert np.allclose(whole, parts)


def test_calib_poisson_log_and_hetero_interval(cfg):
    cfg["calibration"]["interval_method"] = "hetero"
    cm = synthetic_cell_month({"forest": 3.0}, years=range(2012, 2024), cells=120)
    coef, draws = calib.fit(cm, "n_viirs_snpp", "n_modis", (2012, 2019), cfg, model="poisson_log")
    assert {"a", "b", "pi_lo", "pi_hi", "pi_med"} <= set(coef.columns)
    h = cm[cm["year"] >= 2020]
    p = calib.predict(h, "n_modis", coef, draws=draws, cfg=cfg)
    m = h.assign(**p).groupby(["year", "month"])[["n_viirs_snpp", "n_modis", "pred", "low", "high"]].sum()
    assert abs(m["pred"].sum() / m["n_modis"].sum() / 3.0 - 1) < 0.05
    assert ((m["n_viirs_snpp"] >= m["low"]) & (m["n_viirs_snpp"] <= m["high"])).mean() >= 0.75

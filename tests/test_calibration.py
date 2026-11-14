import numpy as np

from pipeline import calib
from tests.conftest import synthetic_cell_month


def test_ratio_recovers_known_coefficients(cfg):
    cm = synthetic_cell_month({"forest": 3.2, "steppe": 2.1})
    coef, _ = calib.fit(cm, "n_viirs_snpp", "n_modis", (2012, 2019), cfg)
    for lc, k_true in {"forest": 3.2, "steppe": 2.1}.items():
        k = coef.loc[coef["land_cover"] == lc, "k"]
        assert np.all(np.abs(k / k_true - 1) < 0.05), (lc, k.tolist())
        assert (coef.loc[coef["land_cover"] == lc, "stratum_level"] == "land_cover_month").all()


def test_loglog_recovers_scale(cfg):
    cm = synthetic_cell_month({"forest": 3.2, "steppe": 2.1})
    coef, _ = calib.fit(cm, "n_viirs_snpp", "n_modis", (2012, 2019), cfg, model="loglog")
    p = calib.predict(cm, "n_modis", coef)
    for lc, k_true in {"forest": 3.2, "steppe": 2.1}.items():
        sel = cm["land_cover"] == lc
        ratio = p.loc[sel, "pred"].sum() / cm.loc[sel, "n_modis"].sum()
        assert abs(ratio / k_true - 1) < 0.05, (lc, ratio)


def test_fallback_to_coarser_stratum_when_sparse(cfg):
    cm = synthetic_cell_month({"forest": 3.0}, cells=40, sparse_month=1)
    cfg["calibration"]["min_count"] = 50
    coef, _ = calib.fit(cm, "n_viirs_snpp", "n_modis", (2012, 2019), cfg)
    jan = coef[coef["month"] == 1].iloc[0]
    jul = coef[coef["month"] == 7].iloc[0]
    assert jan["stratum_level"] != "land_cover_month"
    assert jul["stratum_level"] == "land_cover_month"


def test_bootstrap_interval_brackets_point_estimate(cfg):
    cm = synthetic_cell_month({"forest": 3.2})
    coef, _ = calib.fit(cm, "n_viirs_snpp", "n_modis", (2012, 2019), cfg)
    assert (coef["k_p05"] <= coef["k"]).all() and (coef["k"] <= coef["k_p95"]).all()
    assert (coef["pi_lo"] < 0).all() and (coef["pi_hi"] > 0).all()


def test_harmonize_switches_source_at_2012(cfg):
    cm = synthetic_cell_month({"forest": 3.0}, years=range(2008, 2016))
    coefs = {"main": calib.fit(cm, "n_viirs_snpp", "n_modis", (2012, 2015), cfg)[0],
             "terra": calib.fit(cm, "n_modis", "n_modis_terra", (2008, 2011), cfg, intervals=False)[0],
             "noaa20": calib.fit(cm.assign(n_viirs_noaa20=cm["n_viirs_snpp"]), "n_viirs_snpp",
                                 "n_viirs_noaa20", (2012, 2015), cfg, intervals=False)[0]}
    h = calib.harmonize(cm, coefs, cfg)
    assert (h.loc[h["year"] < 2012, "source"] == "MODIS_calibrated").all()
    assert (h.loc[h["year"] >= 2012, "n_harm"] == h.loc[h["year"] >= 2012, "n_viirs_snpp"]).all()
    pre = h[h["year"] < 2012]
    assert abs(pre["n_harm"].sum() / pre["n_modis"].sum() / 3.0 - 1) < 0.05


def test_ratio_is_additive_over_areas(cfg):
    cm = synthetic_cell_month({"forest": 3.0})
    coef, _ = calib.fit(cm, "n_viirs_snpp", "n_modis", (2012, 2019), cfg, intervals=False)
    half = cm["h3_cell"].str[-1].isin(list("02468"))
    whole = calib.predict(cm, "n_modis", coef)["pred"].sum()
    parts = calib.predict(cm[half], "n_modis", coef)["pred"].sum() + calib.predict(cm[~half], "n_modis", coef)["pred"].sum()
    assert abs(whole - parts) < 1e-6 * whole


def test_conformal_interval_covers_synthetic_holdout(cfg):
    cm = synthetic_cell_month({"forest": 3.0}, years=range(2012, 2024), cells=120)
    coef, _ = calib.fit(cm, "n_viirs_snpp", "n_modis", (2012, 2019), cfg)
    h = cm[cm["year"] >= 2020]
    p = calib.predict(h, "n_modis", coef)
    m = h.assign(**p).groupby(["year", "month"])[["n_viirs_snpp", "low", "high"]].sum()
    cov = ((m["n_viirs_snpp"] >= m["low"]) & (m["n_viirs_snpp"] <= m["high"])).mean()
    assert cov >= 0.75, cov

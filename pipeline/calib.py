"""Calibration core: MODIS -> VIIRS S-NPP equivalent (cell-days), shared by pipeline, validation and tests.

Models (fit on regional stratum totals per (land_cover, year, month)):
  ratio:        V = k * M                        (k = sum V / sum M, scale-invariant)
  loglog:       log1p(V) = a + b * log1p(M), OLS + smearing (v1)
  poisson_log:  E[V] = exp(a) * (M + 1)^b, Poisson MLE (v2, chosen by reports/model_protocol.md)
Non-linear models set a multiplier from the regional monthly total. Intervals: bootstrap over years for coefficients
(CI); leave-one-year-out conformal residuals for prediction (PI), per season or heteroscedastic.
"""
import numpy as np
import pandas as pd

from pipeline import models
from pipeline.common import SEASONS

LEVELS = ["land_cover_month", "land_cover_season", "land_cover", "region"]
LEVEL_KEYS = {"land_cover_month": ["land_cover", "month"], "land_cover_season": ["land_cover", "season"],
              "land_cover": ["land_cover"], "region": []}


def with_strata(df):
    df = df.copy()
    if "land_cover" not in df:
        df["land_cover"] = "all"
    df["season"] = df["month"].map(SEASONS)
    return df


def stratum_year_sums(cm, v_col, m_col, years):
    d = with_strata(cm[cm["year"].between(*years)])
    g = d.groupby(["land_cover", "year", "month"], as_index=False)[[v_col, m_col]].sum()
    g = g.rename(columns={v_col: "V", m_col: "M"})
    g["season"] = g["month"].map(SEASONS)
    return g


def _q(cfg):
    lvl = cfg["calibration"]["interval_level"]
    return (1 - lvl) / 2, 1 - (1 - lvl) / 2


def _groups(ys, keys):
    return ys.groupby(keys) if keys else [((), ys)]


def _point(model, M, V):
    """Point fit on one stratum -> (params, bootstrap tuple), or (None, None) when not estimable."""
    if model == "ratio":
        return ({"k": V.sum() / M.sum()}, (V.sum() / M.sum(), 0.0)) if M.sum() > 0 else (None, None)
    if len(M) < 3 or np.ptp(M) == 0:
        return None, None
    if model == "loglog":
        a, b, smear = models.fit_rows("ols_log1p", M[:, None], V)
    else:
        (a, b), smear = models.fit_rows("log", M[:, None], V), 1.0
    return {"a": a, "b": b, "smear": smear}, (a, b)


def _boot_years(rng, years, n):
    return [rng.choice(years, len(years), replace=True) for _ in range(n)]


def _fit_level(ys, level, model, n_boot, rng):
    keys = LEVEL_KEYS[level]
    years = np.sort(ys["year"].unique())
    picks = _boot_years(rng, years, n_boot)
    rows, draws = [], {}
    for key, g in _groups(ys, keys):
        key = key if isinstance(key, tuple) else (key,)
        r = {"stratum_level": level, "n_obs": float(g["M"].sum()), "v_obs": float(g["V"].sum()),
             "n_points": len(g), "n_years": int((g.groupby("year")["M"].sum() > 0).sum()),
             "m_typical": float(g.loc[g["M"] > 0, "M"].median()) if (g["M"] > 0).any() else np.nan}
        r.update(dict(zip(keys, key)))
        gy, M, V = g["year"].to_numpy(), g["M"].to_numpy(float), g["V"].to_numpy(float)
        params, _ = _point(model, M, V)
        r.update(params or ({"k": np.nan} if model == "ratio" else {}))
        d = []
        for p in picks:
            idx = np.concatenate([np.flatnonzero(gy == yy) for yy in p])
            _, draw = _point(model, M[idx], V[idx])
            if draw is not None:
                d.append(draw)
        r["draw_key"] = f"{level}|{'|'.join(map(str, key))}"
        draws[r["draw_key"]] = np.array(d) if d else np.empty((0, 2))
        rows.append(r)
    return pd.DataFrame(rows), draws


def _resolve(per_level, land_covers, ok_fn):
    """Finest stratum that passes ok_fn for every (land_cover, month)."""
    out = []
    for lc in land_covers:
        for m in range(1, 13):
            probe = {"land_cover": lc, "month": m, "season": SEASONS[m]}
            for level in LEVELS:
                t = per_level[level]
                sel = np.ones(len(t), bool)
                for k in LEVEL_KEYS[level]:
                    sel &= (t[k] == probe[k]).to_numpy()
                hit = t[sel]
                if len(hit) and (ok_fn(hit.iloc[0]) or level == "region"):
                    row = hit.iloc[0].to_dict()
                    row.update(probe)
                    out.append(row)
                    break
    return pd.DataFrame(out)


def _multiplier(model, row_or_df, m_tot, a=None, b=None):
    """Effective VIIRS/MODIS multiplier at regional monthly MODIS total m_tot."""
    if model == "ratio":
        return row_or_df["k"] if a is None else a
    a = row_or_df["a"] if a is None else a
    b = row_or_df["b"] if b is None else b
    mt = np.maximum(m_tot, 1e-9)
    if model == "poisson_log":
        return np.exp(a + b * np.log1p(mt)) / mt
    return np.maximum(np.exp(a + b * np.log1p(mt)) * row_or_df["smear"] - 1, 0) / mt


def fit_point(cm, v_col, m_col, years, cfg, model="ratio", n_boot=None, seed=None):
    """Fit one model; returns (coef table per (land_cover, month), bootstrap draws by draw_key)."""
    c = cfg["calibration"]
    rng = np.random.default_rng(c["bootstrap_seed"] if seed is None else seed)
    n_boot = c["bootstrap_iter"] if n_boot is None else n_boot
    ys = stratum_year_sums(cm, v_col, m_col, years)
    per_level, draws = {}, {}
    for lv in LEVELS:
        per_level[lv], d = _fit_level(ys, lv, model, n_boot, rng)
        draws.update(d)
    if model == "ratio":
        ok = lambda r: r["n_obs"] >= c["min_count"] and np.isfinite(r["k"])  # noqa: E731
    else:
        ok = lambda r: (r["n_obs"] >= c["min_count"] and r["n_points"] >= c["loglog_min_points"]  # noqa: E731
                        and np.isfinite(r.get("a", np.nan)))
    coef = _resolve(per_level, sorted(ys["land_cover"].unique()), ok)
    coef["model"] = model
    lo, hi = _q(cfg)
    # coefficient CI, reported as a multiplier at the stratum's typical monthly total
    ks, k05, k50, k95 = [], [], [], []
    for _, r in coef.iterrows():
        d = draws[r["draw_key"]]
        k = float(_multiplier(model, r, r["m_typical"]))
        kb = d[:, 0] if model == "ratio" else np.array([_multiplier(model, r, r["m_typical"], a, b) for a, b in d])
        ks.append(k)
        q = np.quantile(kb, [lo, .5, hi]) if len(kb) else [np.nan] * 3
        k05.append(q[0]); k50.append(q[1]); k95.append(q[2])
    coef["k"], coef["k_p05"], coef["k_p50"], coef["k_p95"] = ks, k05, k50, k95
    keep = {k: draws[k] for k in coef["draw_key"].unique()}
    return coef, keep


def regional_totals(df, m_col):
    d = with_strata(df)
    return d.groupby(["land_cover", "year", "month"], as_index=False)[m_col].sum().rename(columns={m_col: "M_tot"})


def predict(df, m_col, coef, totals=None, draws=None, cfg=None):
    """MODIS-like counts in m_col -> VIIRS S-NPP equivalent.

    totals: regional MODIS totals per (land_cover, year, month) that set the log-log multiplier;
            defaults to totals of df itself. Production and validation pass whole-region totals.
    Returns pred, low/high (prediction interval), ci_low/ci_high (coefficient CI, if draws given), weight.
    """
    d = with_strata(df)
    model = coef["model"].iloc[0]
    cols = [c for c in coef.columns if c not in ("season", "stratum_level", "n_obs", "model", "v_obs", "n_points", "n_years")]
    d = d.merge(coef[cols], on=["land_cover", "month"], how="left")
    if totals is None:
        totals = regional_totals(df, m_col)
    d = d.merge(totals, on=["land_cover", "year", "month"], how="left")
    m = d[m_col].to_numpy(float)
    w = np.asarray(_multiplier(model, d, d["M_tot"].to_numpy(float)), float)
    pred = m * w
    out = pd.DataFrame({"pred": pred, "weight": w}, index=df.index)
    if "pi_lo" in d:
        lo, hi = d["pi_lo"].to_numpy(float), d["pi_hi"].to_numpy(float)
        if "pi_med" in d:   # heteroscedastic: relative width shrinks with the regional monthly prediction
            scale = np.sqrt(d["pi_med"].to_numpy(float) / np.maximum(w * d["M_tot"].to_numpy(float), 1e-9))
            lo, hi = lo * scale, hi * scale
        has = pred > 0          # nothing predicted -> zero-width interval, not 0 * inf
        out["low"] = np.where(has, pred * np.exp(np.where(has, lo, 0)), 0.0)
        out["high"] = np.where(has, pred * np.exp(np.where(has, hi, 0)), 0.0)
    if draws is not None and cfg is not None:
        lo, hi = _q(cfg)
        ci_lo, ci_hi = np.full(len(d), np.nan), np.full(len(d), np.nan)
        keyed = d[["draw_key", "M_tot"]].assign(_i=np.arange(len(d)))
        for (dk, mt), g in keyed.groupby(["draw_key", "M_tot"]):
            dr = draws.get(dk)
            if dr is None or not len(dr):
                continue
            r = d.iloc[g["_i"].iloc[0]]
            kb = dr[:, 0] if model == "ratio" else _multiplier(model, r, mt, dr[:, 0], dr[:, 1])
            ql, qh = np.quantile(kb, [lo, hi])
            ci_lo[g["_i"]], ci_hi[g["_i"]] = ql, qh
        out["ci_low"], out["ci_high"] = m * ci_lo, m * ci_hi
    return out


def loyo_intervals(cm, v_col, m_col, years, cfg, model, totals=None):
    """Leave-one-year-out conformal residuals log(actual/pred) on regional monthly totals.

    interval_method 'season': quantiles per (land_cover, season).
    interval_method 'hetero': residuals scaled by sqrt(pred / median pred), quantiles per land_cover; pi_med stored.
    """
    lo, hi = _q(cfg)
    res = []
    for y in range(years[0], years[1] + 1):
        coef, _ = fit_point(cm[cm["year"] != y], v_col, m_col, years, cfg, model, n_boot=0)
        test = cm[cm["year"] == y]
        if test.empty:
            continue
        p = predict(test, m_col, coef, totals=totals)
        g = pd.concat([with_strata(test)[["land_cover", "year", "month", v_col]], p["pred"]], axis=1) \
            .groupby(["land_cover", "year", "month"], as_index=False)[[v_col, "pred"]].sum()
        g = g[(g[v_col] > 0) & (g["pred"] > 0)]
        g["r"] = np.log(g[v_col] / g["pred"])
        res.append(g)
    r = pd.concat(res)
    r["season"] = r["month"].map(SEASONS)
    if cfg["calibration"].get("interval_method", "hetero") == "hetero":
        med = r.groupby("land_cover")["pred"].transform("median")
        r["z"] = r["r"] * np.sqrt(r["pred"] / med)
        q = r.groupby("land_cover")["z"].quantile([lo, hi]).unstack()
        q.columns = ["pi_lo", "pi_hi"]
        q["pi_med"] = r.groupby("land_cover")["pred"].median()
        z = r["r"] * np.sqrt(r["pred"] / r["pred"].median())
        return q.reset_index(), z.quantile([lo, hi]).to_numpy(), r
    q = r.groupby(["land_cover", "season"])["r"].quantile([lo, hi]).unstack()
    q.columns = ["pi_lo", "pi_hi"]
    allq = r["r"].quantile([lo, hi]).to_numpy()
    return q.reset_index(), allq, r


def fit(cm, v_col, m_col, years, cfg, model="ratio", seed=None, intervals=True, totals=None):
    """Point fit + bootstrap CI + LOYO conformal PI. Returns (coef, draws)."""
    coef, draws = fit_point(cm, v_col, m_col, years, cfg, model, seed=seed)
    if intervals:
        q, allq, _ = loyo_intervals(cm, v_col, m_col, years, cfg, model, totals=totals)
        coef = coef.merge(q, on=[c for c in ("land_cover", "season") if c in q.columns], how="left")
        coef["pi_lo"] = coef["pi_lo"].fillna(allq[0])
        coef["pi_hi"] = coef["pi_hi"].fillna(allq[1])
    return coef, draws


def fit_noaa20(cm, cfg):
    """NOAA-20 -> S-NPP bridge, fitted only on months with NOAA-20 archive data (calibration.noaa20_start):
    Jan-Mar 2018 have S-NPP but no NOAA-20 and would inflate the ratio of those calendar months."""
    k = cfg["calibration"]
    st = pd.Period(k.get("noaa20_start", f"{k['noaa20_period'][0]}-01"), freq="M")
    d = cm[cm["year"] * 100 + cm["month"] >= st.year * 100 + st.month]
    return fit(d, "n_viirs_snpp", "n_viirs_noaa20", tuple(k["noaa20_period"]), cfg, intervals=False)


def terra_only_mask(df, cfg):
    y, m = map(int, cfg["calibration"]["terra_only_until"].split("-"))
    return (df["year"] < y) | ((df["year"] == y) & (df["month"] <= m))


def modis_effective(df, terra_coef, cfg):
    """Terra∪Aqua-equivalent MODIS cell-days; Terra-only months scaled by (Terra∪Aqua)/Terra."""
    t = predict(df, "n_modis_terra", terra_coef)["pred"]
    return np.where(terra_only_mask(df, cfg), t, df["n_modis"]).astype(float)


def coefs_from_table(t):
    t = t[t["selected"]]
    return {role: g.drop(columns=["role", "selected"]).dropna(axis=1, how="all").reset_index(drop=True)
            for role, g in t.groupby("role")}


def draws_from_table(t):
    return {k: g[["d0", "d1"]].to_numpy() for k, g in t.groupby("draw_key")} if t is not None else None


def harmonize(cm, coefs, cfg, draws=None):
    """coefs: dict with 'main', 'terra', 'noaa20' coefficient tables."""
    df = with_strata(cm)
    cut = cfg["calibration"]["period"][0]
    df["m_eff"] = modis_effective(df, coefs["terra"], cfg)
    totals = regional_totals(df, "m_eff")
    p = predict(df, "m_eff", coefs["main"], totals=totals, draws=draws, cfg=cfg)
    n20 = predict(df, "n_viirs_noaa20_gap", coefs["noaa20"])["pred"] if "n_viirs_noaa20_gap" in df else 0
    viirs = df["n_viirs_snpp"] + n20
    pre = df["year"] < cut
    df["n_harm"] = np.where(pre, p["pred"], viirs)
    df["n_harm_low"] = np.where(pre, p.get("low", p["pred"]), viirs)
    df["n_harm_high"] = np.where(pre, p.get("high", p["pred"]), viirs)
    if "ci_low" in p:
        df["n_harm_ci_low"] = np.where(pre, p["ci_low"], viirs)
        df["n_harm_ci_high"] = np.where(pre, p["ci_high"], viirs)
    df["k_applied"] = p["weight"].to_numpy()
    df["source"] = np.where(pre, "MODIS_calibrated", "VIIRS_SNPP")
    return df.drop(columns=["season", "m_eff"])

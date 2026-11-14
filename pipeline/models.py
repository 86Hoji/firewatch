"""Candidate MODIS -> VIIRS S-NPP models fit on monthly totals (see reports/model_protocol.md).

Links:
  identity  V = sum_j k_j X_j, k >= 0, Poisson MLE (one predictor: k = sum V / sum X)
  log       E[V] = exp(a) (X + 1)^b, Poisson MLE (quasi-Poisson point estimate)
  log_sep   E[V] = sum_j exp(a_j) (X_j + 1)^b_j
  ols_log1p log1p(V) = a + b log1p(X), OLS + smearing (v1 production model)
Non-linear links are evaluated on whole-region totals and applied to an area as a multiplier on its own counts.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from pipeline.common import SEASONS

SPECS = {
    "C0": {"cols": ["n_modis"], "link": "identity", "label": "Terra∪Aqua, ratio"},
    "C1": {"cols": ["n_modis"], "link": "ols_log1p", "label": "Terra∪Aqua, OLS log1p (v1)"},
    "C2": {"cols": ["n_modis"], "link": "log", "label": "Terra∪Aqua, Poisson log-link"},
    "C3": {"cols": ["n_modis_d", "n_modis_n"], "link": "identity", "label": "Terra∪Aqua day+night, ratio"},
    "C4": {"cols": ["n_modis_aqua"], "link": "identity", "label": "Aqua, ratio"},
    "C5": {"cols": ["n_modis_aqua_d", "n_modis_aqua_n"], "link": "identity", "label": "Aqua day+night, ratio"},
    "C6": {"cols": ["n_modis_aqua"], "link": "log", "label": "Aqua, Poisson log-link"},
    "C7": {"cols": ["n_modis_aqua_d", "n_modis_aqua_n"], "link": "log_sep", "label": "Aqua day+night, Poisson log-link"},
}
N_PARAMS = {"identity": 1, "log": 2, "log_sep": 2, "ols_log1p": 2}   # per predictor column


def monthly_totals(cm, cols, v_col="v_target"):
    keep = [c for c in dict.fromkeys(cols + ([v_col] if v_col in cm else [])) if c in cm]
    return cm.groupby(["year", "month"], as_index=False)[keep].sum()


def _poisson_nll(mu, v):
    mu = np.maximum(mu, 1e-9)
    return float(np.sum(mu - v * np.log(mu)))


def fit_rows(link, X, v):
    """X: (n, p) predictors, v: (n,) target totals -> parameter vector."""
    if link == "identity":
        if X.shape[1] == 1:
            return np.array([v.sum() / max(X[:, 0].sum(), 1e-9)])
        k0 = np.full(X.shape[1], v.sum() / max(X.sum(), 1e-9))
        r = minimize(lambda k: _poisson_nll(X @ k, v), k0, bounds=[(0, None)] * X.shape[1], method="L-BFGS-B")
        return r.x
    if link == "ols_log1p":
        x, y = np.log1p(X[:, 0]), np.log1p(v)
        A = np.column_stack([np.ones_like(x), x])
        a, b = np.linalg.lstsq(A, y, rcond=None)[0]
        return np.array([a, b, np.mean(np.exp(y - a - b * x))])
    if link == "log":
        lx = np.log1p(X[:, 0])
        A = np.column_stack([np.ones_like(lx), lx])
        p0 = np.linalg.lstsq(A, np.log1p(v), rcond=None)[0]
        r = minimize(lambda p: _poisson_nll(np.exp(p[0] + p[1] * lx), v), p0, method="L-BFGS-B",
                     bounds=[(-20, 20), (0, 3)])
        return r.x
    if link == "log_sep":
        lx = np.log1p(X)
        a0 = np.log(max(v.sum(), 1) / max(X.sum(), 1))
        p0 = np.concatenate([[a0, 1.0] for _ in range(X.shape[1])])

        def mu(p):
            return sum(np.exp(p[2 * j] + p[2 * j + 1] * lx[:, j]) for j in range(X.shape[1]))
        r = minimize(lambda p: _poisson_nll(mu(p), v), p0, method="L-BFGS-B",
                     bounds=[(-20, 20), (0, 3)] * X.shape[1])
        return r.x
    raise ValueError(link)


def mu_rows(link, p, X):
    """Expected V for predictor totals X (n, p)."""
    if link == "identity":
        return X @ p
    if link == "ols_log1p":
        return np.maximum(np.exp(p[0] + p[1] * np.log1p(X[:, 0])) * p[2] - 1, 0)
    if link == "log":
        return np.exp(p[0] + p[1] * np.log1p(X[:, 0]))
    if link == "log_sep":
        return sum(np.exp(p[2 * j] + p[2 * j + 1] * np.log1p(X[:, j])) for j in range(X.shape[1]))
    raise ValueError(link)


def fit(spec, train, cfg):
    """train: monthly totals with v_target. Returns {month: (level, params)} with month -> season -> all fallback."""
    cols, link = spec["cols"], spec["link"]
    min_count = cfg["calibration"]["min_count"]
    min_pts = cfg["calibration"]["loglog_min_points"] if link != "identity" else 1
    out = {}
    for m in range(1, 13):
        for level, sel in (("month", train["month"] == m),
                           ("season", train["month"].map(SEASONS) == SEASONS[m]),
                           ("all", np.ones(len(train), bool))):
            rows = train[sel]
            if (rows[cols].to_numpy().sum() >= min_count and len(rows) >= min_pts) or level == "all":
                out[m] = (level, fit_rows(link, rows[cols].to_numpy(float), rows["v_target"].to_numpy(float)))
                break
    return out


def predict(spec, params, test, full=None):
    """Predict V for area totals `test`; non-linear links use whole-region totals `full` (same year, month)."""
    cols, link = spec["cols"], spec["link"]
    full = test if full is None else full
    f = test[["year", "month"]].merge(full[["year", "month"] + cols], on=["year", "month"], how="left")
    Xa, Xf = test[cols].to_numpy(float), f[cols].to_numpy(float)
    out = np.zeros(len(test))
    for m in range(1, 13):
        i = (test["month"] == m).to_numpy()
        if not i.any():
            continue
        p = params[m][1]
        if link == "identity":
            out[i] = Xa[i] @ p
        elif link == "log_sep":
            for j in range(len(cols)):   # per-component multiplier at region totals
                mu_j = np.exp(p[2 * j] + p[2 * j + 1] * np.log1p(Xf[i, j]))
                out[i] += mu_j / np.maximum(Xf[i, j], 1e-9) * Xa[i, j]
        else:
            out[i] = mu_rows(link, p, Xf[i]) / np.maximum(Xf[i].sum(1), 1e-9) * Xa[i].sum(1)
    return out


def multiplier_rows(spec, params, full):
    """Per (year, month) multipliers for each predictor column, evaluated on whole-region totals."""
    cols, link = spec["cols"], spec["link"]
    res = full[["year", "month"]].copy()
    for j, c in enumerate(cols):
        res[f"w_{c}"] = np.nan
    for m in range(1, 13):
        i = (full["month"] == m).to_numpy()
        if not i.any():
            continue
        p = params[m][1]
        X = full.loc[i, cols].to_numpy(float)
        for j, c in enumerate(cols):
            if link == "identity":
                w = np.full(i.sum(), p[j])
            elif link == "log_sep":
                w = np.exp(p[2 * j] + p[2 * j + 1] * np.log1p(X[:, j])) / np.maximum(X[:, j], 1e-9)
            else:
                w = mu_rows(link, p, X) / np.maximum(X.sum(1), 1e-9)
            res.loc[i, f"w_{c}"] = w
    return res

import numpy as np
from scipy import stats


def series_metrics(actual, pred, low=None, high=None):
    a, p = np.asarray(actual, float), np.asarray(pred, float)
    mae = float(np.mean(np.abs(p - a)))
    nz = a > 0
    out = {
        "n_months": int(len(a)),
        "mae": mae,
        "mae_pct_of_mean": 100 * mae / float(np.mean(a)) if np.mean(a) > 0 else None,
        "bias_total_pct": 100 * (p.sum() - a.sum()) / a.sum() if a.sum() > 0 else None,
        "bias_median_rel_pct": float(100 * np.median((p[nz] - a[nz]) / a[nz])) if nz.any() else None,
        "pearson_r": float(stats.pearsonr(a, p)[0]) if len(a) > 2 and np.std(a) > 0 and np.std(p) > 0 else None,
        "spearman_rho": float(stats.spearmanr(a, p)[0]) if len(a) > 2 else None,
    }
    if low is not None:
        lo, hi = np.asarray(low, float), np.asarray(high, float)
        out["coverage"] = float(np.mean((a >= lo) & (a <= hi)))
    return out


def step_test(years, months, values, cut, lags=12, covariate=None):
    """log1p(y) = month dummies + linear trend [+ c * log1p(covariate)] + step*(year >= cut); step with Newey-West
    95% CI. covariate: an independent driver (e.g. burned area) -> the step is the jump NOT explained by it.

    Returns the step as a multiplicative factor exp(beta) with its CI.
    """
    y = np.log1p(np.asarray(values, float))
    t = (np.asarray(years) - np.min(years)) * 12 + np.asarray(months) - 1
    D = (np.asarray(months)[:, None] == np.arange(1, 13)[None, :]).astype(float)
    extra = [] if covariate is None else [np.log1p(np.asarray(covariate, float))]
    X = np.column_stack([D, t / 120.0, *extra, (np.asarray(years) >= cut).astype(float)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    n = len(y)
    XtX_inv = np.linalg.pinv(X.T @ X)
    S = (X * e[:, None]).T @ (X * e[:, None])
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        G = (X[L:] * e[L:, None]).T @ (X[:-L] * e[:-L, None])
        S += w * (G + G.T)
    se = np.sqrt(np.diag(XtX_inv @ S @ XtX_inv))[-1]
    b = beta[-1]
    return {"step_factor": float(np.exp(b)), "ci_low": float(np.exp(b - 1.96 * se)),
            "ci_high": float(np.exp(b + 1.96 * se)), "n_months": int(n),
            "ci_includes_1": bool(np.exp(b - 1.96 * se) <= 1 <= np.exp(b + 1.96 * se))}


def pettitt(x):
    """Pettitt change-point test. Returns (index of last point before change, K, approx p-value)."""
    x = np.asarray(x, float)
    n = len(x)
    s = np.sign(x[:, None] - x[None, :])
    U = np.array([s[: t + 1, t + 1:].sum() for t in range(n - 1)])
    t = int(np.argmax(np.abs(U)))
    K = float(np.abs(U[t]))
    p = float(min(1.0, 2 * np.exp(-6 * K ** 2 / (n ** 3 + n ** 2))))
    return t, K, p

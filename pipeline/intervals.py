"""90% prediction intervals at the level being predicted: the whole country, or a region (or smaller).

Both are conformal: the interval edges are percentiles of how wrong the model was on HELD-OUT data at that level.

country  (method "hetero_log_ratio", the baseline method, calibrated on country totals):
         r = log(actual / pred) from leave-one-year-out; edges q_lo, q_hi of r * sqrt(pred / median_pred);
         interval = pred * exp(q * sqrt(median_pred / pred)) -> relative width shrinks for big months.
region   (method "binned_log1p", new in C3, calibrated on leave-one-region-out):
         r = log1p(actual) - log1p(pred); edges q_lo, q_hi computed separately for predictions of similar size
         (bins on pred: 0, (0,5], (5,20], ...). Small predictions get an interval shifted UP, because VIIRS finds
         relatively more of the small fires that MODIS misses; a prediction of 0 still gets [0, q] since VIIRS often
         sees a few fires where MODIS saw none.
The baseline applied the country interval to any area, sized by the COUNTRY prediction -> 41% coverage per region.
Bounds are rounded outward to whole cell-days.
"""
import numpy as np


def _q(level):
    return (1 - level) / 2, 1 - (1 - level) / 2


def fit_hetero(actual, pred, level=0.90):
    a, p = np.asarray(actual, float), np.asarray(pred, float)
    ok = (a > 0) & (p > 0)
    r = np.log(a[ok] / p[ok])
    med = float(np.median(p[ok]))
    lo, hi = np.quantile(r * np.sqrt(p[ok] / med), _q(level))
    return {"method": "hetero_log_ratio", "level": level, "q_lo": float(lo), "q_hi": float(hi), "median_pred": med,
            "n": int(ok.sum())}


def fit_binned(actual, pred, inner_edges, level=0.90, min_n=30):
    """inner_edges e.g. [5, 20, 100, 500] -> bins {0}, (0,5], (5,20], (20,100], (100,500], >500.
    A bin with fewer than min_n held-out points borrows the next-smaller bins."""
    a, p = np.asarray(actual, float), np.asarray(pred, float)
    r = np.log1p(a) - np.log1p(p)
    b = _bin(p, inner_edges)
    q_lo, q_hi, n = [], [], []
    for i in range(len(inner_edges) + 2):
        m, j = b == i, i
        while m.sum() < min_n and j > 0:
            j -= 1
            m |= b == j
        lo, hi = np.quantile(r[m], _q(level)) if m.any() else (0.0, 0.0)
        q_lo.append(float(lo)), q_hi.append(float(hi)), n.append(int(m.sum()))
    return {"method": "binned_log1p", "level": level, "inner_edges": list(map(float, inner_edges)),
            "q_lo": q_lo, "q_hi": q_hi, "n": n}


def _bin(p, inner_edges):
    """0 -> bin 0; (0, e1] -> 1; (e1, e2] -> 2; ...; > e_last -> len(edges) + 1."""
    p = np.asarray(p, float)
    return np.where(p <= 0, 0, 1 + np.searchsorted(np.asarray(inner_edges, float), p, side="left"))


def bounds(pred, params):
    p = np.asarray(pred, float)
    if params["method"] == "hetero_log_ratio":
        s = np.sqrt(params["median_pred"] / np.maximum(p, 1e-9))
        with np.errstate(over="ignore", invalid="ignore"):       # p ~ 0 -> huge s; those rows are set to 0 below
            lo, hi = p * np.exp(params["q_lo"] * s), p * np.exp(params["q_hi"] * s)
        lo, hi = np.where(p > 0, lo, 0.0), np.where(p > 0, hi, 0.0)
    elif params["method"] == "binned_log1p":
        b = _bin(p, params["inner_edges"])
        ql, qh = np.asarray(params["q_lo"])[b], np.asarray(params["q_hi"])[b]
        lo, hi = np.maximum(0.0, np.expm1(np.log1p(p) + ql)), np.expm1(np.log1p(p) + qh)
    else:
        raise ValueError(params["method"])
    return np.floor(lo), np.ceil(hi)


def coverage(actual, pred, params):
    lo, hi = bounds(pred, params)
    a = np.asarray(actual, float)
    return float(np.mean((a >= lo) & (a <= hi))) if len(a) else float("nan")


def cross_fitted(df, group, fit, actual="actual", pred="pred"):
    """For each group g (a year, a region): fit the interval on all OTHER groups, measure coverage on g."""
    rows = []
    for g, d in df.groupby(group):
        rest = df[df[group] != g]
        params = fit(rest[actual].to_numpy(), rest[pred].to_numpy())
        lo, hi = bounds(d[pred], params)
        a = d[actual].to_numpy()
        inside = (a >= lo) & (a <= hi)
        pos = d[pred].to_numpy() > 0
        rows.append({group: g, "n": int(len(d)), "covered": int(inside.sum()), "coverage": float(inside.mean()),
                     "median_width_pct": float(np.median((hi - lo)[pos] / d[pred].to_numpy()[pos]) * 100)
                     if pos.any() else None})
    return rows

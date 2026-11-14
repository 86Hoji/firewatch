"""C3 intervals: size-binned region intervals and the country (hetero) interval."""
import numpy as np
import pandas as pd

from pipeline import intervals


def _synthetic(n=4000, seed=0):
    rng = np.random.default_rng(seed)
    pred = np.where(rng.random(n) < 0.3, 0.0, rng.lognormal(3, 1.5, n))
    actual = rng.poisson(np.maximum(pred * 1.3, 0.5))
    return actual, pred


def test_bins():
    assert intervals._bin([0, 0.1, 5, 5.01, 20, 600], [5, 20, 100, 500]).tolist() == [0, 1, 1, 2, 2, 5]


def test_binned_bounds_contain_prediction_zone_and_nonnegative():
    a, p = _synthetic()
    par = intervals.fit_binned(a, p, [5, 20, 100, 500], 0.9, 30)
    lo, hi = intervals.bounds(p, par)
    assert (lo >= 0).all() and (hi >= lo).all()
    assert (lo[p == 0] == 0).all() and (hi[p == 0] > 0).all()   # a zero prediction still allows a few fires


def test_binned_coverage_near_nominal_cross_fitted():
    a, p = _synthetic()
    df = pd.DataFrame({"actual": a, "pred": p, "g": np.arange(len(a)) % 10})
    rows = intervals.cross_fitted(df, "g", lambda x, y: intervals.fit_binned(x, y, [5, 20, 100, 500], 0.9, 30))
    cov = sum(r["covered"] for r in rows) / sum(r["n"] for r in rows)
    assert 0.86 <= cov <= 0.96


def test_sparse_bin_borrows_from_smaller_bins():
    a, p = _synthetic()
    p2 = np.append(p, [1000.0, 1200.0])        # only 2 points above 500
    a2 = np.append(a, [1300, 1500])
    par = intervals.fit_binned(a2, p2, [5, 20, 100, 500], 0.9, 30)
    assert par["n"][-1] >= 30


def test_hetero_relative_width_shrinks_with_size():
    a, p = _synthetic()
    par = intervals.fit_hetero(a, p, 0.9)
    lo, hi = intervals.bounds(np.array([50.0, 5000.0]), par)
    w = (hi - lo) / np.array([50.0, 5000.0])
    assert w[1] < w[0]

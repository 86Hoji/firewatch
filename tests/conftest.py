import numpy as np
import pandas as pd
import pytest

from pipeline.common import load_config


@pytest.fixture
def cfg():
    c = load_config()
    c["calibration"]["bootstrap_iter"] = 200
    return c


def synthetic_cell_month(k_by_lc, years=range(2012, 2020), cells=300, seed=0, sparse_month=None):
    """SYNTHETIC test data only: V ~ Poisson(k * M) per cell-month."""
    rng = np.random.default_rng(seed)
    rows = []
    for lc, k in k_by_lc.items():
        for c in range(cells):
            for y in years:
                for m in range(1, 13):
                    lam = 0.05 if m == sparse_month else 2.0 + 3 * (m in (7, 8, 9))
                    M = rng.poisson(lam)
                    V = rng.poisson(k * M)
                    if M or V:
                        rows.append((f"{lc}-{c}", y, m, M, V, lc))
    df = pd.DataFrame(rows, columns=["h3_cell", "year", "month", "n_modis", "n_viirs_snpp", "land_cover"])
    df["n_modis_terra"] = df["n_modis"]
    df["n_viirs_noaa20_gap"] = 0
    return df

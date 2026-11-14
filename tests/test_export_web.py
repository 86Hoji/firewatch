"""Phase D export helpers."""
import importlib

import pandas as pd

EXP = importlib.import_module("pipeline.08_export_web")


def test_sig_rounds_to_three_significant_digits():
    assert EXP.sig(12345) == 12300
    assert EXP.sig(0.012345) == 0.0123
    assert EXP.sig(87) == 87 and isinstance(EXP.sig(87.0), int)
    assert EXP.sig(0) == 0 and EXP.sig(None) is None and EXP.sig(float("nan")) is None
    assert EXP.sig(-4567) == -4570


def test_full_months_fills_missing_months_with_zero():
    p, _ = EXP.ym_range("2001-01", "2001-04")
    d = pd.DataFrame({"year": [2001, 2001], "month": [1, 3], "n": [5, 7]})
    out = EXP.full_months(d, p, ["n"])
    assert out["n"].tolist() == [5, 0, 7, 0]

"""Flag the modelled months that lie outside the calibration range -> reports/extrapolation_flags.json.

    python -m pipeline.extrapolation_flags

A month before calibration.period[0] (MODIS converted to S-NPP equivalent) is `extrapolated` when its MODIS
cell-days exceed the largest value of the same calendar month in the calibration years (2012-2019): the fitted
curve is then used beyond the data it was fitted on. `ratio` = MODIS / that maximum (max floored at 1 cell-day).
Observed months (2012+) are never flagged. How well the model holds a moderate step outside its range is measured by
T5 in pipeline/experiments.py (docs/HARMONIZATION_REVIEW.md 2.1); the flag says WHERE the product relies on it.

Input: the exported country series web/public/data/series/{CC}.json (read only), so the flags match the website.
"""
import json

import numpy as np
import pandas as pd

from pipeline.common import REPORTS, ROOT, get_logger, load_config, write_json

log = get_logger("extrapolation_flags")
SERIES = ROOT / "web" / "public" / "data" / "series"


def flags(ym, modis, cal):
    """ym: 'YYYY-MM' list, modis: MODIS cell-days. Returns DataFrame(ym, year, month, ratio, extrapolated)."""
    d = pd.DataFrame({"ym": ym, "modis": np.asarray(modis, float)})
    d["year"], d["month"] = d["ym"].str[:4].astype(int), d["ym"].str[5:7].astype(int)
    in_cal = d["year"].between(*cal)
    cmax = d[in_cal].groupby("month")["modis"].max().clip(lower=1.0)
    pre = d["year"] < cal[0]
    d["ratio"] = np.where(pre, d["modis"] / d["month"].map(cmax), np.nan)
    d["extrapolated"] = pre & (d["ratio"] > 1)
    return d


def summary(d, cal):
    pre = d[d["year"] < cal[0]]
    by_year = pre.groupby("year").agg(months=("extrapolated", "sum"), max_ratio=("ratio", "max"))
    return {"months_before_calibration": int(len(pre)), "months_extrapolated": int(pre["extrapolated"].sum()),
            "share_extrapolated": float(pre["extrapolated"].mean()) if len(pre) else None,
            "median_ratio": float(pre["ratio"].median()) if len(pre) else None,
            "max_ratio": float(pre["ratio"].max()) if len(pre) else None,
            "by_year": {int(y): {"months": int(r["months"]), "max_ratio": round(float(r["max_ratio"]), 3)}
                        for y, r in by_year.iterrows()}}


def main():
    cfg = load_config()
    cal = tuple(cfg["calibration"]["period"])
    out = {"rule": f"month before {cal[0]} with MODIS cell-days above the same calendar month's maximum in "
                   f"{cal[0]}-{cal[1]}", "calibration_period": list(cal),
           "caveat": f"Terra-only months (to {cfg['calibration']['terra_only_until']}) compare Terra alone with "
                     "Terra+Aqua maxima, so they are under-flagged", "countries": {}}
    for p in sorted(SERIES.glob("*.json")):
        j = json.loads(p.read_text(encoding="utf-8"))
        d = flags(j["ym"], j["modis_only"], cal)
        out["countries"][p.stem] = {**summary(d, cal),
                                    "extrapolated_months": d.loc[d["extrapolated"], "ym"].tolist(),
                                    "ym": d["ym"].tolist(), "extrapolated": d["extrapolated"].tolist(),
                                    "ratio": [None if not np.isfinite(r) else round(float(r), 3) for r in d["ratio"]]}
        s = out["countries"][p.stem]
        log.info("%s: %d of %d modelled months extrapolated (%.0f%%), max ratio %.2f", p.stem,
                 s["months_extrapolated"], s["months_before_calibration"], 100 * (s["share_extrapolated"] or 0),
                 s["max_ratio"] or 0)
    write_json(REPORTS / "extrapolation_flags.json", out)


if __name__ == "__main__":
    main()

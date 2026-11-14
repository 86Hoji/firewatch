"""Regression check: the train country (KZ) must give exactly the Phase B results after any refactor.

Compares against the snapshot in reports/phase_b/ (taken before Phase C):
  cleaning steps, hotspots per platform-year, yearly cell-month sums, country_month == sum of cell_month,
  and (if the full pipeline ran) every headline metric in metrics.json / model_comparison.json.
Exit code 1 on any difference.   python -m pipeline.regression_check
"""
import json
import sys

import duckdb
import numpy as np
import pandas as pd

from pipeline.common import AGG, PROCESSED, REPORTS, load_config

SNAP = REPORTS / "phase_b"


def _flat(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flat(v, f"{prefix}{k}."))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out.update(_flat(v, f"{prefix}{i}."))
    else:
        out[prefix[:-1]] = d
    return out


def compare_json(name, rtol=1e-9):
    a, b = _flat(json.loads((SNAP / name).read_text(encoding="utf-8"))), \
        _flat(json.loads((REPORTS / name).read_text(encoding="utf-8")))
    bad = []
    for k in sorted(set(a) | set(b)):
        x, y = a.get(k), b.get(k)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
            if not np.isclose(x, y, rtol=rtol, atol=1e-12, equal_nan=True):
                bad.append((k, x, y))
        elif x != y:
            bad.append((k, x, y))
    return bad


def main():
    cfg = load_config()
    c = cfg["train_country"]
    fails = []
    # 1. cleaning steps
    old = json.loads((SNAP / "cleaning_summary.json").read_text(encoding="utf-8"))
    new = json.loads((REPORTS / "cleaning_summary.json").read_text(encoding="utf-8"))["countries"][c]
    if old["steps"] != new["steps"]:
        fails.append(("cleaning steps", old["steps"], new["steps"]))
    if old["static_mask_cells"] != new["static_mask_cells"]:
        fails.append(("static mask cells", old["static_mask_cells"], new["static_mask_cells"]))
    # 2. hotspots per platform-year
    h0 = pd.read_csv(SNAP / "kz_hotspots_platform_year.csv")
    h1 = duckdb.sql(f"""SELECT platform, CAST(year AS BIGINT) AS year, count(*) AS n FROM read_parquet(
        '{(PROCESSED / 'hotspots' / f'country={c}').as_posix()}/**/*.parquet', hive_partitioning = true)
        GROUP BY ALL ORDER BY ALL""").df()
    if not h0.equals(h1.astype(h0.dtypes.to_dict())):
        fails.append(("hotspots by platform-year", len(h0), len(h1)))
    # 3. yearly cell-month sums (all columns that existed in Phase B)
    y0 = pd.read_csv(SNAP / "kz_cell_month_yearly.csv", index_col="year")
    cm = pd.read_parquet(AGG / "cell_month_all.parquet", filters=[("country", "==", c)])
    cols = [k for k in y0.columns if k in cm.columns and not k.startswith("n_harm")]
    y1 = cm.groupby("year")[cols].sum()
    diff = (y1 - y0[cols]).abs().to_numpy().max()
    if diff > 0:
        fails.append(("yearly cell-month sums", 0, float(diff)))
    # 4. country_month equals the sum of cell_month
    cmon = pd.read_parquet(AGG / "country_month" / f"{c}.parquet").set_index(["year", "month"])
    s = cm.groupby(["year", "month"])[[k for k in cmon.columns if k.startswith(("n_", "p_"))
                                       and k not in ("n_active_cells", "n_outage_days")]].sum()
    if (s - cmon[s.columns]).abs().to_numpy().max() > 0:
        fails.append(("country_month vs cell_month", 0, float((s - cmon[s.columns]).abs().to_numpy().max())))
    # 5. metrics (only if the downstream steps were rerun)
    for name in ("metrics.json", "model_comparison.json", "model_selection.json"):
        if (REPORTS / name).stat().st_mtime > (AGG / "cell_month_all.parquet").stat().st_mtime:
            fails += [(f"{name}:{k}", x, y) for k, x, y in compare_json(name)]
        else:
            print(f"skip {name}: older than this cleaning run (rerun 05-07 to check it)")
    print(f"checked {c}: hotspots {int(h1['n'].sum())}, cell-months {len(cm)}, {len(cols)} cell-month columns")
    if fails:
        for f in fails[:40]:
            print("DIFF", *f)
        print(f"FAILED: {len(fails)} differences")
        sys.exit(1)
    print("OK: identical to Phase B")


if __name__ == "__main__":
    main()

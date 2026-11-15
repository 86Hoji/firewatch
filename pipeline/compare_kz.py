"""Kazakhstan headline metrics: Phase B vs C3 vs C4 snapshots vs now -> reports/kz_before_after.{json,md}.

Snapshots: reports/phase_b/ (before Phase C), reports/phase_c3/ (after C3, before the C3-review changes: type-2-only
mask from the last 5 years, satellite-wide outage days), reports/phase_c4/ (before the static-site fix: every row in
masked cells dropped + static_site rule).    python -m pipeline.compare_kz
"""
import json

from pipeline.common import REPORTS, write_json, load_config


def _get(d, *path):
    for p in path:
        if d is None:
            return None
        d = d.get(p) if isinstance(d, dict) else None
    return d


def load(folder):
    def j(name):
        p = folder / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    return {"metrics": j("metrics.json"), "mc": j("model_comparison.json"), "clean": j("cleaning_summary.json")}


def extract(s, cfg):
    M, mc, cl = s["metrics"], s["mc"], s["clean"]
    c = cfg["train_country"]
    kz = (cl or {}).get("countries", {}).get(c, cl) if cl else None
    sel = (mc or {}).get("selected")
    res = _get(mc, "results", sel) or {}
    prod = (M or {}).get("selected_model") or "poisson_log"
    steps = {st["step"]: st for st in (kz or {}).get("steps", [])}
    th = _get(M, "temporal_holdout", "holdout", prod) or {}
    j = _get(M, "jump") or {}
    iv = (mc or {}).get("intervals") or {}
    return {
        "hotspots after cleaning": _get(steps, "nrt_overlaps_sp", "rows_out"),
        "removed as static (type != 0)": _get(steps, "type_not_vegetation", "removed"),
        "removed by static mask": _get(steps, "static_mask", "removed") or _get(steps, "nrt_static_mask", "removed"),
        "static mask cells": (kz or {}).get("static_mask_cells"),
        "selected model": f"{sel} ({prod})" if sel else None,
        "step ratio 2012: naive points": _get(j, "naive_points", "step_ratio"),
        "step ratio 2012: naive cell-days": _get(j, "naive_cell_days", "step_ratio"),
        "step ratio 2012: harmonized": _get(j, "harmonized", "step_ratio"),
        "step ratio 2012: MODIS alone": _get(j, "modis_only_reference", "step_ratio"),
        "harmonized jump vs MODIS alone": _get(j, "harmonized", "excess_jump_vs_modis"),
        "monthly step factor, harmonized": _get(j, "harmonized", "monthly_step", "step_factor"),
        "backcast T1 MAE %": _get(res, "T1_backcast", "mae_pct_of_mean"),
        "backcast T1 bias %": _get(res, "T1_backcast", "bias_total_pct"),
        "leave-one-year-out T4 MAE %": _get(res, "T4_loyo", "mae_pct_of_mean"),
        "holdout 2020+ MAE %": th.get("mae_pct_of_mean"),
        "holdout 2020+ bias %": th.get("bias_total_pct"),
        "holdout 2020+ coverage": th.get("coverage"),
        "LORO MAE % (median region)": _get(M, "spatial_cv_median", prod, "mae_pct_of_mean"),
        "LORO coverage (region-months)": (_get(iv, "coverage_after", "T3_loro_region")
                                          or _get(M, "spatial_cv_median", prod, "coverage")),
        "model score (mean T1, T3, T4)": res.get("score"),
    }


def fmt(v):
    if v is None:
        return "–"
    if isinstance(v, str):
        return v
    if isinstance(v, int) or (isinstance(v, float) and v.is_integer() and abs(v) > 1000):
        return f"{int(v):,}"
    return f"{v:.3f}" if abs(v) < 10 else f"{v:.1f}"


def main():
    cfg = load_config()
    cols = {"Phase B": REPORTS / "phase_b", "after C3": REPORTS / "phase_c3", "C4 (before flare fix)": REPORTS / "phase_c4",
            "now": REPORTS}
    T = {k: extract(load(p), cfg) for k, p in cols.items()}
    write_json(REPORTS / "kz_before_after.json", T)
    keys = list(T["now"].keys())
    L = ["# Kazakhstan: what moved", "", "| metric | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for k in keys:
        L.append(f"| {k} | " + " | ".join(fmt(T[c][k]) for c in cols) + " |")
    L += ["", "Phase B LORO used H3 res-1 hexagons without zero months; since C3 it uses ADM1 oblasts with zero months "
          "and the region-level interval (not comparable one-to-one)."]
    (REPORTS / "kz_before_after.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()

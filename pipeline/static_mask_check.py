"""C2: is the static-source mask a good stand-in for FIRMS `type` (missing in NRT rows)? Honest time split.

Train: mask built ONLY from archive rows (they carry `type`) dated before mask_check.split (2025-01-01).
Test:  archive rows from split to mask_check.test_end (2026-07-31), never seen when building the mask.
 * detection level: does "in a masked cell" catch type = 2 (static land source)? precision, recall, F1
   - production mask (type-2 rule, built from the last cleaning.static_mask.recent_years years before the split),
     and for comparison the C2 mask (both rules, all history), the type-2 rule on all history, the persistent rule
 * monthly totals: cell-days per month if the mask REPLACED `type` (drop masked cells, ignore type) vs the
   production rule (keep type = 0); % change per country and sensor.
Outputs reports/static_mask_check.json and .md.   python -m pipeline.static_mask_check
"""
import pandas as pd

from pipeline import ingest
from pipeline.common import REPORTS, get_logger, load_config, write_json

log = get_logger("mask_check")
clean_mod = __import__("importlib").import_module("pipeline.02_clean")


def pr(con, test, mask_tbl):
    tp, fp, fn, n2, n = con.execute(f"""
        SELECT count(*) FILTER (WHERE m.h3_cell IS NOT NULL AND type = 2),
               count(*) FILTER (WHERE m.h3_cell IS NOT NULL AND type <> 2),
               count(*) FILTER (WHERE m.h3_cell IS NULL AND type = 2),
               count(*) FILTER (WHERE type = 2), count(*)
        FROM {test} t LEFT JOIN {mask_tbl} m USING (h3_cell)""").fetchall()[0]
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f1 = 2 * p * r / (p + r) if p and r else None
    return {"precision": p, "recall": r, "f1": f1, "tp": tp, "fp": fp, "fn": fn,
            "test_rows": n, "test_type2_rows": n2, "type2_share": n2 / n if n else None}


def monthly_change(con, test, mask_tbl):
    """Cell-days per month and sensor group: production (type = 0) vs mask instead of type."""
    q = f"""
        WITH a AS (SELECT * FROM {test} WHERE type = 0),
             b AS (SELECT * FROM {test} WHERE h3_cell NOT IN (SELECT h3_cell FROM {mask_tbl}))
        SELECT x.year, x.month, x.grp, x.n AS prod, coalesce(y.n, 0) AS mask FROM
          (SELECT year, month, CASE WHEN sensor = 'MODIS' THEN 'MODIS' ELSE platform END AS grp,
                  count(DISTINCT (h3_cell, date)) AS n FROM a GROUP BY ALL) x
          LEFT JOIN
          (SELECT year, month, CASE WHEN sensor = 'MODIS' THEN 'MODIS' ELSE platform END AS grp,
                  count(DISTINCT (h3_cell, date)) AS n FROM b GROUP BY ALL) y USING (year, month, grp)
        ORDER BY ALL"""
    m = con.execute(q).df()
    m["pct"] = 100 * (m["mask"] / m["prod"] - 1)
    out = {}
    for g, d in m.groupby("grp"):
        if g not in ("MODIS", "SNPP", "NOAA20"):
            continue
        out[g] = {"total_prod": int(d["prod"].sum()), "total_mask": int(d["mask"].sum()),
                  "total_pct": float(100 * (d["mask"].sum() / d["prod"].sum() - 1)),
                  "median_abs_monthly_pct": float(d.loc[d["prod"] >= 10, "pct"].abs().median()),
                  "max_abs_monthly_pct": float(d.loc[d["prod"] >= 10, "pct"].abs().max()),
                  "months": int(len(d))}
    return out


MASKS = {"mask": "mask", "c2_both_rules_all_history": "mask_c2", "type2_all_history": "mask_type2_all",
         "persistent_rule_only": "mask_persistent"}
LABELS = {"mask": "production: type-2 rule, last 5 y", "c2_both_rules_all_history": "C2 mask (both rules, all history)",
          "type2_all_history": "type-2 rule, all history", "persistent_rule_only": "persistent rule only"}


def check_country(cfg, man, country):
    mc = cfg["mask_check"]
    path = ingest.work_dir(cfg) / f"maskcheck_{country}.duckdb"
    ingest.remove_work(path)
    con = ingest.connect(cfg, path)
    try:
        ingest.stage(con, cfg, man[man["country"] == country], clean_mod.unify, cfg["inputs"]["sensors"])
        ingest.confident(con, cfg)
        sp = mc["split"]
        q = lambda **k: ingest.static_mask_sql(cfg, "t1", before=sp, **k)  # noqa: E731
        con.execute(f"CREATE TABLE mask AS {q()}")                                    # production (as configured)
        con.execute(f"CREATE TABLE mask_c2 AS {q(rules=['type2', 'persistent'], recent_years=None)}")
        con.execute(f"CREATE TABLE mask_type2_all AS {q(rules=['type2'], recent_years=None)}")
        con.execute(f"CREATE TABLE mask_persistent AS {q(rules=['persistent'], recent_years=None)}")
        con.execute(f"""CREATE TABLE test AS SELECT * FROM t1 WHERE type IS NOT NULL
                        AND date >= DATE '{sp}' AND date <= DATE '{mc['test_end']}'""")
        res = {"mask_cells": {k: con.execute(f"SELECT count(*) FROM {t}").fetchall()[0][0]
                              for k, t in MASKS.items()},
               "detection": {k: pr(con, "test", t) for k, t in MASKS.items()},
               "monthly": {k: monthly_change(con, "test", t) for k, t in MASKS.items() if k != "persistent_rule_only"}}
    finally:
        con.close()
        ingest.remove_work(path)
    d = res["detection"]["mask"]
    log.info("%s: precision %.3f recall %.3f (type2 share of test rows %.1f%%)", country, d["precision"] or 0,
             d["recall"] or 0, 100 * (d["type2_share"] or 0))
    return res


def fmt(x, d=1, pct=False):
    if x is None:
        return "—"
    return f"{100 * x:.{d}f}%" if pct else f"{x:.{d}f}"


def write_md(cfg, R):
    mc = cfg["mask_check"]
    L = ["# Static-source mask: honest test", "",
         f"Every mask is built ONLY from archive rows before {mc['split']}; tested on archive rows {mc['split']} … {mc['test_end']} "
         "(which carry the true FIRMS `type`). A detection counts as \"caught\" if it falls in a masked H3 cell.", "",
         "## Does the mask catch static sources (type = 2)?", "",
         "| country | rule | precision | recall | F1 | test rows | of which type 2 |", "|---|---|---|---|---|---|---|"]
    for c, r in R.items():
        for k, lab in LABELS.items():
            d = r["detection"][k]
            L.append(f"| {c} | {lab} | {fmt(d['precision'], pct=True)} | {fmt(d['recall'], pct=True)} | "
                     f"{fmt(d['f1'], 3)} | {d['test_rows']:,} | {d['test_type2_rows']:,} ({fmt(d['type2_share'], pct=True)}) |")
    L += ["", "## If the mask replaced `type`: change in monthly cell-days", "",
          "Production keeps `type = 0`; the alternative drops masked cells and ignores `type`. "
          "Positive = the mask lets through more than `type` does (missed flares, or real fires `type` drops).", "",
          "| country | rule | sensor | total change | median monthly abs. change | worst month |", "|---|---|---|---|---|---|"]
    for c, r in R.items():
        for k, lab in ((k, v) for k, v in LABELS.items() if k in r["monthly"]):
            for g, m in r["monthly"][k].items():
                L.append(f"| {c} | {lab} | {g} | {m['total_pct']:+.1f}% | {m['median_abs_monthly_pct']:.1f}% | "
                         f"{m['max_abs_monthly_pct']:.1f}% |")
    (REPORTS / "static_mask_check.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    cfg = load_config()
    man = ingest.load_manifest(cfg)
    R = {c: check_country(cfg, man, c) for c in cfg["mask_check"]["countries"]}
    write_json(REPORTS / "static_mask_check.json", {"split": cfg["mask_check"]["split"],
                                                    "test_end": cfg["mask_check"]["test_end"], "countries": R})
    write_md(cfg, R)
    log.info("wrote reports/static_mask_check.{json,md}")


if __name__ == "__main__":
    main()

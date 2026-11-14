"""Why the outage list is satellite-wide: per-country rules compared with the global list (reports/outage_check.json).

Reference = the production list (pipeline/outage.py, all countries combined). For each country: the old fixed
threshold (20 NOAA-20 detections) and the superseded per-country threshold; days found, share of the global list
caught ("found"), share of the country's days that are real ("true").     python -m pipeline.outage_check
"""
import pandas as pd

from pipeline import ingest, outage
from pipeline.common import REPORTS, get_logger, load_config, write_json

log = get_logger("outage_check")


def main():
    cfg = load_config()
    oc = cfg["outage"]["per_country_superseded"]
    daily = outage.combined_daily(cfg)
    days, _ = outage.global_days(cfg, daily)
    ref = set(days["date"])
    since = pd.Timestamp(oc["typical_from"])
    out = {"global_outage_days": len(ref), "countries_combined": sorted(daily["country"].unique()), "countries": {}}
    for c, d in daily.groupby("country"):
        thr, info = ingest.outage_threshold(cfg, c, d.drop(columns="country"))
        d = d[d["date"] >= since]
        row = {"per_country_threshold": thr, "typical_daily_noaa20": info["typical_daily_noaa20"]}
        for name, t in (("fixed_20", oc["reference_threshold"]), ("per_country", thr)):
            sel = set(d.loc[(d["n_snpp"] == 0) & (d["n_noaa20"] >= t), "date"])
            tp = len(sel & ref)
            row[name] = {"outage_days": len(sel), "global": tp, "true_share": tp / len(sel) if sel else None,
                         "found_share": tp / len(ref) if ref else None}
        out["countries"][c] = row
        log.info("%s: %s", c, row)
    write_json(REPORTS / "outage_check.json", out)
    return out


if __name__ == "__main__":
    main()

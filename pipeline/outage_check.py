"""Cross-check of the per-country S-NPP outage thresholds.

S-NPP outages are satellite-wide, so a real outage day should be an outage in every country with fires that day.
Reference ("global") outage days: S-NPP has zero detections summed over all countries while NOAA-20 has detections
in at least half of them. For each country: how many of its outage days are global (precision) and how many global
days it catches (recall), with the per-country threshold and with the old fixed one.
-> reports/outage_check.json        python -m pipeline.outage_check
"""
import duckdb

from pipeline.common import AGG, REPORTS, get_logger, load_config, write_json

log = get_logger("outage_check")


def main():
    cfg = load_config()
    oc = cfg["outage"]
    files = sorted((AGG / "country_day").glob("*.parquet"))
    con = duckdb.connect()
    con.execute(f"CREATE TABLE d AS SELECT * FROM read_parquet({[f.as_posix() for f in files]}, filename = true)")
    # country_day is already one row per country-date with a count per platform
    con.execute(f"""CREATE TABLE w AS SELECT regexp_extract(filename, '([A-Z]{{3}})\\.parquet$', 1) AS country,
                    CAST(date AS DATE) AS date, n_snpp AS snpp, n_noaa20 AS n20
                    FROM d WHERE date >= DATE '{oc["typical_from"]}'""")
    nc = con.execute("SELECT count(DISTINCT country) FROM w").fetchall()[0][0]
    con.execute(f"""CREATE TABLE g AS SELECT date FROM w GROUP BY date
                    HAVING sum(snpp) = 0 AND count(*) FILTER (WHERE n20 > 0) >= {nc / 2}""")
    n_global = con.execute("SELECT count(*) FROM g").fetchall()[0][0]
    summ = __import__("json").loads((REPORTS / "cleaning_summary.json").read_text(encoding="utf-8"))["countries"]
    out = {"n_countries": nc, "global_outage_days": n_global, "countries": {}}
    for c in sorted(summ):
        thr = (summ[c].get("outage") or {}).get("threshold")
        if thr is None:
            continue
        row = {"threshold": thr}
        for name, t in (("per_country", thr), ("fixed", oc["reference_threshold"])):
            tp, n = con.execute(f"""SELECT count(*) FILTER (WHERE date IN (SELECT date FROM g)), count(*) FROM w
                                    WHERE country = '{c}' AND snpp = 0 AND n20 >= {t}""").fetchall()[0]
            row[name] = {"outage_days": n, "global": tp, "precision": tp / n if n else None,
                         "recall": tp / n_global if n_global else None}
        out["countries"][c] = row
        log.info("%s thr %s: %s", c, thr, row)
    write_json(REPORTS / "outage_check.json", out)


if __name__ == "__main__":
    main()

"""S-NPP outage days: one satellite-wide list, derived from ALL countries combined.

An outage is a property of the satellite, not of a country: when S-NPP delivers no data, it is missing everywhere.
Rule (config `outage`): a UTC day is an outage day when, summed over all countries in the manifest,
  S-NPP detections <= max_snpp_share x NOAA-20 detections   and   NOAA-20 detections >= min_noaa20_total.
The big countries (USA, BRA, AUS, IND) see thousands of NOAA-20 detections every day, so a real outage is unmistakable
(S-NPP ~0 against thousands); a small country alone cannot tell an outage from a quiet day.
On those days S-NPP cell-days are filled with NOAA-20 cell-days in cells where S-NPP saw nothing that day.

Inputs : data/aggregated/country_day/{ISO3}.parquet (02_clean; daily detections per satellite, plus
         c_noaa20_only = cells seen by NOAA-20 but not S-NPP that day)
Outputs: data/aggregated/outage_days.parquet, reports/outage_days.json, and the outage columns
         (n_viirs_noaa20_gap, n_outage_days) of country_month for totals-only countries.
"""
import pandas as pd

from pipeline import ingest
from pipeline.common import AGG, REPORTS, ROOT, get_logger, load_config, write_json

log = get_logger("outage")


def days_path(cfg):
    return ROOT / cfg["outage"]["file"]


def _ready(c):
    """country_day exists and was written by the current 02_clean (has c_noaa20_only)."""
    p = AGG / "country_day" / f"{c}.parquet"
    return p.exists() and "c_noaa20_only" in pd.read_parquet(p).columns


def combined_daily(cfg, man=None, skip=()):
    """Daily counts of every manifest country. skip: countries left out on purpose (provisional run only)."""
    man = ingest.load_manifest(cfg) if man is None else man
    want = [c for c in ingest.countries(cfg, man) if c not in set(skip)]
    missing = sorted(c for c in want if not _ready(c))
    if missing:
        raise SystemExit(f"country_day missing/outdated for {missing}: run 02_clean for all countries first")
    d = pd.concat([pd.read_parquet(AGG / "country_day" / f"{c}.parquet").assign(country=c) for c in sorted(want)])
    d["date"] = pd.to_datetime(d["date"]).dt.normalize()
    return d


def global_days(cfg, daily):
    o = cfg["outage"]
    g = daily.groupby("date").agg(snpp=("n_snpp", "sum"), noaa20=("n_noaa20", "sum"),
                                  countries_with_noaa20=("n_noaa20", lambda s: int((s > 0).sum()))).reset_index()
    g["snpp_share"] = g["snpp"] / g["noaa20"].where(g["noaa20"] > 0)
    out = (g["noaa20"] >= o["min_noaa20_total"]) & (g["snpp"] <= o["max_snpp_share"] * g["noaa20"])
    return g[out].sort_values("date").reset_index(drop=True), g


def load_days(cfg):
    """Outage dates (datetime.date list). Fails loudly if the global list was not built (run 02b_outage)."""
    p = days_path(cfg)
    if not p.exists():
        raise SystemExit(f"{p} missing: run `python -m pipeline.run_all 02b` after 02_clean for all countries")
    return pd.to_datetime(pd.read_parquet(p)["date"]).dt.date.tolist()


def gap_from_country_day(daily_c, days):
    """Country-month outage columns from one country's country_day (totals-only countries)."""
    d = daily_c.copy()
    d["date"] = pd.to_datetime(d["date"]).dt.normalize()
    on = d["date"].dt.date.isin(set(days))
    d["year"], d["month"] = d["date"].dt.year.astype(int), d["date"].dt.month.astype(int)
    gap = d[on].groupby(["year", "month"])["c_noaa20_only"].sum().rename("n_viirs_noaa20_gap")
    nd = pd.Series(pd.to_datetime(list(days))).pipe(
        lambda s: s.groupby([s.dt.year.astype(int), s.dt.month.astype(int)]).size()).rename("n_outage_days")
    nd.index.names = ["year", "month"]
    return gap, nd


def main(provisional=False):
    """provisional=True: build the list from the countries that are ready and say which are missing (used once in
    C4 while Brazil was still re-ingesting; the final run always uses all countries)."""
    cfg = load_config()
    man = ingest.load_manifest(cfg)
    skip = [c for c in ingest.countries(cfg, man) if not _ready(c)] if provisional else []
    if skip:
        log.warning("PROVISIONAL outage list without %s", skip)
    daily = combined_daily(cfg, man, skip)
    days, g = global_days(cfg, daily)
    p = days_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    days.to_parquet(p, index=False)
    dates = days["date"].dt.date.tolist()
    near = g[(g["snpp_share"] > cfg["outage"]["max_snpp_share"]) & (g["snpp_share"] <= 0.3)
             & (g["noaa20"] >= cfg["outage"]["min_noaa20_total"])]
    # totals-only countries: patch the outage columns of country_month from country_day
    patched = {}
    for c in ingest.countries(cfg, man, "totals"):
        if c in skip:
            continue
        f = AGG / "country_month" / f"{c}.parquet"
        cm = pd.read_parquet(f).drop(columns=["n_viirs_noaa20_gap", "n_outage_days"], errors="ignore")
        gap, nd = gap_from_country_day(daily[daily["country"] == c], dates)
        cm = cm.merge(gap.reset_index(), on=["year", "month"], how="left") \
               .merge(nd.reset_index(), on=["year", "month"], how="left")
        cm[["n_viirs_noaa20_gap", "n_outage_days"]] = cm[["n_viirs_noaa20_gap", "n_outage_days"]].fillna(0).astype("int64")
        cm.to_parquet(f, index=False)
        patched[c] = int(cm["n_viirs_noaa20_gap"].sum())
    rep = {"rule": {k: cfg["outage"][k] for k in ("max_snpp_share", "min_noaa20_total")},
           "provisional_missing": skip,
           "countries": sorted(daily["country"].unique()), "n_days": len(days),
           "by_year": days.groupby(days["date"].dt.year).size().astype(int).to_dict(),
           "days": [{"date": str(r.date.date()), "snpp": int(r.snpp), "noaa20": int(r.noaa20),
                     "countries_with_noaa20": int(r.countries_with_noaa20)} for r in days.itertuples()],
           "partial_days_not_counted": [{"date": str(r.date.date()), "snpp_share": round(float(r.snpp_share), 3)}
                                        for r in near.itertuples()],
           "noaa20_fill_cell_days_totals_only": patched}
    write_json(REPORTS / "outage_days.json", rep)
    log.info("satellite-wide S-NPP outage days: %d (from %d countries); partial days not counted: %d",
             len(days), rep["countries"].__len__(), len(near))
    return rep


if __name__ == "__main__":
    import sys
    main(provisional="--provisional" in sys.argv)

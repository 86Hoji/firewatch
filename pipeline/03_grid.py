"""Aggregate hotspots to H3 cell-months (cell-level countries) and country-months (all countries).

Outputs:
  data/aggregated/cell_month_all.parquet   one row per (country, h3_cell, year, month), cell-level countries only
  data/aggregated/country_month/XXX.parquet totals per (country, year, month); transfer countries are written by
                                           02_clean straight from their cleaned points (same query)
"""
import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from pipeline import ingest, regions  # noqa: E402
from pipeline.common import AGG, PROCESSED, REPORTS, ensure_dirs, get_logger, load_config, write_json  # noqa: E402
from pipeline.ingest import GROUPS, cell_month_query, outage_fill  # noqa: E402,F401  (re-exported for tests)

log = get_logger("grid")
ADM1_LOG = {}


def hotspots_src(country):
    return (f"read_parquet('{(PROCESSED / 'hotspots' / f'country={country}').as_posix()}/**/*.parquet', "
            f"hive_partitioning = true)")


def build(con, cfg, country):
    src = hotspots_src(country)
    thr, _ = ingest.outage_threshold(cfg, country)
    n_in = con.execute(f"SELECT count(*) FROM {src}").fetchall()[0][0]
    cm = con.execute(cell_month_query(src)).df()
    # days when S-NPP saw nothing country-wide but NOAA-20 did -> outage, filled later from NOAA-20
    gap, n_gap_days = outage_fill(con, src, thr)
    cm = cm.merge(gap, on=["h3_cell", "year", "month"], how="left")
    cm["n_viirs_noaa20_gap"] = cm["n_viirs_noaa20_gap"].fillna(0).astype("int64")
    cells = ingest.cells_table(con, cm["h3_cell"].unique(), cfg["grid"]["coarse_res"])
    adm = regions.assign(cfg, country, cells)
    cells = cells.merge(adm[["h3_cell", "adm1_id", "adm1_name", "adm1_method", "adm1_dist_km"]], on="h3_cell")
    cm = cm.merge(cells, on="h3_cell")
    ADM1_LOG[country] = {"cells": regions.summary(adm),
                         "modis_cell_days": cm.groupby("adm1_method")["n_modis"].sum().astype(int).to_dict()}
    cm.insert(0, "country", country)
    cmon = con.execute(ingest.country_month_query(src, thr)).df()
    cmon.insert(0, "country", country)
    log.info("%s: hotspots %d, S-NPP outage days %d, cell-months %d, cells %d", country, n_in, n_gap_days,
             len(cm), len(cells))
    return cm, cmon


def plot_raw(cm, title):
    m = cm.groupby(["year", "month"])[["p_modis", "p_viirs_snpp", "n_modis", "n_viirs_snpp"]].sum()
    m.index = pd.to_datetime({"year": m.index.get_level_values(0), "month": m.index.get_level_values(1), "day": 1})
    m = m.sort_index()
    fig, ax = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    for a, (mod, vii, t) in zip(ax, [("p_modis", "p_viirs_snpp", "Raw hotspot points"),
                                      ("n_modis", "n_viirs_snpp", "H3 cell-days")]):
        a.plot(m.index, m[mod], lw=1, label="MODIS (Terra+Aqua)", color="#d95f02")
        v = m[vii].where(m.index >= "2012-01-01")
        a.plot(m.index, v, lw=1, label="VIIRS S-NPP", color="#1b9e77")
        a.set_yscale("symlog", linthresh=10)
        a.set_title(f"{title} — {t}")
        a.axvline(pd.Timestamp("2012-01-01"), color="k", ls="--", lw=0.8)
        a.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(REPORTS / "raw_series.png", dpi=130)
    plt.close(fig)


def main():
    ensure_dirs()
    cfg = load_config()
    man = ingest.load_manifest(cfg)
    con = duckdb.connect()
    con.execute("LOAD h3")
    (AGG / "country_month").mkdir(parents=True, exist_ok=True)
    parts = []
    for c in ingest.countries(cfg, man, "cell"):
        cm, cmon = build(con, cfg, c)
        cmon.to_parquet(AGG / "country_month" / f"{c}.parquet", index=False)
        parts.append(cm)
    allcm = pd.concat(parts, ignore_index=True).sort_values(["country", "h3_cell", "year", "month"],
                                                              ignore_index=True)
    allcm.to_parquet(AGG / "cell_month_all.parquet", index=False)
    train = cfg["train_country"]
    plot_raw(allcm[allcm["country"] == train], train)
    write_json(REPORTS / "adm1_assignment.json", ADM1_LOG)
    log.info("ADM1 assignment: %s", ADM1_LOG)
    log.info("wrote cell_month_all.parquet (%d rows, %d countries)", len(allcm), allcm["country"].nunique())


if __name__ == "__main__":
    main()

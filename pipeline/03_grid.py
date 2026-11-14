"""Aggregate hotspots to H3 cell-days and cell-months per sensor group."""
import duckdb
import h3
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from pipeline.common import AGG, PROCESSED, REPORTS, ensure_dirs, get_logger, load_config, outage_days_sql  # noqa: E402

log = get_logger("grid")

GROUPS = {
    "modis": "sensor = 'MODIS'",
    "modis_terra": "platform = 'Terra'",
    "modis_aqua": "platform = 'Aqua'",
    "viirs_snpp": "platform = 'SNPP'",
    "viirs_noaa20": "platform = 'NOAA20'",
    "viirs_all": "sensor = 'VIIRS'",
}


def cell_month_query(src):
    parts = []
    for g, cond in GROUPS.items():
        parts.append(f"count(DISTINCT CASE WHEN {cond} THEN date END) AS n_{g}")
        parts.append(f"count(DISTINCT CASE WHEN {cond} AND daynight = 'D' THEN date END) AS n_{g}_d")
        parts.append(f"count(DISTINCT CASE WHEN {cond} AND daynight = 'N' THEN date END) AS n_{g}_n")
        parts.append(f"count(CASE WHEN {cond} THEN 1 END) AS p_{g}")
    return f"""
        SELECT h3_cell, CAST(year AS INTEGER) AS year, CAST(month AS INTEGER) AS month, {', '.join(parts)}
        FROM {src} GROUP BY 1, 2, 3 ORDER BY 1, 2, 3"""


def outage_fill(con, src, min_n20):
    """NOAA-20 cell-days per cell-month on S-NPP outage days, and the number of outage days."""
    days = outage_days_sql(src, min_n20)
    gap = con.execute(f"""
        SELECT h3_cell, CAST(year AS INTEGER) AS year, CAST(month AS INTEGER) AS month,
               count(DISTINCT date) AS n_viirs_noaa20_gap
        FROM {src} WHERE platform = 'NOAA20' AND date IN ({days}) GROUP BY 1, 2, 3""").df()
    return gap, con.execute(f"SELECT count(*) FROM ({days})").fetchone()[0]


def build(con, cfg):
    src = f"read_parquet('{(PROCESSED / 'hotspots').as_posix()}/**/*.parquet', hive_partitioning = true)"
    n_in = con.execute(f"SELECT count(*) FROM {src}").fetchone()[0]
    cm = con.execute(cell_month_query(src)).df()
    # days when S-NPP saw nothing region-wide but NOAA-20 did -> outage, filled later from NOAA-20
    gap, n_gap_days = outage_fill(con, src, cfg["calibration"]["snpp_gap_min_noaa20"])
    log.info("S-NPP outage days filled from NOAA-20: %d", n_gap_days)
    cm = cm.merge(gap, on=["h3_cell", "year", "month"], how="left")
    cm["n_viirs_noaa20_gap"] = cm["n_viirs_noaa20_gap"].fillna(0).astype("int64")
    coarse = cfg["grid"]["coarse_res"]
    cells = pd.DataFrame({"h3_cell": cm["h3_cell"].unique()})
    cells["h3_coarse"] = [h3.cell_to_parent(c, coarse) for c in cells["h3_cell"]]
    ll = [h3.cell_to_latlng(c) for c in cells["h3_cell"]]
    cells["lat"] = [a for a, _ in ll]
    cells["lon"] = [b for _, b in ll]
    cm = cm.merge(cells, on="h3_cell")
    log.info("hotspots in: %d, cell-months out: %d, cells: %d", n_in, len(cm), len(cells))
    return cm


def plot_raw(cm):
    m = cm.groupby(["year", "month"])[["p_modis", "p_viirs_snpp", "n_modis", "n_viirs_snpp"]].sum()
    m.index = pd.to_datetime({"year": m.index.get_level_values(0), "month": m.index.get_level_values(1), "day": 1})
    m = m.sort_index()
    fig, ax = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    for a, (mod, vii, title) in zip(ax, [("p_modis", "p_viirs_snpp", "Raw hotspot points"),
                                          ("n_modis", "n_viirs_snpp", "H3 cell-days")]):
        a.plot(m.index, m[mod], lw=1, label="MODIS (Terra+Aqua)", color="#d95f02")
        v = m[vii].where(m.index >= "2012-01-01")
        a.plot(m.index, v, lw=1, label="VIIRS S-NPP", color="#1b9e77")
        a.set_yscale("symlog", linthresh=10)
        a.set_title(title)
        a.axvline(pd.Timestamp("2012-01-01"), color="k", ls="--", lw=0.8)
        a.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(REPORTS / "raw_series.png", dpi=130)
    plt.close(fig)


def main():
    ensure_dirs()
    cfg = load_config()
    con = duckdb.connect()
    cm = build(con, cfg)
    cm.to_parquet(AGG / "cell_month.parquet", index=False)
    plot_raw(cm)
    log.info("wrote cell_month.parquet and raw_series.png")


if __name__ == "__main__":
    main()

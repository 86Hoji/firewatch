import importlib

import duckdb
import numpy as np
import pandas as pd

clean = importlib.import_module("pipeline.02_clean")
grid = importlib.import_module("pipeline.03_grid")


def raw_modis():
    return pd.DataFrame({"latitude": [50.0, 50.0, 50.0, 50.0], "longitude": [70.0] * 4, "brightness": [320] * 4,
                         "scan": [1] * 4, "track": [1] * 4, "acq_date": ["2010-07-01"] * 4,
                         "acq_time": ["0610", "0611", "0612", "0613"], "satellite": ["Terra", "Aqua", "Terra", "Aqua"],
                         "instrument": ["MODIS"] * 4, "confidence": [10, 30, 80, 95], "version": ["6.2"] * 4,
                         "bright_t31": [290] * 4, "frp": [10.0] * 4, "daynight": ["D"] * 4, "type": [0, 0, 2, 0]})


def raw_viirs():
    return pd.DataFrame({"latitude": [50.0] * 4, "longitude": [70.0] * 4, "bright_ti4": [330] * 4, "scan": [.4] * 4,
                         "track": [.4] * 4, "acq_date": ["2013-07-01"] * 4, "acq_time": ["0800", "0801", "0802", "0803"],
                         "satellite": ["N", "N", "N", "1"], "instrument": ["VIIRS"] * 4, "confidence": ["l", "n", "h", "nominal"],
                         "version": ["2", "2", "2.0NRT", "2"], "bright_ti5": [290] * 4, "frp": [3.0] * 4,
                         "daynight": ["D"] * 4, "type": [0, 0, None, 0]})


def test_unify_platforms_and_processing():
    m, v = clean.unify(raw_modis()), clean.unify(raw_viirs())
    assert list(m["platform"]) == ["Terra", "Aqua", "Terra", "Aqua"]
    assert list(v["platform"]) == ["SNPP", "SNPP", "SNPP", "NOAA20"]
    assert list(v["processing"]) == ["SP", "SP", "NRT", "SP"]
    assert list(m["confidence_norm"]) == ["l", "n", "h", "h"]


def test_confidence_and_type_filters(cfg):
    df = pd.concat([clean.unify(raw_modis()), clean.unify(raw_viirs())], ignore_index=True)
    c = clean.confidence_filter(df, cfg)
    assert (c[c["sensor"] == "MODIS"]["confidence"].astype(int) >= 30).all()
    assert len(c[c["sensor"] == "MODIS"]) == 3
    assert set(c[c["sensor"] == "VIIRS"]["confidence_norm"]) == {"n", "h"}
    t = clean.type_filter(c, cfg)
    assert not (t["type"] == 2).any()
    assert t["type"].isna().sum() == 1      # NRT row without type is kept for the static mask step


def test_cell_day_dedup(tmp_path):
    rows = pd.DataFrame({"h3_cell": ["a", "a", "a", "a", "b"], "year": [2013] * 5, "month": [7] * 5,
                         "date": pd.to_datetime(["2013-07-01", "2013-07-01", "2013-07-02", "2013-07-01", "2013-07-01"]).date,
                         "sensor": ["VIIRS"] * 4 + ["MODIS"], "platform": ["SNPP", "SNPP", "SNPP", "NOAA20", "Aqua"],
                         "daynight": ["D", "N", "D", "D", "D"]})
    p = tmp_path / "h.parquet"
    rows.to_parquet(p)
    cm = duckdb.connect().execute(grid.cell_month_query(f"read_parquet('{p.as_posix()}')")).df().set_index("h3_cell")
    assert cm.loc["a", "n_viirs_snpp"] == 2       # 3 S-NPP points on 2 days
    assert cm.loc["a", "p_viirs_snpp"] == 3
    assert cm.loc["a", "n_viirs_all"] == 2        # NOAA-20 on an S-NPP day adds nothing
    assert cm.loc["a", "n_viirs_snpp_d"] == 2 and cm.loc["a", "n_viirs_snpp_n"] == 1
    assert cm.loc["b", "n_modis"] == 1 and cm.loc["b", "n_modis_aqua"] == 1 and cm.loc["b", "n_modis_terra"] == 0


def test_country_month_equals_sum_of_cell_months(tmp_path):
    """Transfer countries get country-month totals straight from points; they must equal summed cell-months."""
    from pipeline import ingest
    rng = np.random.default_rng(1)
    n = 3000
    df = pd.DataFrame({"h3_cell": rng.choice(list("abcdefgh"), n),
                       "date": pd.to_datetime("2019-01-01") + pd.to_timedelta(rng.integers(0, 120, n), unit="D"),
                       "platform": rng.choice(["Terra", "Aqua", "SNPP", "NOAA20", "NOAA21"], n),
                       "daynight": rng.choice(["D", "N"], n)})
    df["date"] = df["date"].dt.date
    df["sensor"] = np.where(df["platform"].isin(["Terra", "Aqua"]), "MODIS", "VIIRS")
    df["year"], df["month"] = [d.year for d in df["date"]], [d.month for d in df["date"]]
    p = tmp_path / "h.parquet"
    df.to_parquet(p)
    src = f"read_parquet('{p.as_posix()}')"
    con = duckdb.connect()
    cm = con.execute(ingest.cell_month_query(src)).df()
    gap, _ = ingest.outage_fill(con, src, 1)
    cm = cm.merge(gap, on=["h3_cell", "year", "month"], how="left").fillna({"n_viirs_noaa20_gap": 0})
    tot = con.execute(ingest.country_month_query(src, 1)).df().set_index(["year", "month"])
    s = cm.groupby(["year", "month"])[[c for c in cm.columns if c.startswith(("n_", "p_"))]].sum()
    assert (s - tot[s.columns]).abs().to_numpy().max() == 0

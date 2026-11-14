"""API on a tiny SYNTHETIC dataset written to a temp dir."""
import json

import h3
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import main as api
from pipeline import intervals


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    agg, ref, proc = tmp / "agg", tmp / "ref", tmp / "proc"
    for d in (agg, ref, proc / "hotspots"):
        d.mkdir(parents=True)
    a = h3.latlng_to_cell(50.0, 70.0, 7)
    b = h3.latlng_to_cell(45.0, 80.0, 7)
    rows = []
    for cell, scale in ((a, 1.0), (b, 3.0)):
        lat, lon = h3.cell_to_latlng(cell)
        for y in range(2010, 2015):
            for m in range(1, 13):
                if y == 2014 and m > 3:
                    continue
                v = scale * (m + 1)
                rows.append({"h3_cell": cell, "year": y, "month": m, "lat": lat, "lon": lon,
                             "n_harm": v, "n_harm_low": v * .8, "n_harm_high": v * 1.2,
                             "p_modis": v, "p_viirs_snpp": 3 * v, "n_modis": v, "n_viirs_snpp": 2 * v,
                             "k_applied": 2.0, "source": "MODIS_calibrated" if y < 2012 else "VIIRS_SNPP"})
    pd.DataFrame(rows).to_parquet(agg / "cell_month.parquet")
    (agg / "meta.json").write_text(json.dumps({"region": "Test", "first_date": "2010-01-01", "last_date": "2014-03-10",
                                               "model": "ratio", "h3_res": 7, "coef_version": "t"}))
    pd.DataFrame({"sensor": ["VIIRS"], "platform": ["SNPP"], "lat": [50.0], "lon": [70.0],
                  "datetime_utc": [pd.Timestamp("2013-07-01 08:00")], "date": [pd.Timestamp("2013-07-01").date()],
                  "year": [2013], "month": [7], "daynight": ["D"], "confidence": ["n"], "confidence_norm": ["n"],
                  "frp": [5.0], "type": [0.0], "processing": ["SP"], "h3_cell": [a]}) \
        .to_parquet(proc / "hotspots" / "part.parquet")
    api.load_state(agg=agg, ref=ref, processed=proc)
    return TestClient(api.app)


def test_calendar_small_bbox_shapes(client):
    r = client.post("/api/calendar", json={"bbox": [69.5, 49.5, 70.5, 50.5]})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["years"] == [2010, 2011, 2012, 2013, 2014]
    assert len(j["values"]) == 5 and all(len(row) == 12 for row in j["values"])
    assert j["values"][0][0] == 2.0          # only cell a: 1 * (1 + 1)
    assert j["values"][4][5] is None         # after last date
    assert j["source"][0][0] == "MODIS_calibrated" and j["source"][3][0] == "VIIRS_SNPP"
    assert j["partial"]["month"] == 3


def test_whole_region_sums_both_cells(client):
    j = client.post("/api/calendar", json={}).json()
    assert j["values"][0][0] == 8.0          # 2 + 6


def test_empty_area_is_clear_error(client):
    r = client.post("/api/calendar", json={"bbox": [10, 10, 11, 11]})
    assert r.status_code == 404 and "no hotspots" in r.json()["detail"]


def test_bad_bbox_rejected(client):
    assert client.post("/api/calendar", json={"bbox": [71, 50, 70, 51]}).status_code == 422


def test_anomaly_partial_month_is_normalized(client):
    j = client.post("/api/anomaly", json={"year": 2014, "month": 3}).json()
    assert j["partial"] is True and j["days_elapsed"] == 10 and j["days_in_month"] == 31
    assert abs(j["value_normalized"] - j["value"] * 31 / 10) < 1e-6
    full = client.post("/api/anomaly", json={"year": 2013, "month": 3}).json()
    assert full["partial"] is False and full["value_normalized"] == full["value"]


def test_yearly_ranks_only_complete_years(client):
    yrs = {y["year"]: y for y in client.post("/api/yearly", json={}).json()["years"]}
    assert yrs[2014]["rank"] is None and yrs[2014]["complete"] is False
    assert sorted(y["rank"] for y in yrs.values() if y["rank"]) == [1, 1, 1, 1]


def test_point_radius_and_export(client):
    r = client.post("/api/export.csv", json={"point": [50.0, 70.0], "radius_km": 20})
    assert r.status_code == 200
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("date,time,lat,lon,sensor,platform")
    assert len(lines) == 2 and ",1.0," in lines[1]


IV = {"level": 0.9,
      "country": {"method": "hetero_log_ratio", "q_lo": -0.2, "q_hi": 0.2, "median_pred": 10.0},
      "region": {"method": "binned_log1p", "inner_edges": [5.0, 20.0],
                 "q_lo": [0.0, -0.5, -0.3, -0.2], "q_hi": [2.0, 1.5, 0.8, 0.4]}}


def test_intervals_sized_on_area_total_not_summed(client, monkeypatch):
    monkeypatch.setitem(api.S.meta, "intervals", IV)
    whole = client.post("/api/calendar", json={}).json()
    lo, hi = intervals.bounds([whole["values"][0][0]], IV["country"])      # 2010-01, both cells: 8
    assert (whole["low"][0][0], whole["high"][0][0]) == (lo[0], hi[0])
    small = client.post("/api/calendar", json={"bbox": [69.5, 49.5, 70.5, 50.5]}).json()
    lo, hi = intervals.bounds([small["values"][0][0]], IV["region"])       # cell a only: 2
    assert (small["low"][0][0], small["high"][0][0]) == (lo[0], hi[0])
    assert whole["low"][3][0] == whole["values"][3][0] == whole["high"][3][0]   # 2013: observed VIIRS
    y2010 = {y["year"]: y for y in client.post("/api/yearly", json={}).json()["years"]}[2010]
    lo, hi = intervals.bounds(whole["values"][0], IV["country"])
    assert (y2010["low"], y2010["high"]) == (lo.sum(), hi.sum())

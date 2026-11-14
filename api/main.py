"""FastAPI service over pre-aggregated H3 cell-months (DuckDB in memory)."""
import calendar
import datetime as dt
import io
import json
from functools import lru_cache
from typing import Literal

import duckdb
import h3
import numpy as np
import pandas as pd
import shapely
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator
from shapely.geometry import box, shape

from pipeline.common import AGG, PROCESSED, REF, REPORTS, ROOT, load_config, outage_days_sql

CFG = load_config()
MODES = {"harmonized": "n_harm", "raw_modis": "p_modis", "raw_viirs": "p_viirs_snpp", "naive": None, "modis_cells": "n_modis"}
UNITS = {"harmonized": "cell-days (VIIRS S-NPP equivalent)", "raw_modis": "MODIS hotspot points",
         "raw_viirs": "VIIRS S-NPP hotspot points", "naive": "hotspot points (MODIS until 2011, VIIRS after)",
         "modis_cells": "MODIS cell-days (unharmonized)"}


class State:
    con: duckdb.DuckDBPyConnection
    cells: pd.DataFrame
    meta: dict
    regions: dict
    cut: int


S = State()


def load_state(agg=AGG, ref=REF, processed=PROCESSED):
    S.con = duckdb.connect()
    cm = pd.read_parquet(agg / "cell_month.parquet")
    if "n_harm" not in cm:
        raise RuntimeError("cell_month.parquet is not harmonized; run the pipeline")
    if "n_viirs_noaa20_gap" not in cm:
        cm["n_viirs_noaa20_gap"] = 0
    S.con.register("cm_df", cm)
    S.con.execute("CREATE TABLE cm AS SELECT * FROM cm_df")
    S.con.unregister("cm_df")
    S.cells = cm[["h3_cell", "lat", "lon"]].drop_duplicates("h3_cell").reset_index(drop=True)
    S.meta = json.loads((agg / "meta.json").read_text(encoding="utf-8"))
    S.cut = CFG["calibration"]["period"][0]
    by_country = processed / "hotspots" / f"country={CFG['train_country']}"
    S.hotspots = (by_country if by_country.is_dir() else processed / "hotspots").as_posix()
    # S-NPP outage days (same rule as 03_grid): NOAA-20 points stand in for S-NPP on the map
    try:
        src = f"read_parquet('{S.hotspots}/**/*.parquet', hive_partitioning = true)"
        S.gap_dates = [str(d) for (d,) in S.con.execute(
            outage_days_sql(src, CFG["calibration"]["snpp_gap_min_noaa20"])).fetchall()]
    except duckdb.Error:
        S.gap_dates = []
    S.regions = {}
    gj = ref / "regions.geojson"
    if gj.exists():
        for i, f in enumerate(json.loads(gj.read_text(encoding="utf-8"))["features"]):
            p = f["properties"]
            rid = str(p.get("shapeISO") or p.get("shapeID") or i)
            g = shapely.simplify(shape(f["geometry"]), 0.01, preserve_topology=True)
            S.regions[rid] = {"id": rid, "name": p.get("shapeName", rid), "geometry": g}
    _region_cells.cache_clear()


app = FastAPI(title="Fire Regimes — harmonized MODIS + VIIRS calendar", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def _revalidate_static(request, call_next):
    resp = await call_next(request)
    if not request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.on_event("startup")
def _startup():
    if not hasattr(S, "con"):
        load_state()


class Query(BaseModel):
    geometry: dict | None = None
    bbox: list[float] | None = Field(None, description="west,south,east,north")
    point: list[float] | None = Field(None, description="lat,lon")
    radius_km: float | None = Field(None, gt=0, le=1000)
    region_id: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    mode: Literal["harmonized", "raw_modis", "raw_viirs", "naive", "modis_cells"] = "harmonized"
    year: int | None = None
    month: int | None = Field(None, ge=1, le=12)
    base_start: int | None = None
    base_end: int | None = None

    @field_validator("bbox")
    @classmethod
    def _bbox(cls, v):
        if v is not None and (len(v) != 4 or v[0] >= v[2] or v[1] >= v[3]):
            raise ValueError("bbox must be west,south,east,north with west<east and south<north")
        return v

    @model_validator(mode="after")
    def _area(self):
        given = [self.geometry is not None, self.bbox is not None, self.point is not None, self.region_id is not None]
        if sum(given) > 1:
            raise ValueError("give only one of geometry, bbox, point, region_id")
        if self.point is not None and (len(self.point) != 2 or not self.radius_km):
            raise ValueError("point needs [lat, lon] and radius_km")
        if self.start_year and self.end_year and self.start_year > self.end_year:
            raise ValueError("start_year must be <= end_year")
        return self


def _circle(lat, lon, km):
    ang = np.linspace(0, 2 * np.pi, 72)
    dlat = km / 111.32 * np.sin(ang)
    dlon = km / (111.32 * np.cos(np.radians(lat))) * np.cos(ang)
    return shapely.Polygon(np.column_stack([lon + dlon, lat + dlat]))


def area_geometry(q: Query):
    if q.region_id is not None:
        if q.region_id not in S.regions:
            raise HTTPException(404, f"unknown region_id {q.region_id!r}")
        return S.regions[q.region_id]["geometry"]
    if q.bbox:
        return box(*q.bbox)
    if q.point:
        return _circle(q.point[0], q.point[1], q.radius_km)
    if q.geometry:
        try:
            g = shape(q.geometry.get("geometry", q.geometry))
        except Exception as e:
            raise HTTPException(422, f"invalid GeoJSON geometry: {e}")
        if not g.is_valid:
            g = shapely.make_valid(g)
        return g
    return None


@lru_cache(maxsize=256)
def _region_cells(wkb):
    g = shapely.from_wkb(wkb)
    shapely.prepare(g)
    inside = shapely.contains_xy(g, S.cells["lon"].to_numpy(), S.cells["lat"].to_numpy())
    return tuple(S.cells.loc[inside, "h3_cell"])


def select_cells(q: Query):
    """H3 cells (with data) whose centre lies in the area — same rule as h3.geo_to_cells."""
    g = area_geometry(q)
    if g is None:
        return None
    cells = _region_cells(shapely.to_wkb(g))
    if not cells:
        raise HTTPException(404, "no hotspots were ever recorded inside this area (or it lies outside the data region)")
    if len(cells) > CFG["api"]["max_cells"] * 5:
        raise HTTPException(413, "area too large")
    return cells


def year_range(q: Query):
    first = dt.date.fromisoformat(S.meta["first_date"][:10])
    last = dt.date.fromisoformat(S.meta["last_date"][:10])
    y0, y1 = q.start_year or first.year, q.end_year or last.year
    if y1 < first.year or y0 > last.year:
        raise HTTPException(422, f"data covers {first.year}–{last.year}")
    return max(y0, first.year), min(y1, last.year), first, last


def monthly(cells, y0, y1):
    cur = S.con.cursor()
    where = f"year BETWEEN {int(y0)} AND {int(y1)}"
    if cells is not None:
        cur.register("sel_df", pd.DataFrame({"h3_cell": list(cells)}))
        where += " AND h3_cell IN (SELECT h3_cell FROM sel_df)"
    return cur.execute(f"""
        SELECT year, month, sum(n_harm) n_harm, sum(n_harm_low) n_harm_low, sum(n_harm_high) n_harm_high,
               sum(p_modis) p_modis, sum(p_viirs_snpp) p_viirs_snpp, sum(n_modis) n_modis,
               sum(n_viirs_snpp) n_viirs_snpp, sum(coalesce(n_viirs_noaa20_gap, 0)) n_viirs_noaa20_gap,
               count(DISTINCT h3_cell) cells
        FROM cm WHERE {where} GROUP BY 1, 2""").df()


def grid(q: Query):
    """Full year x month frame with zeros inside the data period and NaN outside."""
    y0, y1, first, last = year_range(q)
    cells = select_cells(q)
    m = monthly(cells, y0, y1)
    idx = pd.MultiIndex.from_product([range(y0, y1 + 1), range(1, 13)], names=["year", "month"])
    f = m.set_index(["year", "month"]).reindex(idx).fillna(0).reset_index()
    ym = f["year"] * 12 + f["month"]
    out = (ym < first.year * 12 + first.month) | (ym > last.year * 12 + last.month)
    f.loc[out, f.columns.difference(["year", "month"])] = np.nan
    if q.mode == "naive":
        f["value"] = np.where(f["year"] < S.cut, f["p_modis"], f["p_viirs_snpp"])
    else:
        f["value"] = f[MODES[q.mode]]
    if q.mode == "raw_viirs":
        f.loc[f["year"] < S.cut, "value"] = np.nan
    f["source"] = np.where(f["value"].isna(), None, np.where(f["year"] < S.cut, "MODIS_calibrated", "VIIRS_SNPP"))
    if q.mode != "harmonized":
        f["source"] = np.where(f["value"].isna(), None, q.mode)
    f["partial"] = (f["year"] == last.year) & (f["month"] == last.month) & \
                   (last.day < calendar.monthrange(last.year, last.month)[1])
    return f, cells, last


def _clean(v, nd=2):
    return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), nd)


def base_stats(f, q, last):
    b0 = q.base_start or CFG["api"]["base_period_start"]
    b1 = q.base_end or (last.year if last.month == 12 and not f["partial"].any() else last.year - 1)
    base = f[f["year"].between(b0, b1)]
    st = base.groupby("month")["value"].agg(median="median", p25=lambda s: s.quantile(.25),
                                            p75=lambda s: s.quantile(.75), mean="mean", std="std")
    return st, (b0, b1), base


@app.get("/api/meta")
def meta():
    return {**S.meta, "cells": int(len(S.cells)), "calibration_start": S.cut,
            "modes": UNITS, "validation": "/reports/validation.md"}


@app.get("/api/regions")
def regions():
    return [{"id": r["id"], "name": r["name"], "bbox": list(r["geometry"].bounds),
             "geometry": shapely.geometry.mapping(r["geometry"])} for r in S.regions.values()]


@app.post("/api/calendar")
def calendar_ep(q: Query):
    f, cells, last = grid(q)
    st, base, _ = base_stats(f, q, last)
    years = sorted(f["year"].unique().tolist())

    def mat(col, nd=2):
        return [[_clean(v, nd) if not isinstance(v, str) else v for v in f.loc[f["year"] == y, col]] for y in years]

    med = st["median"].reindex(range(1, 13))
    anom = [[_clean(100 * (v / med[m] - 1), 1) if med[m] and np.isfinite(v) else None
             for m, v in zip(range(1, 13), f.loc[f["year"] == y, "value"])] for y in years]
    low = mat("n_harm_low") if q.mode == "harmonized" else mat("value")
    high = mat("n_harm_high") if q.mode == "harmonized" else mat("value")
    return {"years": years, "months": list(range(1, 13)), "values": mat("value"),
            "source": [[s if isinstance(s, str) else None for s in f.loc[f["year"] == y, "source"]] for y in years],
            "low": low, "high": high, "anomaly_pct": anom, "median": [_clean(v) for v in med],
            "base_period": base, "mode": q.mode, "unit": UNITS[q.mode],
            "partial": {"year": last.year, "month": last.month, "days": last.day,
                        "days_in_month": calendar.monthrange(last.year, last.month)[1]} if f["partial"].any() else None,
            "cells": len(cells) if cells is not None else int(len(S.cells)), "last_date": str(last)}


@app.post("/api/anomaly")
def anomaly(q: Query):
    f, _, last = grid(q)
    st, base, basef = base_stats(f, q, last)
    y = q.year or last.year
    mth = q.month or last.month
    row = f[(f["year"] == y) & (f["month"] == mth)]
    if row.empty or not np.isfinite(row["value"].iloc[0]):
        raise HTTPException(422, f"no data for {y}-{mth:02d}")
    v = float(row["value"].iloc[0])
    partial = bool(row["partial"].iloc[0])
    dim = calendar.monthrange(y, mth)[1]
    v_norm = v * dim / last.day if partial else v
    hist = basef.loc[(basef["month"] == mth) & (basef["year"] != y), "value"].dropna().to_numpy()
    s = st.loc[mth]
    pct = float(100 * (np.sum(hist < v_norm) + 0.5 * np.sum(hist == v_norm)) / len(hist)) if len(hist) else None
    by_month = [{"month": m, "value": _clean(f.loc[(f["year"] == y) & (f["month"] == m), "value"].iloc[0]),
                 "median": _clean(st.loc[m, "median"]), "p25": _clean(st.loc[m, "p25"]), "p75": _clean(st.loc[m, "p75"])}
                for m in range(1, 13)]
    return {"year": y, "month": mth, "value": _clean(v), "value_normalized": _clean(v_norm), "partial": partial,
            "days_elapsed": last.day if partial else dim, "days_in_month": dim,
            "median": _clean(s["median"]), "p25": _clean(s["p25"]), "p75": _clean(s["p75"]),
            "pct_vs_median": _clean(100 * (v_norm / s["median"] - 1), 1) if s["median"] else None,
            "z": _clean((v_norm - s["mean"]) / s["std"], 2) if s["std"] else None,
            "percentile": _clean(pct, 0), "base_period": base, "by_month": by_month, "unit": UNITS[q.mode],
            "noaa20_fill_share": _clean(_fill_share(row.iloc[0]), 3)}


def _fill_share(r):
    """Share of the month's VIIRS cell-days that come from NOAA-20 on S-NPP outage days."""
    tot = r["n_viirs_snpp"] + r["n_viirs_noaa20_gap"]
    return r["n_viirs_noaa20_gap"] / tot if r["year"] >= S.cut and tot > 0 else 0.0


@app.post("/api/yearly")
def yearly(q: Query):
    f, _, last = grid(q)
    a = f.groupby("year").agg(value=("value", "sum"), low=("n_harm_low", "sum"), high=("n_harm_high", "sum"),
                              months=("value", "count")).reset_index()
    full = a["months"].eq(12) & ~a["year"].isin(f.loc[f["partial"], "year"])
    a["rank"] = a["value"].where(full).rank(ascending=False, method="min")
    return {"unit": UNITS[q.mode], "years": [
        {"year": int(r["year"]), "value": _clean(r["value"]), "low": _clean(r["low"]), "high": _clean(r["high"]),
         "rank": None if np.isnan(r["rank"]) else int(r["rank"]), "complete": bool(full[i]),
         "source": "MODIS_calibrated" if r["year"] < S.cut else "VIIRS_SNPP"} for i, r in a.iterrows()]}


@app.post("/api/seasonal")
def seasonal(q: Query):
    f, _, last = grid(q)
    st, base, _ = base_stats(f, q, last)
    peak = int(st["median"].idxmax()) if st["median"].max() > 0 else None
    share = st["median"] / st["median"].sum() if st["median"].sum() else st["median"] * 0
    return {"base_period": base, "peak_month": peak, "unit": UNITS[q.mode], "months": [
        {"month": int(m), "median": _clean(r["median"]), "p25": _clean(r["p25"]), "p75": _clean(r["p75"]),
         "share": _clean(share[m], 4)} for m, r in st.iterrows()]}


def _csv_response(df, name):
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.post("/api/export.csv")
def export_points(q: Query):
    cur = S.con.cursor()
    y0, y1, _, _ = year_range(q)
    cells = select_cells(q)
    cur.register("sel_df", pd.DataFrame({"h3_cell": list(cells) if cells is not None else S.cells["h3_cell"]}))
    src = f"read_parquet('{S.hotspots}/**/*.parquet', hive_partitioning = true)"
    month = f"AND h.month = {int(q.month)}" if q.month else ""
    n = cur.execute(f"SELECT count(*) FROM {src} h WHERE CAST(h.year AS INT) BETWEEN {y0} AND {y1} {month} "
                      f"AND h.h3_cell IN (SELECT h3_cell FROM sel_df)").fetchall()[0][0]
    if n > CFG["api"]["max_export_rows"]:
        cur.unregister("sel_df")
        raise HTTPException(413, f"{n} points: narrow the area or period (limit {CFG['api']['max_export_rows']})")
    df = cur.execute(f"""
        SELECT h.date, strftime(h.datetime_utc, '%H:%M') AS time, h.lat, h.lon, h.sensor, h.platform,
               h.confidence, h.frp, h.daynight, h.h3_cell,
               CASE WHEN h.sensor = 'MODIS' THEN round(c.k_applied, 4) WHEN h.platform = 'SNPP' THEN 1.0 END
                   AS harmonization_weight,
               (h.sensor = 'MODIS' AND CAST(h.year AS INT) < {S.cut})
                   OR (h.platform = 'SNPP' AND CAST(h.year AS INT) >= {S.cut}) AS in_harmonized_series
        FROM {src} h LEFT JOIN cm c ON c.h3_cell = h.h3_cell AND c.year = CAST(h.year AS INT) AND c.month = h.month
        WHERE CAST(h.year AS INT) BETWEEN {y0} AND {y1} {month} AND h.h3_cell IN (SELECT h3_cell FROM sel_df)
        ORDER BY h.datetime_utc""").df()
    cur.unregister("sel_df")
    return _csv_response(df, f"hotspots_{y0}_{y1}.csv")


@app.post("/api/export_calendar.csv")
def export_calendar(q: Query):
    f, _, _ = grid(q)
    cols = ["year", "month", "value", "n_harm_low", "n_harm_high", "source", "p_modis", "p_viirs_snpp",
            "n_modis", "n_viirs_snpp", "partial"]
    return _csv_response(f[cols].rename(columns={"value": q.mode, "n_harm_low": "low", "n_harm_high": "high"}),
                         f"calendar_{q.mode}.csv")


@app.post("/api/points")
def points(q: Query):
    cur = S.con.cursor()
    if not (q.year and q.month):
        raise HTTPException(422, "year and month are required")
    cells = select_cells(q)
    cur.register("sel_df", pd.DataFrame({"h3_cell": list(cells) if cells is not None else S.cells["h3_cell"]}))
    src = f"read_parquet('{S.hotspots}/sensor=*/year={int(q.year)}/*.parquet', hive_partitioning = true)"
    gaps = ", ".join(f"DATE '{d}'" for d in S.gap_dates) or "NULL"
    plat = (f"(h.platform = 'SNPP' OR (h.platform = 'NOAA20' AND h.date IN ({gaps})))"
            if q.year >= S.cut else "h.sensor = 'MODIS'")
    df = cur.execute(f"""SELECT round(h.lat, 4) lat, round(h.lon, 4) lon, round(h.frp, 1) frp, h.platform, h.date
        FROM {src} h WHERE h.month = {int(q.month)} AND {plat} AND h.h3_cell IN (SELECT h3_cell FROM sel_df)
        LIMIT 30000""").df()
    cur.unregister("sel_df")
    return {"year": q.year, "month": q.month, "n": len(df),
            "points": df[["lat", "lon", "frp"]].to_numpy().tolist(), "platform": "+".join(sorted(df["platform"].unique())) if len(df) else None}


@app.post("/api/hexes")
def hexes(q: Query):
    """Coarse H3 intensity layer: harmonized cell-days per coarse cell for the period (or one month)."""
    cur = S.con.cursor()
    y0, y1, _, _ = year_range(q)
    cells = select_cells(q)
    res = CFG["grid"]["coarse_res"] if (cells is None or len(cells) > 4000) else CFG["grid"]["h3_res"] - 1
    cur.register("sel_df", pd.DataFrame({"h3_cell": list(cells) if cells is not None else S.cells["h3_cell"]}))
    month = f"AND month = {int(q.month)}" if q.month else ""
    yrs = f"year = {int(q.year)}" if q.year else f"year BETWEEN {y0} AND {y1}"
    df = cur.execute(f"SELECT h3_cell, sum(n_harm) v FROM cm WHERE {yrs} {month} "
                       f"AND h3_cell IN (SELECT h3_cell FROM sel_df) GROUP BY 1").df()
    cur.unregister("sel_df")
    df["p"] = [h3.cell_to_parent(c, res) for c in df["h3_cell"]]
    g = df.groupby("p")["v"].sum()
    g = g[g > 0]
    def ring(c):
        pts = [[lo, la] for la, lo in h3.cell_to_boundary(c)]
        return pts + pts[:1]

    feats = [{"type": "Feature", "properties": {"v": round(float(v), 1)},
              "geometry": {"type": "Polygon", "coordinates": [ring(c)]}} for c, v in g.items()]
    return {"type": "FeatureCollection", "features": feats, "res": res}


app.mount("/reports", StaticFiles(directory=REPORTS), name="reports")


@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")


if (ROOT / "web").is_dir():   # frontend is optional; the API works without it
    app.mount("/", StaticFiles(directory=ROOT / "web"), name="web")

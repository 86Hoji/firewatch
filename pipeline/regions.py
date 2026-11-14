"""ADM1 (oblast / province) for every H3 cell, from data/boundaries/{ISO3}_ADM1.geojson (geoBoundaries, CRS84).

Rule: the cell centre inside a polygon -> that region ('inside'); otherwise the nearest region if it is within
regions.nearest_km ('nearest', e.g. a fire on a border river or a coastline simplified in the boundary file);
otherwise 'outside' (FIRMS clips countries with its own, slightly different border). Vectorized (STRtree joins).
"""
import geopandas as gpd
import numpy as np

from pipeline.common import ROOT


def load_adm1(cfg, country):
    p = ROOT / cfg["regions"]["boundaries_dir"] / f"{country}_ADM1.geojson"
    if not p.exists():
        return None
    g = gpd.read_file(p)[["shapeISO", "shapeID", "shapeName", "geometry"]]
    g["adm1_id"] = g["shapeISO"].where(g["shapeISO"].fillna("").str.len() > 0, g["shapeID"])
    return g.rename(columns={"shapeName": "adm1_name"})[["adm1_id", "adm1_name", "geometry"]].to_crs("EPSG:4326")


def assign(cfg, country, cells):
    """cells: DataFrame h3_cell, lat, lon -> + adm1_id, adm1_name, adm1_method, adm1_dist_km."""
    out = cells[["h3_cell", "lat", "lon"]].copy()
    adm = load_adm1(cfg, country)
    if adm is None:
        out["adm1_id"], out["adm1_name"], out["adm1_method"], out["adm1_dist_km"] = "outside", "outside", "no_file", np.nan
        return out
    pts = gpd.GeoDataFrame(out[["h3_cell"]], geometry=gpd.points_from_xy(out["lon"], out["lat"]), crs="EPSG:4326")
    j = gpd.sjoin(pts, adm, predicate="within", how="left").reset_index()
    # a centre exactly on a shared border can match two polygons: keep the first region id (deterministic)
    j = j.sort_values(["index", "adm1_id"]).drop_duplicates("index").set_index("index").sort_index()
    out["adm1_id"], out["adm1_name"] = j["adm1_id"].to_numpy(), j["adm1_name"].to_numpy()
    out["adm1_method"] = np.where(out["adm1_id"].notna(), "inside", None)
    out["adm1_dist_km"] = np.where(out["adm1_id"].notna(), 0.0, np.nan)
    miss = out["adm1_id"].isna().to_numpy()
    if miss.any():
        c = adm.union_all().centroid
        crs = f"+proj=aeqd +lat_0={c.y:.4f} +lon_0={c.x:.4f} +units=m"     # country-centred, metres
        near = gpd.sjoin_nearest(pts[miss].to_crs(crs), adm.to_crs(crs), how="left",
                                 max_distance=cfg["regions"]["nearest_km"] * 1000, distance_col="d").reset_index()
        near = near.sort_values(["index", "d", "adm1_id"]).drop_duplicates("index").set_index("index")
        idx = np.flatnonzero(miss)
        got = near.reindex(out.index[idx])
        ok = got["adm1_id"].notna().to_numpy()
        out.loc[out.index[idx[ok]], "adm1_id"] = got["adm1_id"].to_numpy()[ok]
        out.loc[out.index[idx[ok]], "adm1_name"] = got["adm1_name"].to_numpy()[ok]
        out.loc[out.index[idx[ok]], "adm1_method"] = "nearest"
        out.loc[out.index[idx[ok]], "adm1_dist_km"] = got["d"].to_numpy()[ok] / 1000
    rest = out["adm1_id"].isna()
    out.loc[rest, ["adm1_id", "adm1_name", "adm1_method"]] = "outside"
    return out


def summary(assigned):
    return assigned.groupby("adm1_method").size().to_dict()


def regional_share(cm, col="n_modis", years=None, key="adm1_id"):
    d = cm if years is None else cm[cm["year"].between(*years)]
    s = d.groupby(key)[col].sum()
    return (s / s.sum()).rename("share").reset_index()


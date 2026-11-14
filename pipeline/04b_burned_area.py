"""Optional: monthly burned area (MCD64A1 C6.1, 500 m sinusoidal tiles) inside the region.

Reads data/reference/mcd64a1/MCD64A1.AYYYYDDD.hHHvVV.061.*.hdf, counts pixels with Burn Date > 0 whose centre lies
in the region (union of regions.geojson), writes data/reference/burned_area_monthly.parquet
(year, month, burned_km2, burned_pixels, tiles). Skipped when no tiles are present.
"""
import json
import re

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import shape

from pipeline.common import REF, get_logger, load_config

log = get_logger("burned_area")

R = 6371007.181                       # MODIS sinusoidal sphere radius, m
TILE = 1111950.5197665233             # tile size, m
N = 2400                              # 500 m product: 2400 x 2400 pixels per tile
PIX = TILE / N
X0, Y0 = -20015109.354, 10007554.677  # upper-left corner of the global grid
NAME = re.compile(r"MCD64A1\.A(\d{4})(\d{3})\.h(\d{2})v(\d{2})\.")


def pixel_latlon(h, v, rows, cols):
    """Centres of sinusoidal pixels (row, col) in tile hHHvVV -> (lat, lon) degrees."""
    x = X0 + h * TILE + (cols + 0.5) * PIX
    y = Y0 - v * TILE - (rows + 0.5) * PIX
    lat = y / R
    lon = x / (R * np.cos(lat))
    return np.degrees(lat), np.degrees(lon)


def region_geometry():
    gj = json.loads((REF / "regions.geojson").read_text(encoding="utf-8"))
    g = shapely.union_all([shape(f["geometry"]) for f in gj["features"]])
    shapely.prepare(g)
    return g


def read_burn_date(path):
    from pyhdf.SD import SD, SDC
    return SD(str(path), SDC.READ).select("Burn Date")[:]


def tile_month(path, region, bbox):
    m = NAME.search(path.name)
    year, doy, h, v = (int(x) for x in m.groups())
    month = (pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(days=doy - 1)).month
    bd = read_burn_date(path)
    rows, cols = np.nonzero(bd > 0)
    if len(rows) == 0:
        return year, month, 0
    lat, lon = pixel_latlon(h, v, rows, cols)
    w, s, e, n = bbox
    pre = (lon >= w) & (lon <= e) & (lat >= s) & (lat <= n)
    inside = shapely.contains_xy(region, lon[pre], lat[pre])
    return year, month, int(inside.sum())


def main():
    files = sorted((REF / "mcd64a1").glob("MCD64A1*.hdf"))
    if not files:
        log.info("no MCD64A1 tiles in %s: skipping burned area (optional)", REF / "mcd64a1")
        return
    try:
        import pyhdf  # noqa: F401
    except ImportError:
        log.warning("pyhdf not installed: skipping burned area")
        return
    cfg = load_config()
    region = region_geometry()
    rows, bad = [], 0
    for p in files:
        try:
            rows.append((*tile_month(p, region, cfg["region"]["bbox"]), p.name))
        except Exception as e:  # corrupt/partial download
            bad += 1
            log.warning("skip %s: %s", p.name, e)
    df = pd.DataFrame(rows, columns=["year", "month", "burned_pixels", "file"])
    out = df.groupby(["year", "month"]).agg(burned_pixels=("burned_pixels", "sum"), tiles=("file", "count")).reset_index()
    out["burned_km2"] = out["burned_pixels"] * (PIX / 1000) ** 2
    out.to_parquet(REF / "burned_area_monthly.parquet", index=False)
    log.info("tiles in: %d (unreadable %d), months out: %d, tiles per month: %s", len(files), bad, len(out),
             sorted(out["tiles"].unique().tolist()))


if __name__ == "__main__":
    main()

import importlib

import numpy as np

ba = importlib.import_module("pipeline.04b_burned_area")
lc = importlib.import_module("pipeline.04_landcover")


def test_sinusoidal_tile_corners():
    # h20v03 upper-left corner = 60°N, 40°E; tile edge lies on 50°N
    lat, lon = ba.pixel_latlon(20, 3, np.array([0, 2399]), np.array([0, 0]))
    assert abs(lat[0] - 60) < 0.01 and abs(lon[0] - 40) < 0.02
    assert abs(lat[1] - 50) < 0.01
    # equator, prime meridian: h18v09 upper-left = (0, 0)
    lat, lon = ba.pixel_latlon(18, 9, np.array([0]), np.array([0]))
    assert abs(lat[0]) < 0.01 and abs(lon[0]) < 0.01


def test_kazakhstan_tiles_cover_bbox():
    # every bbox corner falls in one of the tiles listed in the README (h20-h23 v03, h20-h24 v04)
    for lat, lon in [(55.5, 46.4), (55.5, 87.4), (40.5, 46.4), (40.5, 87.4)]:
        x = np.radians(lon) * ba.R * np.cos(np.radians(lat))
        y = np.radians(lat) * ba.R
        h, v = int((x - ba.X0) // ba.TILE), int((ba.Y0 - y) // ba.TILE)
        assert (v == 3 and 20 <= h <= 23) or (v == 4 and 20 <= h <= 24), (lat, lon, h, v)


def test_mcd12c1_cmg_indexing():
    grid = np.zeros((3600, 7200), dtype=np.uint8)
    grid[int((90 - 50.02) / 0.05), int((70.01 + 180) / 0.05)] = 10
    assert lc.sample(grid, np.array([50.02]), np.array([70.01]))[0] == 10
    assert lc.IGBP_GROUPS[10] == "savanna_steppe"

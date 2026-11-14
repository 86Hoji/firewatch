"""Optional: IGBP land-cover group per H3 cell from MCD12C1 (0.05° CMG, HDF4) placed in data/reference/.

Reads Majority_Land_Cover_Type_1 at each cell centre. Skipped when no MCD12C1*.hdf is present;
the pipeline then uses month/season/region strata only.
"""
import numpy as np
import pandas as pd

from pipeline.common import AGG, REF, get_logger

log = get_logger("landcover")

# IGBP: 1-5 forests, 6-7 shrublands, 8-9 savannas, 10 grasslands, 12/14 croplands
IGBP_GROUPS = {1: "forest", 2: "forest", 3: "forest", 4: "forest", 5: "forest",
               6: "shrubland", 7: "shrubland", 8: "savanna_steppe", 9: "savanna_steppe", 10: "savanna_steppe",
               12: "cropland", 14: "cropland"}


def read_mcd12c1(path):
    from pyhdf.SD import SD, SDC
    return SD(str(path), SDC.READ).select("Majority_Land_Cover_Type_1")[:]


def sample(grid, lat, lon):
    rows = np.clip(((90 - lat) / 0.05).astype(int), 0, grid.shape[0] - 1)
    cols = np.clip(((lon + 180) / 0.05).astype(int), 0, grid.shape[1] - 1)
    return grid[rows, cols]


def main():
    files = sorted(REF.glob("MCD12C1*.hdf"))
    if not files:
        log.info("no MCD12C1*.hdf in %s: skipping land cover (optional)", REF)
        return
    try:
        grid = read_mcd12c1(files[-1])
    except ImportError:
        log.warning("pyhdf not installed: skipping land cover")
        return
    cells = pd.read_parquet(AGG / "cell_month.parquet", columns=["h3_cell", "lat", "lon"]).drop_duplicates("h3_cell")
    cells["igbp"] = sample(grid, cells["lat"].to_numpy(), cells["lon"].to_numpy())
    cells["land_cover"] = cells["igbp"].map(IGBP_GROUPS).fillna("other")
    cells[["h3_cell", "igbp", "land_cover"]].to_parquet(REF / "landcover_cells.parquet", index=False)
    log.info("land cover from %s for %d cells: %s", files[-1].name, len(cells), cells["land_cover"].value_counts().to_dict())


if __name__ == "__main__":
    main()

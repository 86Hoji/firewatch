"""List every FIRMS zip in inputs.zips_dir: request id, sensor, rows, date range, bbox, manifest role or a guessed
country. Writes reports/inventory.csv. Reads the zips in place, in chunks (works for 20M-row files).

    python -m pipeline.inventory
"""
import re
import zipfile

import pandas as pd

from pipeline.common import REPORTS, ROOT, load_config

NAME = re.compile(r"DL_FIRE_([A-Z0-9]+-C\d+)_(\d{6})")
SENSOR = {"M-C61": "MODIS", "SV-C2": "VIIRS S-NPP", "J1V-C2": "NOAA-20", "J2V-C2": "NOAA-21"}
# crude [lat_min, lat_max, lon_min, lon_max] boxes, only to GUESS the country of an unlisted request
GUESS = {"PRT": (30, 43, -32, -6), "AUS": (-45, -9, 112, 155), "BRA": (-34, 6, -75, -34),
         "USA": (18, 72, -180, -66), "IND": (6, 36, 68, 98)}


def guess(lat, lon):
    hits = [c for c, (a, b, c0, c1) in GUESS.items() if a <= lat <= b and c0 <= lon <= c1]
    return hits[0] if len(hits) == 1 else ("?" if not hits else "/".join(hits))


def scan(path):
    rows, lo, hi, box, med = 0, None, None, [90, -90, 180, -180], []
    with zipfile.ZipFile(path) as z:
        for name in (n for n in z.namelist() if n.endswith(".csv")):
            for ch in pd.read_csv(z.open(name), usecols=["latitude", "longitude", "acq_date"], chunksize=2_000_000):
                rows += len(ch)
                a, b = ch["acq_date"].min(), ch["acq_date"].max()
                lo, hi = min(lo or a, a), max(hi or b, b)
                box = [min(box[0], ch.latitude.min()), max(box[1], ch.latitude.max()),
                       min(box[2], ch.longitude.min()), max(box[3], ch.longitude.max())]
                med.append(ch[["latitude", "longitude"]].median())
    m = pd.DataFrame(med).median()
    return rows, lo, hi, box, float(m["latitude"]), float(m["longitude"])


def main():
    cfg = load_config()
    man = pd.read_csv(ROOT / cfg["inputs"]["manifest"], dtype={"request_id": int}).set_index("request_id")
    out = []
    for p in sorted((ROOT / cfg["inputs"]["zips_dir"]).glob("*.zip")):
        m = NAME.match(p.name)
        if not m:
            continue
        rid = int(m.group(2))
        rows, lo, hi, box, mlat, mlon = scan(p)
        listed = rid in man.index
        out.append({"request_id": rid, "file": p.name, "sensor": SENSOR.get(m.group(1), m.group(1)), "rows": rows,
                    "first_date": lo, "last_date": hi, "lat_min": round(box[0], 2), "lat_max": round(box[1], 2),
                    "lon_min": round(box[2], 2), "lon_max": round(box[3], 2), "median_lat": round(mlat, 2),
                    "median_lon": round(mlon, 2), "in_manifest": listed,
                    "country": man.loc[rid, "country"] if listed else guess(mlat, mlon),
                    "role": man.loc[rid, "role"] if listed else "UNCONFIRMED"})
    df = pd.DataFrame(out).sort_values("request_id")
    df.to_csv(REPORTS / "inventory.csv", index=False)
    pd.set_option("display.width", 250)
    print(df[~df["in_manifest"]].drop(columns=["file", "in_manifest"]).to_string(index=False))


if __name__ == "__main__":
    main()

import json
import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
AGG = DATA / "aggregated"
REF = DATA / "reference"
REPORTS = ROOT / "reports"

load_dotenv(ROOT / ".env")

SEASONS = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
           6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}


def load_config(path=None):
    with open(path or os.environ.get("FIRE_CONFIG", ROOT / "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_logger(name):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    return logging.getLogger(name)


def outage_days_sql(src, min_noaa20):
    """Dates when S-NPP has no detection in the region but NOAA-20 has >= min_noaa20 (S-NPP outage)."""
    return f"""SELECT date FROM {src} GROUP BY date
               HAVING count(*) FILTER (WHERE platform = 'SNPP') = 0
                  AND count(*) FILTER (WHERE platform = 'NOAA20') >= {int(min_noaa20)}"""


def ensure_dirs():
    for d in (RAW, PROCESSED, AGG, REF, REPORTS):
        d.mkdir(parents=True, exist_ok=True)


def _finite(o):
    if isinstance(o, float) and o != o or o in (float("inf"), float("-inf")):
        return None
    if isinstance(o, dict):
        return {k: _finite(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_finite(v) for v in o]
    return o


def write_json(path, obj):
    """Strict JSON (NaN/inf -> null) so browsers can parse it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    obj = json.loads(json.dumps(obj, default=str))
    path.write_text(json.dumps(_finite(obj), indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")

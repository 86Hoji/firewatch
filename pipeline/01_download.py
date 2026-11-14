"""Fetch FIRMS per-country archive CSVs, NRT tail via API, and ADM1 boundaries."""
import datetime as dt
import io
import os
import shutil
import time

import pandas as pd
import requests

from pipeline.common import RAW, REF, REPORTS, ROOT, ensure_dirs, get_logger, load_config, write_json

log = get_logger("download")
UA = {"User-Agent": "fire-calendar/0.1"}


def _redact(text):
    key = os.environ.get("FIRMS_MAP_KEY", "").strip()
    return text.replace(key, "***") if key else text


def _get(url, retries, stream=False):
    for i in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=120, stream=stream)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            wait = 2 ** i
            log.warning("retry %d for %s (%s), sleeping %ds", i + 1, _redact(url), _redact(str(e)), wait)
            time.sleep(wait)
    raise RuntimeError(f"failed: {_redact(url)}")


def download_archive(cfg):
    d = cfg["download"]
    last_year = cfg["years"]["end"] or dt.date.today().year
    for folder, pid in d["products"].items():
        y0 = max(d["product_start_year"][folder], cfg["years"]["start"])
        for year in range(y0, last_year + 1):
            for country in cfg["region"]["firms_countries"]:
                out = RAW / "archive" / pid / f"{pid}_{year}_{country}.csv"
                if out.exists():
                    continue
                url = f"{d['archive_base']}/{folder}/{year}/{folder}_{year}_{country}.csv"
                r = _get(url, d["retries"], stream=True)
                if r is None:
                    log.info("not available: %s", url)
                    continue
                out.parent.mkdir(parents=True, exist_ok=True)
                tmp = out.with_suffix(".part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                tmp.replace(out)
                log.info("saved %s (%.1f MB)", out.name, out.stat().st_size / 1e6)


def archive_last_date():
    last = None
    for p in (RAW / "archive").rglob("*.csv"):
        s = pd.read_csv(p, usecols=["acq_date"])["acq_date"].max()
        if isinstance(s, str) and (last is None or s > last):
            last = s
    return dt.date.fromisoformat(last) if last else None


API = "https://firms.modaps.eosdis.nasa.gov/api"


def availability(key, retries):
    r = _get(f"{API}/data_availability/csv/{key}/ALL", retries)
    df = pd.read_csv(io.StringIO(r.text))
    return {row.data_id: (dt.date.fromisoformat(row.min_date), dt.date.fromisoformat(row.max_date))
            for row in df.itertuples()}


def download_api_tail(cfg):
    """Days after the yearly archive: SP via API where available, NRT for the rest."""
    key = os.environ.get("FIRMS_MAP_KEY", "").strip()
    if not key:
        log.warning("FIRMS_MAP_KEY not set: skipping API tail")
        return
    d = cfg["download"]
    avail = availability(key, d["retries"])
    start = (archive_last_date() or dt.date.today() - dt.timedelta(days=60)) + dt.timedelta(days=1)
    today = dt.date.today()
    bbox = ",".join(str(v) for v in cfg["region"]["bbox"])
    outdir = RAW / "api"
    outdir.mkdir(parents=True, exist_ok=True)
    for nrt in d["nrt_sources"]:
        sp = nrt.replace("_NRT", "_SP")
        sp_end = avail.get(sp, (None, start - dt.timedelta(days=1)))[1]
        plan = [(sp, start, min(sp_end, today))]
        if nrt in avail:
            plan.append((nrt, max(sp_end + dt.timedelta(days=1), avail[nrt][0], start), min(avail[nrt][1], today)))
        for src, a, b in plan:
            day, n = a, 0
            while day <= b:
                span = min(d["nrt_day_range"], (b - day).days + 1)
                out = outdir / f"{src}_{day.isoformat()}_{span}.csv"
                fresh = day + dt.timedelta(days=span) > today - dt.timedelta(days=3)
                if not out.exists() or fresh:
                    r = _get(f"{API}/area/csv/{key}/{src}/{bbox}/{span}/{day.isoformat()}", d["retries"])
                    text = r.text if r is not None else ""
                    if text.startswith("latitude"):
                        out.write_text(text, encoding="utf-8")
                        n += 1
                    else:
                        log.warning("%s %s: unexpected response %r", src, day, text[:120])
                    time.sleep(d["nrt_pause_s"])
                day += dt.timedelta(days=span)
            if a <= b:
                log.info("%s %s..%s: %d new windows", src, a, b, n)


def download_boundaries(cfg):
    out = REF / "regions.geojson"
    if out.exists():
        return
    meta = _get(cfg["download"]["boundaries_url"].format(iso3=cfg["region"]["iso3"]), 3)
    if meta is None:
        log.warning("no boundaries for %s", cfg["region"]["iso3"])
        return
    url = meta.json().get("simplifiedGeometryGeoJSON") or meta.json()["gjDownloadURL"]
    r = _get(url, 3)
    out.write_bytes(r.content)
    log.info("saved boundaries %s", out)


def summary():
    rows = []
    for p in sorted(RAW.rglob("*.csv")):
        df = pd.read_csv(p, usecols=["acq_date", "instrument", "satellite"], dtype=str)
        df["year"] = df["acq_date"].str[:4]
        df["kind"] = p.stem.split("_2")[0] if p.parent.name == "api" else "archive"
        rows.append(df.groupby(["instrument", "satellite", "year", "kind"]).size().rename("rows"))
    if not rows:
        log.warning("data/raw is empty")
        return
    s = pd.concat(rows).groupby(level=[0, 1, 2, 3]).sum().reset_index()
    pivot = s.pivot_table(index="year", columns=["instrument", "satellite"], values="rows",
                          aggfunc="sum", fill_value=0)
    print(pivot.to_string())
    write_json(REPORTS / "download_summary.json", s.to_dict(orient="records"))


def use_local_inputs(cfg):
    """inputs.source = zips: nothing to download; copy the local ADM1 file for the API."""
    src = ROOT / cfg["inputs"]["boundaries"]
    if src.exists():
        shutil.copyfile(src, REF / "regions.geojson")
        log.info("local inputs: zips in %s, boundaries %s", cfg["inputs"]["zips_dir"], src.name)
    else:
        log.warning("boundaries file not found: %s", src)


def main():
    ensure_dirs()
    cfg = load_config()
    if cfg.get("inputs", {}).get("source") == "zips":
        use_local_inputs(cfg)
        return
    download_archive(cfg)
    download_api_tail(cfg)
    download_boundaries(cfg)
    summary()


if __name__ == "__main__":
    main()

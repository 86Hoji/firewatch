"""Download MCD64A1 tiles listed in data/reference/mcd64a1/urls.txt (built from NASA CMR) with your Earthdata login.

    python -m pipeline.fetch_mcd64a1                 # 2009-2014 (default)
    python -m pipeline.fetch_mcd64a1 2008 2016       # any year range from the list

Credentials: EARTHDATA_USER / EARTHDATA_PASS from .env, otherwise asked in the terminal. Nothing is stored.
Resumable: existing files are skipped.
"""
import getpass
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests

from pipeline.common import REF, get_logger

log = get_logger("fetch_mcd64a1")
DIR = REF / "mcd64a1"
URS = "urs.earthdata.nasa.gov"


class EarthdataSession(requests.Session):
    """Keeps basic auth only for redirects to/from the Earthdata login host."""

    def __init__(self, user, password):
        super().__init__()
        self.auth = (user, password)
        self.headers["User-Agent"] = "fire-calendar/0.1"

    def rebuild_auth(self, prepared_request, response):
        headers = prepared_request.headers
        if "Authorization" in headers:
            old, new = urlparse(response.request.url).hostname, urlparse(prepared_request.url).hostname
            if old != new and URS not in (old, new):
                del headers["Authorization"]


def fetch(session, url):
    out = DIR / url.rsplit("/", 1)[1]
    if out.exists() and out.stat().st_size > 0:
        return "skip"
    tmp = out.with_suffix(".part")
    with session.get(url, stream=True, timeout=300) as r:
        if r.status_code in (401, 403):
            raise PermissionError(f"HTTP {r.status_code}: check login / approve LP DAAC at https://{URS}")
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.replace(out)
    return "ok"


def main(argv):
    y0, y1 = (int(argv[0]), int(argv[1])) if len(argv) == 2 else (2009, 2014)
    urls = [u.strip() for u in (DIR / "urls.txt").read_text().splitlines() if u.strip()]
    urls = [u for u in urls if y0 <= int(re.search(r"\.A(\d{4})\d{3}\.", u).group(1)) <= y1]
    user = os.environ.get("EARTHDATA_USER") or input("Earthdata username: ")
    password = os.environ.get("EARTHDATA_PASS") or getpass.getpass("Earthdata password: ")
    s = EarthdataSession(user, password)
    fetch(s, urls[0])  # fail fast on bad credentials
    done = {"ok": 0, "skip": 0, "err": 0}
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fetch, s, u): u for u in urls[1:]}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                done[f.result()] += 1
            except PermissionError:
                raise
            except Exception as e:
                done["err"] += 1
                log.warning("failed %s: %s", futs[f].rsplit("/", 1)[1], e)
            if i % 25 == 0:
                log.info("%d / %d  %s", i, len(urls) - 1, done)
    log.info("%d-%d: %d files, %s. Re-run to retry failures.", y0, y1, len(urls), done)


if __name__ == "__main__":
    main(sys.argv[1:])

"""Thin client for ProPublica's Nonprofit Explorer API (v2).

Free, keyless, and rate-limit-polite by design here: one request at a
time with a courtesy pause. Use it for spot lookups and enrichment,
not bulk pulls -- bulk analysis should run on the IRS extract files.
Usage of the API is subject to ProPublica's Data Terms of Use.
"""

from __future__ import annotations

import time

import requests

DEFAULT_BASE = "https://projects.propublica.org/nonprofits/api/v2"
_PAUSE_SECONDS = 0.6
_HEADERS = {"User-Agent": "990-watchdog (personal research project)"}


def get_organization(ein: str | int, base: str = DEFAULT_BASE) -> dict:
    """Full record for one org: profile + filings with extracted data."""
    ein = str(ein).replace("-", "").zfill(9)
    resp = requests.get(
        f"{base}/organizations/{ein}.json", headers=_HEADERS, timeout=30
    )
    resp.raise_for_status()
    time.sleep(_PAUSE_SECONDS)
    return resp.json()


def search(query: str, page: int = 0, base: str = DEFAULT_BASE) -> dict:
    """Keyword search (25 results per page on the v2 API)."""
    resp = requests.get(
        f"{base}/search.json",
        params={"q": query, "page": page},
        headers=_HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    time.sleep(_PAUSE_SECONDS)
    return resp.json()

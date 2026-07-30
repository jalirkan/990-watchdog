"""Load the IRS SOI Annual Extract of Tax-Exempt Organization
Financial Data (Form 990 file).

You download the per-year CSVs manually from the IRS index page (see
config/settings.yaml -> sources.soi_extract_index) into data/raw/,
then point extract_files at them. `download()` is provided for
convenience once you have a direct file URL.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

from watchdog990.schema import SOI_990_COLUMN_MAP, to_canonical


def download(url: str, dest: str | Path, timeout: int = 120) -> Path:
    """Stream a file to disk (for direct CSV/zip links you trust)."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    return dest


def load(path: str | Path, canonical: bool = True) -> pd.DataFrame:
    """Read one extract CSV; optionally rename to canonical schema.

    encoding="utf-8-sig": the PY2022/PY2023 files ship with a UTF-8
    BOM that would otherwise glue \\ufeff onto the first header name;
    harmless for BOM-less years.
    """
    df = pd.read_csv(
        path,
        dtype={"EIN": "string", "ein": "string"},
        low_memory=False,
        encoding="utf-8-sig",
    )
    return to_canonical(df) if canonical else df


def load_slim(path: str | Path) -> pd.DataFrame:
    """Read only the mapped columns of an extract CSV, canonicalized.

    For multi-year panels: three full-width years (246 columns each)
    do not fit in a small-memory environment, and the metrics/flags
    layers only consume mapped canonical fields anyway. Case-matches
    the header like to_canonical does.
    """
    wanted = {v.lower() for v in SOI_990_COLUMN_MAP.values()}
    df = pd.read_csv(
        path,
        usecols=lambda c: c.lower() in wanted,
        dtype={"EIN": "string", "ein": "string"},
        low_memory=False,
        encoding="utf-8-sig",
    )
    return to_canonical(df)

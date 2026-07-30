"""Exempt Organizations Business Master File (EO BMF): who orgs ARE.

The BMF is published as per-state/region CSVs and carries names,
addresses, NTEE codes, and subsection codes. It's the lookup table
you join onto extract EINs so flags have names attached.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from watchdog990.schema import normalize_ein

KEEP = ["EIN", "NAME", "CITY", "STATE", "NTEE_CD", "SUBSECTION"]


def load(paths: Iterable[str | Path]) -> pd.DataFrame:
    """Concatenate one or more BMF CSVs into an EIN-keyed lookup."""
    frames = []
    for p in paths:
        df = pd.read_csv(p, dtype="string", low_memory=False)
        df.columns = [c.upper() for c in df.columns]
        cols = [c for c in KEEP if c in df.columns]
        frames.append(df[cols])
    if not frames:
        return pd.DataFrame(columns=[c.lower() for c in KEEP])
    out = pd.concat(frames, ignore_index=True)
    out.columns = [c.lower() for c in out.columns]
    out["ein"] = normalize_ein(out["ein"])
    if "ntee_cd" in out.columns:
        # First letter of the NTEE code is the major group (A-Z);
        # anything unparseable stays NA rather than a fake sector.
        major = out["ntee_cd"].astype("string").str.strip().str.upper().str[0]
        out["ntee_major"] = major.where(major.str.match(r"[A-Z]", na=False))
    return out.drop_duplicates(subset="ein", keep="last")

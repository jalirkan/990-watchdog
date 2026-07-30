"""Exempt Organizations Business Master File (EO BMF): who orgs ARE.

The BMF is published as per-state/region CSVs and carries names,
addresses, NTEE codes, and subsection codes. It's the lookup table
you join onto extract EINs so flags have names attached.
"""

from __future__ import annotations

from pathlib import Path
from typing import Collection, Iterable

import pandas as pd

from watchdog990.schema import normalize_ein

KEEP = ["EIN", "NAME", "CITY", "STATE", "NTEE_CD", "SUBSECTION"]


def load(
    paths: Iterable[str | Path],
    keep_eins: Collection[str] | None = None,
) -> pd.DataFrame:
    """Concatenate one or more BMF CSVs into an EIN-keyed lookup.

    keep_eins: optional set of normalized 9-char EINs; each file is
    filtered to it at load time. The full-country BMF is ~2M rows and
    a screen only needs the orgs in its panel — filtering per file
    keeps peak memory flat on small machines.
    """
    keep = set(keep_eins) if keep_eins is not None else None
    frames = []
    for p in paths:
        # usecols at read time: the region files are large and we
        # keep 6 of ~30 columns; no reason to parse the rest.
        df = pd.read_csv(
            p,
            usecols=lambda c: c.upper() in KEEP,
            dtype="string",
            low_memory=False,
        )
        df.columns = [c.upper() for c in df.columns]
        df["EIN"] = normalize_ein(df["EIN"])
        if keep is not None:
            df = df[df["EIN"].isin(keep)]
        frames.append(df[[c for c in KEEP if c in df.columns]])
    if not frames:
        return pd.DataFrame(columns=[c.lower() for c in KEEP])
    out = pd.concat(frames, ignore_index=True)
    frames.clear()
    out.columns = [c.lower() for c in out.columns]
    if "ntee_cd" in out.columns:
        # First letter of the NTEE code is the major group (A-Z);
        # anything unparseable stays NA rather than a fake sector.
        major = out["ntee_cd"].astype("string").str.strip().str.upper().str[0]
        out["ntee_major"] = major.where(major.str.match(r"[A-Z]", na=False))
    return out.drop_duplicates(subset="ein", keep="last")

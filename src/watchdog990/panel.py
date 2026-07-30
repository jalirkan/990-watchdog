"""Assemble a multi-processing-year panel of filings.

Phase-1 fieldwork fact this module exists for: a processing-year
extract is NOT one-row-per-org. PY2024 carried 20,949 duplicate EINs
(late-filed prior years, amendments), with tax periods reaching back
to 2008. Trend analysis needs one row per (ein, tax_period) — an
org-fiscal-year — assembled across several processing-year files.

Dedup rule (documented, deliberate): files are stacked in ascending
processing-year order and the LAST occurrence of each
(ein, tax_period) wins. That means later processing years supersede
earlier ones (amended/reprocessed returns carry the freshest data),
and within one file the last occurrence wins (arbitrary but stable).

Caveat for consumers: successive tax periods for an org are usually
~12 months apart but fiscal-year changes produce short years; trend
streaks treat successive filings as successive "years" and
docs/methodology.md says so.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def build_panel(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Stack canonical per-PY dataframes into a filing panel.

    frames: processing-year label -> canonical dataframe (already
    passed through schema.to_canonical). Labels sort ascending, so
    pass them as strings of equal length ("2022", "2023", ...).

    Returns one row per (ein, tax_period), sorted by (ein,
    tax_period), with a `processing_year` column recording which file
    each surviving row came from.
    """
    if not frames:
        return pd.DataFrame(columns=["ein", "tax_period", "processing_year"])

    # Single concat, then one label column via repeat — avoids
    # per-frame copies (three years of filings on a small machine).
    labels = sorted(frames)
    parts = [frames[lb] for lb in labels]
    panel = pd.concat(parts, ignore_index=True)
    panel["processing_year"] = np.repeat(
        [str(lb) for lb in labels], [len(p) for p in parts]
    )
    del parts

    panel["tax_period"] = pd.to_numeric(panel["tax_period"], errors="coerce")
    n_no_period = int(panel["tax_period"].isna().sum())
    if n_no_period:
        log.warning(
            "Dropping %s filing(s) without a parseable tax_period "
            "(cannot join a per-org series)",
            f"{n_no_period:,}",
        )
        panel = panel.dropna(subset=["tax_period"])
    panel["tax_period"] = panel["tax_period"].astype("int64")

    before = len(panel)
    panel = panel.drop_duplicates(subset=["ein", "tax_period"], keep="last")
    dropped = before - len(panel)
    if dropped:
        log.info(
            "Dedup: %s duplicate (ein, tax_period) row(s) superseded "
            "by a later processing year (or later in-file occurrence)",
            f"{dropped:,}",
        )

    return panel.sort_values(["ein", "tax_period"]).reset_index(drop=True)


def latest_per_org(panel: pd.DataFrame) -> pd.DataFrame:
    """One row per EIN: the most recent tax_period in the panel."""
    return panel.groupby("ein", sort=False).tail(1).reset_index(drop=True)

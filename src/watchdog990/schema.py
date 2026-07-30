"""Canonical schema + column maps for IRS SOI 990 extract files.

Design rule: everything downstream (metrics, flags, reports) speaks
CANONICAL names only. IRS field names vary by form (990 / 990-EZ /
990-PF) and occasionally by year, so all of that mess is quarantined
here. If a load warns about unmapped fields, fix THIS file — nothing
else should change.

Before your first real run, verify the mappings against the field
layout doc the IRS publishes alongside each year's extract.
"""

from __future__ import annotations

import logging

import pandas as pd

log = logging.getLogger(__name__)

# Canonical field -> column name in the Form 990 SOI extract.
# Every entry below was verified against the official field layout
# doc for the Processing Year 2024 extract (24eofinextractdoc.xlsx,
# sheet "990", 246 elements) on 2026-07-29. Location cites are that
# doc's "Location" column. Re-verify when switching extract years.
SOI_990_COLUMN_MAP: dict[str, str] = {
    "ein": "ein",                               # header col is "EIN"; match is case-insensitive
    "tax_period": "tax_pd",                     # Form 990 Header, YYYYMM
    "total_revenue": "totrevenue",              # Pt VIII-12(A)
    "total_contributions": "totcntrbgfts",      # Pt VIII-1h(A)
    "program_revenue": "totprgmrevnue",         # Pt VIII-2g(A); was mis-guessed "totprgmrevn"
    "total_expenses": "totfuncexpns",           # Pt IX-25(A)
    "officer_comp": "compnsatncurrofcr",        # Pt IX-5(A)
    "salaries_other": "othrsalwages",           # Pt IX-7(A)
    "fundraising_events_direct": "lessdirfndrsng",  # Pt VIII-8b (direct costs of events only)
    "total_assets_eoy": "totassetsend",         # Pt X-16(B)
    "total_liabilities_eoy": "totliabend",      # Pt X-26(B)
    "net_assets_eoy": "totnetassetend",         # Pt X-33(B)
}

# Canonical fields that the PY2024 990 extract simply does not carry.
# The extract reports Part IX (functional expenses) as column (A)
# totals only -- there is NO program (B) / management (C) /
# fundraising (D) breakdown. Metrics that need these stay NA by
# design; flags must never fire on their absence. Phase 3 (e-file
# XML) is the route to these fields.
NOT_IN_EXTRACT: dict[str, str] = {
    "program_expenses": "Part IX line 25(B) not in extract (col A totals only)",
    "fundraising_expenses": "Part IX line 25(D) not in extract (col A totals only); "
    "nearest columns profndraising (IX-11e, outside fees only) and "
    "lessdirfndrsng (VIII-8b, event costs only) are semantically narrower",
}

# Fields the metrics layer can genuinely use. Missing ones degrade
# gracefully (metrics come back NA, flags don't fire).
REQUIRED = ["ein", "total_revenue", "total_expenses"]


def to_canonical(
    df: pd.DataFrame,
    column_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Rename an extract dataframe to canonical names.

    Case-insensitive on the source side (IRS headers drift between
    upper/lower). Keeps unmapped source columns untouched so nothing
    is silently thrown away; logs which canonical fields could not be
    found so you know which VERIFY entries to chase.
    """
    column_map = column_map or SOI_990_COLUMN_MAP

    lower_to_orig = {c.lower(): c for c in df.columns}
    renames: dict[str, str] = {}
    missing: list[str] = []

    for canonical, source in column_map.items():
        orig = lower_to_orig.get(source.lower())
        if orig is not None:
            renames[orig] = canonical
        else:
            missing.append(f"{canonical} (looked for '{source}')")

    out = df.rename(columns=renames)

    hard_missing = [m for m in missing if m.split(" ")[0] in REQUIRED]
    if hard_missing:
        raise ValueError(
            "Extract is missing required fields: "
            + "; ".join(hard_missing)
            + ". Update SOI_990_COLUMN_MAP in schema.py."
        )
    if missing:
        log.warning(
            "Unmapped canonical fields (metrics using them will be NA): %s",
            "; ".join(missing),
        )
    if column_map is SOI_990_COLUMN_MAP and NOT_IN_EXTRACT:
        log.info(
            "Known extract limitations (fields absent by design): %s",
            "; ".join(f"{k}: {v}" for k, v in NOT_IN_EXTRACT.items()),
        )

    out["ein"] = normalize_ein(out["ein"])
    return out


def normalize_ein(s: pd.Series) -> pd.Series:
    """EINs as zero-padded 9-char strings, the join key everywhere."""
    return (
        s.astype("string")
        .str.replace(r"\D", "", regex=True)
        .str.zfill(9)
    )

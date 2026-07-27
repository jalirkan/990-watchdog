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
# Names below follow the IRS/ProPublica convention (totrevenue,
# totfuncexpns, ...). Entries marked VERIFY are best-effort guesses:
# confirm them against the layout doc for your extract year.
SOI_990_COLUMN_MAP: dict[str, str] = {
    "ein": "ein",
    "tax_period": "tax_pd",                     # VERIFY (YYYYMM)
    "total_revenue": "totrevenue",
    "total_contributions": "totcntrbgfts",
    "program_revenue": "totprgmrevn",
    "total_expenses": "totfuncexpns",
    "officer_comp": "compnsatncurrofcr",        # VERIFY
    "salaries_other": "othrsalwages",           # VERIFY
    "fundraising_expenses": "totfndrsngexpns",  # VERIFY (Part IX ln 25D)
    "fundraising_events_direct": "lessdirfndrsng",  # VERIFY
    "total_assets_eoy": "totassetsend",
    "total_liabilities_eoy": "totliabend",
    "net_assets_eoy": "totnetassetend",         # VERIFY
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

    out["ein"] = normalize_ein(out["ein"])
    return out


def normalize_ein(s: pd.Series) -> pd.Series:
    """EINs as zero-padded 9-char strings, the join key everywhere."""
    return (
        s.astype("string")
        .str.replace(r"\D", "", regex=True)
        .str.zfill(9)
    )

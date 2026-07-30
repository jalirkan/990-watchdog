"""Trend metrics over a multi-year filing panel.

Deteriorating ratios beat snapshots: a single deficit year is noise,
three in a row is a pattern. These metrics are computed per filing
row (trailing, as of that filing) so the latest row per org carries
the org's current streaks.

NA discipline matches the point metrics: an NA input breaks a streak
(absence of evidence is not evidence of a deficit), so streak values
are computed only from filings where the underlying metric exists.

Fiscal-year caveat (also in docs/methodology.md): "consecutive" means
consecutive *filings* ordered by tax_period. Orgs that change fiscal
year end file a short year; we do not attempt to calendar-normalize.

Expected input: output of panel.build_panel() run through
metrics.compute_all() — i.e. one row per (ein, tax_period) with
surplus_margin and months_net_assets present.
"""

from __future__ import annotations

import pandas as pd

TREND_COLUMNS = [
    "n_filings",
    "consec_deficit_years",
    "runway_drop_streak",
    "runway_change",
]


def _trailing_streak(condition: pd.Series, ein: pd.Series) -> pd.Series:
    """Length of the run of consecutive True values ending at each row,
    restarting at each new EIN. condition must be boolean with NA
    already resolved to False."""
    new_block = condition.ne(condition.shift()) | ein.ne(ein.shift())
    block_id = new_block.cumsum()
    streak = condition.groupby(block_id).cumcount() + 1
    return streak.where(condition, 0).astype("int64")


def add_trend_metrics(panel: pd.DataFrame) -> pd.DataFrame:
    """Add trailing trend columns to a (ein, tax_period)-sorted panel."""
    out = panel.sort_values(["ein", "tax_period"]).reset_index(drop=True)
    ein = out["ein"]

    margin = pd.to_numeric(out.get("surplus_margin"), errors="coerce")
    deficit = (margin < 0).fillna(False)
    out["consec_deficit_years"] = _trailing_streak(deficit, ein)

    mna = pd.to_numeric(out.get("months_net_assets"), errors="coerce")
    prev_mna = mna.groupby(ein, sort=False).shift()
    out["runway_change"] = mna - prev_mna
    dropped = (mna < prev_mna).fillna(False)
    out["runway_drop_streak"] = _trailing_streak(dropped, ein)

    out["n_filings"] = out.groupby("ein", sort=False)["tax_period"].transform("size")

    # Honesty in outputs: a streak "as of" a filing whose own metric is
    # NA is not a streak we can assert. (Flags would not fire anyway;
    # this keeps the CSV from overstating.)
    out.loc[margin.isna(), "consec_deficit_years"] = pd.NA
    out.loc[mna.isna(), "runway_drop_streak"] = pd.NA

    return out

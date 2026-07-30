"""Screening flags.

Framing matters and it is deliberate: a flag means "this filing
pattern warrants a closer look," never "this organization did
something wrong." Legitimate explanations exist for every rule below
(startup years, hospital systems, pass-through grantmakers, one-time
events). The public-facing language in report.py repeats this;
docs/methodology.md is the canonical statement.

Each rule is a small, named, individually testable function so the
methodology can be audited line by line — by you or by anyone who
forks the repo. That transparency IS the product.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Flag:
    id: str
    severity: str  # "high" | "medium" | "low"
    description: str
    # fn(df, thresholds) -> boolean Series (True = flagged)
    fn: Callable[[pd.DataFrame, dict], pd.Series]


def _num(df: pd.DataFrame, name: str) -> pd.Series:
    """Numeric column, or an all-NA series when the extract lacks it.

    A column the dataset never carried is "no data", not "reported
    zero" -- rules must degrade to never-fire, mirroring metrics._col.
    (df.get() on a missing column returns None, and the scalar NaN it
    coerces to would crash .fillna()/Series ops downstream.)
    """
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def _negative_net_assets(df: pd.DataFrame, t: dict) -> pd.Series:
    return _num(df, "net_assets_eoy") < 0


def _officer_comp_heavy(df: pd.DataFrame, t: dict) -> pd.Series:
    return _num(df, "officer_comp_ratio") > t["officer_comp_ratio_max"]


def _low_program_ratio(df: pd.DataFrame, t: dict) -> pd.Series:
    return _num(df, "program_expense_ratio") < t["program_expense_ratio_min"]


def _zero_fundraising_cost(df: pd.DataFrame, t: dict) -> pd.Series:
    """Large contributions with zero/blank reported fundraising expense.

    A classic understatement pattern: money rarely raises itself.
    Also frequently innocent (all-volunteer boards, single-grant
    funding) — which is exactly why this is a flag, not a finding.

    Blank-but-present fundraising on a filed return counts as a
    reported zero (that IS the pattern). A dataset that never carried
    the column at all (e.g. the SOI extract lacks Part IX-25(D)) must
    never fire this rule.
    """
    if "fundraising_expenses" not in df.columns:
        return pd.Series(False, index=df.index)
    contributions = _num(df, "total_contributions")
    fundraising = _num(df, "fundraising_expenses").fillna(0)
    return (contributions >= t["large_contributions_floor"]) & (
        fundraising == 0
    )


def _thin_runway(df: pd.DataFrame, t: dict) -> pd.Series:
    return (_num(df, "months_net_assets") < t["months_net_assets_min"]) & (
        _num(df, "net_assets_eoy") >= 0
    )


def _persistent_deficits(df: pd.DataFrame, t: dict) -> pd.Series:
    """Trend rule: expenses exceeded revenue in N consecutive filings.

    Only computable on a multi-year panel (trends.add_trend_metrics);
    on single-year runs the column is absent and the rule never fires.
    """
    return _num(df, "consec_deficit_years") >= t["persistent_deficit_years_min"]


def _deteriorating_runway(df: pd.DataFrame, t: dict) -> pd.Series:
    """Trend rule: months-of-spending cushion fell in consecutive
    filings AND the latest cushion is thin. Both legs required — a
    fall from 60 to 40 months is not distress."""
    return (
        (_num(df, "runway_drop_streak") >= t["runway_drop_streak_min"])
        & (_num(df, "months_net_assets") < t["runway_deteriorating_latest_max"])
    )


REGISTRY: list[Flag] = [
    Flag(
        "NEGATIVE_NET_ASSETS",
        "high",
        "Liabilities exceed assets at year end.",
        _negative_net_assets,
    ),
    Flag(
        "OFFICER_COMP_HEAVY",
        "medium",
        "Officer compensation is an unusually large share of total expenses.",
        _officer_comp_heavy,
    ),
    Flag(
        "LOW_PROGRAM_RATIO",
        "medium",
        "Reported program spending is a low share of total expenses.",
        _low_program_ratio,
    ),
    Flag(
        "ZERO_FUNDRAISING_COST",
        "medium",
        "Substantial contributions with no reported fundraising expense.",
        _zero_fundraising_cost,
    ),
    Flag(
        "THIN_RUNWAY",
        "low",
        "Net assets cover less than the configured months of spending.",
        _thin_runway,
    ),
    Flag(
        "PERSISTENT_DEFICITS",
        "medium",
        "Expenses exceeded revenue in several consecutive filed years.",
        _persistent_deficits,
    ),
    Flag(
        "DETERIORATING_RUNWAY",
        "medium",
        "Months-of-spending cushion fell in consecutive years to a thin level.",
        _deteriorating_runway,
    ),
]


def evaluate(df: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    """Run every registered flag.

    Returns a long dataframe: one row per (ein, flag) hit, with
    severity and description — ready for report.py. NA inputs never
    fire a flag (absence of evidence is not evidence).
    """
    hits: list[pd.DataFrame] = []
    for flag in REGISTRY:
        mask = flag.fn(df, thresholds).fillna(False)
        if mask.any():
            sub = df.loc[mask, ["ein"]].copy()
            sub["flag_id"] = flag.id
            sub["severity"] = flag.severity
            sub["description"] = flag.description
            hits.append(sub)

    if not hits:
        return pd.DataFrame(
            columns=["ein", "flag_id", "severity", "description"]
        )
    return pd.concat(hits, ignore_index=True)

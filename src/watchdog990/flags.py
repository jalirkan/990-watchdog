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

import pandas as pd


@dataclass(frozen=True)
class Flag:
    id: str
    severity: str  # "high" | "medium" | "low"
    description: str
    # fn(df, thresholds) -> boolean Series (True = flagged)
    fn: Callable[[pd.DataFrame, dict], pd.Series]


def _negative_net_assets(df: pd.DataFrame, t: dict) -> pd.Series:
    return pd.to_numeric(df.get("net_assets_eoy"), errors="coerce") < 0


def _officer_comp_heavy(df: pd.DataFrame, t: dict) -> pd.Series:
    return df["officer_comp_ratio"] > t["officer_comp_ratio_max"]


def _low_program_ratio(df: pd.DataFrame, t: dict) -> pd.Series:
    return df["program_expense_ratio"] < t["program_expense_ratio_min"]


def _zero_fundraising_cost(df: pd.DataFrame, t: dict) -> pd.Series:
    """Large contributions with zero/blank reported fundraising expense.

    A classic understatement pattern: money rarely raises itself.
    Also frequently innocent (all-volunteer boards, single-grant
    funding) — which is exactly why this is a flag, not a finding.
    """
    contributions = pd.to_numeric(
        df.get("total_contributions"), errors="coerce"
    )
    fundraising = pd.to_numeric(
        df.get("fundraising_expenses"), errors="coerce"
    ).fillna(0)
    return (contributions >= t["large_contributions_floor"]) & (
        fundraising == 0
    )


def _thin_runway(df: pd.DataFrame, t: dict) -> pd.Series:
    return (df["months_net_assets"] < t["months_net_assets_min"]) & (
        pd.to_numeric(df.get("net_assets_eoy"), errors="coerce") >= 0
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

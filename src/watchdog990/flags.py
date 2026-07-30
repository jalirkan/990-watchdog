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


def _chronic_deficits(df: pd.DataFrame, t: dict) -> pd.Series:
    """Severity tier above PERSISTENT_DEFICITS: a deficit in EVERY
    observed filing, with at least chronic_deficit_min_years of
    history. An org that has never once broken even in five-plus
    observable years is a materially stronger signal than any fixed
    streak — though planned endowment spend-down remains an innocent
    explanation, which the manual review checks first."""
    consec = _num(df, "consec_deficit_years")
    nf = _num(df, "n_filings")
    return (nf >= t["chronic_deficit_min_years"]) & (consec >= nf)


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
    Flag(
        "CHRONIC_DEFICITS",
        "high",
        "Expenses exceeded revenue in every observed year (5+ years of history).",
        _chronic_deficits,
    ),
]


def governance_flags(gov: pd.DataFrame, panel_eins: set) -> pd.DataFrame:
    """Governance rules from parsed e-file XML (methodology change
    approved 2026-07-30).

    MATERIAL_DIVERSION (high): the org checked Part VI line 5 — a
    self-reported discovery of material diversion of assets — on a
    signed return. Fires for ANY panel org with the admission, not
    just orgs already flagged on ratios: a clean balance sheet does
    not neutralize a diversion admission. The counterweight is in the
    description and methodology: self-reporting WITH remediation is
    transparency; the flag means "read Schedule O", never more.

    Insider loans and board independence deliberately stay context
    columns, not flags (2% base rate and continuous-valued
    respectively — better sort keys than binary alarms).
    """
    if gov.empty or "material_diversion" not in gov.columns:
        return pd.DataFrame(columns=["ein", "flag_id", "severity", "description"])
    mask = (gov["material_diversion"] == True) & gov["ein"].isin(panel_eins)  # noqa: E712
    hits = gov.loc[mask, ["ein"]].copy()
    hits["flag_id"] = "MATERIAL_DIVERSION"
    hits["severity"] = "high"
    hits["description"] = (
        "Org reported discovering a material diversion of assets "
        "(Part VI line 5). Read Schedule O for the org's explanation."
    )
    return hits.reset_index(drop=True)


def sector_outliers(df: pd.DataFrame, t: dict) -> pd.DataFrame:
    """Sector-RELATIVE screen: officer comp ratio above the
    sector_outlier_pctl quantile of the org's own NTEE major group.

    Lives outside REGISTRY deliberately: registry rules are row-local
    (an org's numbers alone decide), while this rule needs the whole
    population to define "unusual for its sector". It therefore runs
    only where the sector join exists (the trend report stage) and
    only for sectors with at least sector_outlier_min_group
    computable orgs. Returns hits in the standard long shape, plus
    the cutoff used — the workpaper should show the bar that was
    cleared.
    """
    if "ntee_major" not in df.columns:
        return pd.DataFrame(
            columns=["ein", "flag_id", "severity", "description",
                     "sector_officer_comp_cutoff"]
        )
    ratio = _num(df, "officer_comp_ratio")
    sector = df["ntee_major"]
    ok = ratio.notna() & sector.notna()

    counts = sector[ok].value_counts()
    big_sectors = counts[counts >= t["sector_outlier_min_group"]].index
    cuts = (
        df.loc[ok & sector.isin(big_sectors)]
        .groupby("ntee_major")["officer_comp_ratio"]
        .quantile(t["sector_outlier_pctl"])
    )
    cutoff = sector.map(cuts)  # NA for unknown/small sectors
    mask = (ratio > cutoff).fillna(False)

    hits = df.loc[mask, ["ein"]].copy()
    hits["flag_id"] = "SECTOR_OUTLIER_OFFICER_COMP"
    hits["severity"] = "low"
    hits["description"] = (
        "Officer compensation share is unusually high relative to the "
        "org's own NTEE sector."
    )
    hits["sector_officer_comp_cutoff"] = cutoff[mask].round(4)
    return hits.reset_index(drop=True)


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

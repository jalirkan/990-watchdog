"""Screening metrics computed on the canonical dataframe.

Every function is pure: canonical df in, df with added columns out.
Division by zero / missing inputs produce NA, never crashes and never
fake zeros — an NA ratio means "the filing didn't support computing
this," which is itself information.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

METRIC_COLUMNS = [
    "program_expense_ratio",
    "officer_comp_ratio",
    "fundraising_efficiency",
    "surplus_margin",
    "months_net_assets",
]


def _safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    num = pd.to_numeric(num, errors="coerce")
    den = pd.to_numeric(den, errors="coerce")
    out = num / den.replace(0, np.nan)
    return out


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Column if present, else an all-NA series (graceful degradation)."""
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """Add all screening metrics. Idempotent; safe on partial schemas."""
    out = df.copy()

    total_expenses = _col(out, "total_expenses")
    total_revenue = _col(out, "total_revenue")

    # Share of spending that went to program services (Part IX col B).
    # NOTE: only computable if program_expenses is mapped; the base
    # SOI extract may not carry the functional breakdown — see
    # docs/data-sources.md for the phase-2 XML route.
    out["program_expense_ratio"] = _safe_div(
        _col(out, "program_expenses"), total_expenses
    )

    # Officer/director/key-employee comp as a share of total spending.
    out["officer_comp_ratio"] = _safe_div(
        _col(out, "officer_comp"), total_expenses
    )

    # Contributions raised per dollar of reported fundraising expense.
    out["fundraising_efficiency"] = _safe_div(
        _col(out, "total_contributions"), _col(out, "fundraising_expenses")
    )

    # (Revenue - expenses) / revenue. Persistent deep deficits or
    # implausibly perfect break-evens both merit a look.
    out["surplus_margin"] = _safe_div(
        total_revenue - total_expenses, total_revenue
    )

    # Rough runway: net assets over one month of spending.
    out["months_net_assets"] = _safe_div(
        _col(out, "net_assets_eoy"), total_expenses / 12.0
    )

    return out

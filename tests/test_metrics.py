"""Tests run on synthetic canonical data — no downloads, no network.

Run with either:
    pytest -q
    python tests/test_metrics.py
"""

from __future__ import annotations

import math

import pandas as pd

from watchdog990 import flags, metrics
from watchdog990.schema import normalize_ein

THRESHOLDS = {
    "officer_comp_ratio_max": 0.30,
    "program_expense_ratio_min": 0.50,
    "months_net_assets_min": 1.0,
    "large_contributions_floor": 1_000_000,
    "large_private_contributions_floor": 1_000_000,
    "persistent_deficit_years_min": 3,
    "runway_drop_streak_min": 2,
    "runway_deteriorating_latest_max": 6.0,
    "chronic_deficit_min_years": 5,
    "sector_outlier_pctl": 0.95,
    "sector_outlier_min_group": 300,
}


def _synthetic() -> pd.DataFrame:
    return pd.DataFrame(
        {
            # org A: healthy. org B: comp-heavy, underwater, "free" money.
            # org C: zero-expense edge case (division guards).
            "ein": ["000000001", "000000002", "000000003"],
            "total_revenue": [1_000_000, 2_000_000, 0],
            "total_contributions": [600_000, 1_500_000, 0],
            "total_expenses": [900_000, 1_800_000, 0],
            "program_expenses": [720_000, 700_000, 0],
            "officer_comp": [90_000, 720_000, 0],
            "fundraising_expenses": [50_000, 0, 0],
            "net_assets_eoy": [450_000, -250_000, 0],
        }
    )


def test_metrics_values():
    df = metrics.compute_all(_synthetic())
    a = df.iloc[0]
    assert math.isclose(a.program_expense_ratio, 0.8)
    assert math.isclose(a.officer_comp_ratio, 0.1)
    assert math.isclose(a.fundraising_efficiency, 12.0)
    assert math.isclose(a.surplus_margin, 0.1)
    assert math.isclose(a.months_net_assets, 6.0)


def test_zero_denominators_yield_na_not_crash():
    df = metrics.compute_all(_synthetic())
    c = df.iloc[2]
    assert pd.isna(c.program_expense_ratio)
    assert pd.isna(c.surplus_margin)
    assert pd.isna(c.months_net_assets)


def test_flags_fire_on_bad_org_only():
    df = metrics.compute_all(_synthetic())
    hits = flags.evaluate(df, THRESHOLDS)

    flagged = set(hits.ein)
    assert "000000001" not in flagged, "healthy org must stay clean"
    assert "000000003" not in flagged, "NA metrics must never fire flags"

    b_flags = set(hits.loc[hits.ein == "000000002", "flag_id"])
    assert {
        "NEGATIVE_NET_ASSETS",
        "OFFICER_COMP_HEAVY",
        "LOW_PROGRAM_RATIO",
        "ZERO_FUNDRAISING_COST",
    } <= b_flags


def test_ein_normalization():
    s = pd.Series(["12-3456789", "987654321", "1234567"])
    out = normalize_ein(s).tolist()
    assert out == ["123456789", "987654321", "001234567"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("All tests passed.")

"""Phase-2 tests: panel dedup, trend streaks, trend flags, sectors.

All synthetic — no downloads, no network.

Run with either:
    pytest -q
    python tests/test_trends.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from watchdog990 import flags, metrics, panel, report, trends

THRESHOLDS = {
    "officer_comp_ratio_max": 0.30,
    "program_expense_ratio_min": 0.50,
    "months_net_assets_min": 1.0,
    "large_contributions_floor": 1_000_000,
    "persistent_deficit_years_min": 3,
    "runway_drop_streak_min": 2,
    "runway_deteriorating_latest_max": 6.0,
}


def _frame(rows):
    return pd.DataFrame(
        rows, columns=["ein", "tax_period", "total_revenue", "total_expenses"]
    )


def test_panel_dedup_latest_processing_year_wins():
    py23 = _frame([("000000001", 202212, 100, 90), ("000000002", 202212, 50, 60)])
    py24 = _frame([("000000001", 202212, 999, 90)])  # amended in a later PY
    pnl = panel.build_panel({"2023": py23, "2024": py24})
    assert len(pnl) == 2
    row = pnl[pnl.ein == "000000001"].iloc[0]
    assert row.total_revenue == 999 and row.processing_year == "2024"


def test_panel_dedup_within_file_keeps_last():
    py24 = _frame([("000000003", 202312, 1, 1), ("000000003", 202312, 2, 2)])
    pnl = panel.build_panel({"2024": py24})
    assert len(pnl) == 1
    assert pnl.iloc[0].total_revenue == 2


def test_latest_per_org():
    py = _frame([("000000004", 202112, 1, 1), ("000000004", 202312, 3, 3)])
    latest = panel.latest_per_org(panel.build_panel({"2024": py}))
    assert len(latest) == 1 and latest.iloc[0].tax_period == 202312


def _metric_panel(ein, margins, runways):
    """Panel rows with surplus_margin / months_net_assets set directly."""
    n = len(margins)
    return pd.DataFrame(
        {
            "ein": [ein] * n,
            "tax_period": [202012 + 100 * i for i in range(n)],
            "surplus_margin": margins,
            "months_net_assets": runways,
        }
    )


def test_deficit_streak_counts_trailing_consecutive():
    pnl = _metric_panel("000000005", [0.1, -0.1, -0.2, -0.3], [9, 9, 9, 9])
    out = trends.add_trend_metrics(pnl)
    assert out["consec_deficit_years"].tolist() == [0, 1, 2, 3]


def test_deficit_streak_broken_by_surplus_and_by_na():
    pnl = _metric_panel(
        "000000006", [-0.1, -0.1, np.nan, -0.2], [9, 9, 9, 9]
    )
    out = trends.add_trend_metrics(pnl)
    # NA row: streak value is NA (can't assert a streak on a missing
    # metric); following deficit restarts at 1.
    assert out["consec_deficit_years"].iloc[1] == 2
    assert pd.isna(out["consec_deficit_years"].iloc[2])
    assert out["consec_deficit_years"].iloc[3] == 1


def test_runway_drop_streak_and_change():
    pnl = _metric_panel("000000007", [0, 0, 0], [10.0, 8.0, 5.0])
    out = trends.add_trend_metrics(pnl)
    assert out["runway_drop_streak"].tolist() == [0, 1, 2]
    assert out["runway_change"].iloc[2] == -3.0


def test_streaks_do_not_leak_across_orgs():
    a = _metric_panel("000000008", [-0.1, -0.1], [5, 4])
    b = _metric_panel("000000009", [-0.1, -0.1], [5, 4])
    out = trends.add_trend_metrics(pd.concat([a, b], ignore_index=True))
    assert out.groupby("ein")["consec_deficit_years"].last().tolist() == [2, 2]
    assert out.groupby("ein")["runway_drop_streak"].last().tolist() == [1, 1]


def test_persistent_deficits_fires_at_three_not_two():
    three = trends.add_trend_metrics(
        _metric_panel("000000010", [-0.1, -0.1, -0.1], [9, 9, 9])
    )
    two = trends.add_trend_metrics(
        _metric_panel("000000011", [0.1, -0.1, -0.1], [9, 9, 9])
    )
    latest = pd.concat(
        [panel.latest_per_org(three), panel.latest_per_org(two)],
        ignore_index=True,
    )
    hits = flags.evaluate(latest, THRESHOLDS)
    pd_hits = set(hits.loc[hits.flag_id == "PERSISTENT_DEFICITS", "ein"])
    assert pd_hits == {"000000010"}


def test_deteriorating_runway_needs_both_legs():
    fires = trends.add_trend_metrics(
        _metric_panel("000000012", [0, 0, 0], [10.0, 8.0, 5.0])
    )
    rich = trends.add_trend_metrics(  # falling but still 40 months
        _metric_panel("000000013", [0, 0, 0], [60.0, 50.0, 40.0])
    )
    one_drop = trends.add_trend_metrics(
        _metric_panel("000000014", [0, 0, 0], [3.0, 5.0, 4.0])
    )
    latest = pd.concat(
        [panel.latest_per_org(x) for x in (fires, rich, one_drop)],
        ignore_index=True,
    )
    hits = flags.evaluate(latest, THRESHOLDS)
    dr = set(hits.loc[hits.flag_id == "DETERIORATING_RUNWAY", "ein"])
    assert dr == {"000000012"}


def test_trend_flags_never_fire_on_single_year_run():
    df = pd.DataFrame(
        {
            "ein": ["000000015"],
            "total_revenue": [100_000],
            "total_expenses": [200_000],  # deficit, but only one year
            "net_assets_eoy": [50_000],
        }
    )
    hits = flags.evaluate(metrics.compute_all(df), THRESHOLDS)
    assert not set(hits.flag_id) & {"PERSISTENT_DEFICITS", "DETERIORATING_RUNWAY"}


def test_point_flags_in_trend_mode_use_latest_filing_only():
    """Org was underwater in an old year but healthy now: evaluating
    the latest filing must not carry the old year's point flag."""
    rows = pd.DataFrame(
        {
            "ein": ["000000016"] * 2,
            "tax_period": [202112, 202312],
            "total_revenue": [100_000, 500_000],
            "total_expenses": [150_000, 400_000],
            "net_assets_eoy": [-10_000, 400_000],
        }
    )
    pnl = trends.add_trend_metrics(
        metrics.compute_all(panel.build_panel({"2024": rows}))
    )
    latest = panel.latest_per_org(pnl)
    hits = flags.evaluate(latest, THRESHOLDS)
    assert "NEGATIVE_NET_ASSETS" not in set(hits.flag_id)


def test_bmf_ntee_major_and_sector_rates():
    """End-to-end through the real bmf.load: NTEE major extraction,
    case handling, unusable codes staying NA, and the rate table."""
    import tempfile
    from pathlib import Path

    from watchdog990.ingest import bmf as bmf_mod

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "eo_test.csv"
        p.write_text(
            "EIN,NAME,CITY,STATE,NTEE_CD,SUBSECTION\n"
            "17,ALPHA EDU,ALBANY,NY,B25,03\n"
            "18,BETA HEALTH,BUFFALO,NY,e21x,03\n"
            "19,GAMMA MYSTERY,NYC,NY,,03\n"
            "20,DELTA ODD,NYC,NY,9zz,03\n"
        )
        names = bmf_mod.load([p])

    got = dict(zip(names.ein, names.ntee_major))
    assert got["000000017"] == "B"
    assert got["000000018"] == "E"  # lowercased code still resolves
    assert pd.isna(got["000000019"]) and pd.isna(got["000000020"])

    pop = names[["ein", "ntee_major"]]
    table = report.sector_rates(pop, flagged_eins={"000000017"})
    edu = table[table.ntee_major == "B"].iloc[0]
    assert edu.n_orgs == 1 and edu.n_flagged == 1 and edu.rate == 1.0
    assert edu.sector == "Education"
    no_ntee = table[table.ntee_major == "(no NTEE)"].iloc[0]
    assert no_ntee.n_orgs == 2 and no_ntee.n_flagged == 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("All tests passed.")

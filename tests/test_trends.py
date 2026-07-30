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
    "chronic_deficit_min_years": 5,
    "sector_outlier_pctl": 0.95,
    "sector_outlier_min_group": 5,  # tiny for testability
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


def test_chronic_deficits_requires_every_observed_year_and_history():
    all5 = trends.add_trend_metrics(
        _metric_panel("000000040", [-0.1] * 5, [9] * 5)
    )
    four_of_five = trends.add_trend_metrics(
        _metric_panel("000000041", [0.1, -0.1, -0.1, -0.1, -0.1], [9] * 5)
    )
    all4 = trends.add_trend_metrics(
        _metric_panel("000000042", [-0.1] * 4, [9] * 4)
    )
    latest = pd.concat(
        [panel.latest_per_org(x) for x in (all5, four_of_five, all4)],
        ignore_index=True,
    )
    hits = flags.evaluate(latest, THRESHOLDS)
    chronic = set(hits.loc[hits.flag_id == "CHRONIC_DEFICITS", "ein"])
    assert chronic == {"000000040"}, (
        "only the org in deficit every observed year with 5+ years fires"
    )
    # tiering: the chronic org also carries PERSISTENT_DEFICITS
    persistent = set(hits.loc[hits.flag_id == "PERSISTENT_DEFICITS", "ein"])
    assert "000000040" in persistent


def test_sector_outliers_relative_to_own_sector():
    df = pd.DataFrame(
        {
            "ein": [f"00000005{i}" for i in range(9)],
            "officer_comp_ratio": [0.05, 0.06, 0.05, 0.04, 0.05, 0.90,  # sector A
                                   0.95, 0.94,                          # sector B (too small)
                                   0.99],                               # no sector
            "ntee_major": ["A"] * 6 + ["B"] * 2 + [None],
        }
    )
    hits = flags.sector_outliers(df, THRESHOLDS)
    assert set(hits.ein) == {"000000055"}, (
        "fires only in big-enough sectors, relative to that sector"
    )
    row = hits.iloc[0]
    assert row.flag_id == "SECTOR_OUTLIER_OFFICER_COMP"
    assert 0.05 < row.sector_officer_comp_cutoff < 0.90


def test_sector_outliers_absent_sector_column_yields_empty():
    df = pd.DataFrame({"ein": ["000000060"], "officer_comp_ratio": [0.99]})
    hits = flags.sector_outliers(df, THRESHOLDS)
    assert hits.empty


def test_subsection_rates_normalizes_codes():
    pop = pd.DataFrame(
        {
            "ein": ["000000030", "000000031", "000000032"],
            "subsection": ["3", "03", None],  # unpadded + padded + missing
        }
    )
    table = report.subsection_rates(pop, flagged_eins={"000000030"})
    c3 = table[table.group.str.startswith("501(c)(3)")].iloc[0]
    assert c3.n_orgs == 2 and c3.n_flagged == 1  # "3" and "03" merged
    assert "(no subsection)" in set(table.group)


def test_subsection_rates_survives_float_contamination():
    """Regression: a NaN-bearing code column re-read from a CSV
    checkpoint arrives as float64 ("03" -> 3.0) and must still map."""
    pop = pd.DataFrame(
        {
            "ein": ["000000033", "000000034"],
            "subsection": [3.0, None],
        }
    )
    table = report.subsection_rates(pop, flagged_eins=set())
    assert any(table.group.str.startswith("501(c)(3)"))


def test_bmf_keep_eins_filters_at_load():
    import tempfile
    from pathlib import Path

    from watchdog990.ingest import bmf as bmf_mod

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "eo_test.csv"
        p.write_text(
            "EIN,NAME,CITY,STATE,NTEE_CD,SUBSECTION\n"
            "21,KEEP ME,NYC,NY,A10,03\n"
            "22,DROP ME,NYC,NY,B20,03\n"
        )
        names = bmf_mod.load([p], keep_eins={"000000021"})
    assert names.ein.tolist() == ["000000021"]
    assert names.name.tolist() == ["KEEP ME"]


def test_trend_cli_staged_end_to_end():
    """panel -> names -> report through the real CLI with checkpoint
    round-trips (EIN zero-padding must survive the CSV boundary)."""
    import os
    import tempfile
    from pathlib import Path

    from watchdog990 import cli

    hdr = (
        "EIN,tax_pd,totrevenue,totcntrbgfts,totprgmrevnue,totfuncexpns,"
        "compnsatncurrofcr,othrsalwages,lessdirfndrsng,totassetsend,"
        "totliabend,totnetassetend\n"
    )
    # org 1: FOUR deficit years (matches the >=4 default), runway
    # 24 -> 12 -> 6 -> 2.4 months. org 2: healthy.
    years = {
        "2021": ["1,202012,90,10,80,100,0,0,0,250,50,200", "2,202012,120,0,120,100,0,0,0,300,100,90"],
        "2022": ["1,202112,90,10,80,100,0,0,0,150,50,100", "2,202112,120,0,120,100,0,0,0,300,100,100"],
        "2023": ["1,202212,90,10,80,100,0,0,0,110,60,50", "2,202212,120,0,120,100,0,0,0,300,100,110"],
        "2024": ["1,202312,90,10,80,100,0,0,0,90,70,20", "2,202312,120,0,120,100,0,0,0,300,100,120"],
    }
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        try:
            os.chdir(d)
            Path("data/raw").mkdir(parents=True)
            for yr, rows in years.items():
                Path(f"data/raw/{yr}.csv").write_text(hdr + "\n".join(rows) + "\n")
            Path("data/raw/bmf.csv").write_text(
                "EIN,NAME,CITY,STATE,NTEE_CD,SUBSECTION\n"
                "1,SLIDING ORG,ALBANY,NY,B25,03\n"
                "2,FINE ORG,BUFFALO,NY,,03\n"
            )
            Path("s.yaml").write_text(
                "extract_files:\n"
                '  "2021": data/raw/2021.csv\n'
                '  "2022": data/raw/2022.csv\n'
                '  "2023": data/raw/2023.csv\n'
                '  "2024": data/raw/2024.csv\n'
                "output_dir: out\n"
            )
            Path("gov.csv").write_text(
                "ein,tax_period,material_diversion,loans_to_insiders,"
                "board_independence,schedule_l_present,is_form_990\n"
                "000000001,202312,True,False,0.5,True,True\n"
            )
            assert cli.main(["trend", "--stage", "panel", "--config", "s.yaml"]) == 0
            assert cli.main(
                ["trend", "--stage", "names", "--config", "s.yaml",
                 "--bmf", "data/raw/bmf.csv"]
            ) == 0
            assert cli.main(
                ["trend", "--stage", "report", "--config", "s.yaml",
                 "--governance", "gov.csv"]
            ) == 0

            summary = Path("out/summary_2021-2024_trend.md").read_text()
            assert "Governance signals" in summary
            assert "Material diversion of assets reported: 1" in summary
            flags_csv = pd.read_csv(
                "out/flags_2021-2024_trend.csv", dtype={"ein": "string"}
            )
            assert "material_diversion" in flags_csv.columns
            assert "PERSISTENT_DEFICITS" in summary
            assert "DETERIORATING_RUNWAY" in summary
            assert "SLIDING ORG" in summary
            assert "FINE ORG" not in summary  # healthy org stays clean
            assert "NTEE" in summary
            assert "501(c)(3) charitable" in summary  # subsection table

            hits = pd.read_csv("data/interim/trend_hits.csv", dtype={"ein": "string"})
            assert set(hits.ein) == {"000000001"}  # zfill survived
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("All tests passed.")

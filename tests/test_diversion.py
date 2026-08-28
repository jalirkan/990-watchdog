"""Phase-5 tests: the material-diversion review workpaper.

Synthetic governance records, no downloads, no network. The fixture is
built from the failure modes real batches actually produced, so each
test pins a rule leg documented in src/watchdog990/diversion.py.

Run with either:
    pytest -q
    python tests/test_diversion.py
"""

from __future__ import annotations

import pandas as pd

from watchdog990 import diversion


def _row(ein, tax_period, **kw):
    rec = {
        "ein": ein,
        "tax_period": tax_period,
        "material_diversion": True,
        "is_form_990": True,
        "schedule_o_text": f"[Form 990, Part VI, Line 5] Explanation for {ein}.",
        "schema_version": "2023v5.0",
        "voting_members": 9,
        "independent_members": 8,
        "board_independence": 8 / 9,
        "loans_to_insiders": False,
        "schedule_l_present": False,
    }
    rec.update(kw)
    return rec


# One frame, in stacking order (earlier batch first), covering:
#  70  a plain admission
#  71  admitted twice for the same period -- the later row supersedes
#  72  admitted, then a 990-EZ/PF row lands for the SAME period
#  73  admitted in two DIFFERENT periods -- both are separate rows
#  74  answered "No"
#  75  the question is NA (990-EZ; never a fake False)
#  76  admitted with no Schedule O explanation filed
GOV = pd.DataFrame(
    [
        _row("000000070", 202312),
        _row("000000071", 202312, schedule_o_text="first, superseded"),
        _row("000000072", 202312),
        _row("000000073", 202212),
        _row("000000074", 202312, material_diversion=False, schedule_o_text=None),
        _row(
            "000000075", 202312, material_diversion=pd.NA,
            is_form_990=False, schedule_o_text=None,
        ),
        _row("000000076", 202312, schedule_o_text=None),
        # ---- later batch ----
        _row("000000071", 202312, schedule_o_text="second, wins"),
        _row(
            "000000072", 202312, material_diversion=pd.NA,
            is_form_990=False, schedule_o_text=None,
        ),
        _row("000000073", 202312),
    ]
)


def test_workpaper_selects_admissions_with_explanations():
    wp = diversion.build_workpaper(GOV)
    assert list(wp.ein) == [
        "000000070", "000000071", "000000072", "000000073", "000000073",
    ]
    # 74 answered No, 75 is NA on a non-990 return, 76 filed no text.
    assert not {"000000074", "000000075", "000000076"} & set(wp.ein)


def test_supersede_keeps_the_last_row_for_an_org_fiscal_year():
    """(ein, tax_period), last wins -- panel.py's rule, applied to the
    admissions. Org 71 filed twice for 202312; the later batch's text
    is the one a reviewer must read."""
    wp = diversion.build_workpaper(GOV)
    org71 = wp[wp.ein == "000000071"]
    assert len(org71) == 1
    assert org71.iloc[0].schedule_o_text == "second, wins"


def test_a_non_990_return_never_supersedes_an_admission():
    """Regression guard for the rule leg that costs 12 organizations on
    the real 2024+2025 base: dedupe the whole governance base on
    (ein, tax_period) first and org 72's 990-EZ row -- material
    diversion NA, because Part VI line 5 does not exist on that form --
    evicts a genuine admission. The workpaper supersedes among
    admissions, so it survives."""
    naive = GOV.drop_duplicates(["ein", "tax_period"], keep="last")
    naive = naive[naive.material_diversion == True]  # noqa: E712
    assert "000000072" not in set(naive.ein)  # the bug this pins

    wp = diversion.build_workpaper(GOV)
    assert "000000072" in set(wp.ein)


def test_distinct_tax_periods_are_distinct_rows_one_organization():
    wp = diversion.build_workpaper(GOV)
    org73 = wp[wp.ein == "000000073"]
    assert list(org73.tax_period) == [202212, 202312]
    assert wp.ein.nunique() == 4  # 5 admissions, 4 organizations


def test_admissions_counts_before_the_explanation_filter():
    """The runbook reconciles admissions -> workpaper rows; org 76 is
    the difference and must be visible, not silently absent."""
    adm = diversion.admissions(GOV)
    assert len(adm) == 7  # every Form 990 row with the box checked
    missing = adm[diversion.explanation_text(adm) == ""]
    assert list(missing.ein) == ["000000076"]


def test_output_is_deterministic_and_input_order_independent():
    """Same inputs -> byte-identical file. Row order within a batch is
    the supersede tie-break, but the batch stacking order is fixed by
    sorting paths, and the output is sorted by (ein, tax_period)."""
    first = diversion.build_workpaper(GOV)
    second = diversion.build_workpaper(GOV)
    assert first.to_csv(index=False) == second.to_csv(index=False)
    # Column order is pinned too -- the long text sorts last.
    assert list(first.columns)[:2] == ["ein", "tax_period"]
    assert list(first.columns)[-1] == "schedule_o_text"


def test_empty_and_column_light_frames_do_not_crash():
    assert diversion.build_workpaper(GOV.iloc[0:0]).empty
    # A governance CSV predating is_form_990 / schedule_o_text: the
    # legs that need those columns degrade instead of exploding.
    bare = pd.DataFrame(
        {"ein": ["000000070"], "tax_period": [202312], "material_diversion": [True]}
    )
    assert diversion.build_workpaper(bare).empty  # no explanation -> not reviewable


def test_diversion_cli_end_to_end():
    import os
    import tempfile
    from pathlib import Path

    from watchdog990 import cli

    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        try:
            os.chdir(d)
            # Two batches; the sorted-path order decides who supersedes,
            # so pass them in the WRONG order on the command line.
            GOV.iloc[:7].to_csv("governance_2024_TEOS_XML_01A.csv", index=False)
            GOV.iloc[7:].to_csv("governance_2025_TEOS_XML_01A.csv", index=False)
            Path("s.yaml").write_text("output_dir: out\n")
            rc = cli.main(
                ["diversion",
                 "--governance", "governance_2025_TEOS_XML_01A.csv",
                 "governance_2024_TEOS_XML_01A.csv",
                 "--label", "t", "--config", "s.yaml"]
            )
            assert rc == 0
            wp = pd.read_csv(
                "out/diversion_review_t.csv", dtype={"ein": "string"}
            )
            assert len(wp) == 5 and wp.ein.nunique() == 4
            assert wp[wp.ein == "000000071"].iloc[0].schedule_o_text == "second, wins"
            # Leading zeros survive the round trip (the assembly trap).
            assert (wp.ein.str.len() == 9).all()
            # Provenance: which batch each surviving row came from.
            assert set(wp.source) == {
                "2024_TEOS_XML_01A", "2025_TEOS_XML_01A"
            }
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("All tests passed.")

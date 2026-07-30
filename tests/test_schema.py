"""Schema-mapping and flag-degradation tests pinned to the PY2024
SOI extract layout (24eofinextractdoc.xlsx) — the real column names,
synthetic values. No downloads, no network.

Run with either:
    pytest -q
    python tests/test_schema.py
"""

from __future__ import annotations

import pandas as pd

from watchdog990 import flags, metrics
from watchdog990.schema import (
    NOT_IN_EXTRACT,
    SOI_990_COLUMN_MAP,
    to_canonical,
)

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


def _py2024_style_df() -> pd.DataFrame:
    """Two rows shaped like the real 2024 extract (verified names,
    including the uppercase EIN header)."""
    return pd.DataFrame(
        {
            "EIN": ["12-3456789", "987654321"],
            "tax_pd": [202312, 202306],
            "totrevenue": [5_000_000, 2_000_000],
            "totcntrbgfts": [3_000_000, 1_500_000],
            "totprgmrevnue": [1_800_000, 400_000],
            "totfuncexpns": [4_500_000, 1_900_000],
            "compnsatncurrofcr": [300_000, 700_000],
            "othrsalwages": [2_000_000, 500_000],
            "lessdirfndrsng": [20_000, 0],
            "totassetsend": [9_000_000, 800_000],
            "totliabend": [2_000_000, 1_100_000],
            "totnetassetend": [7_000_000, -300_000],
        }
    )


def test_every_mapped_column_resolves_on_2024_layout():
    df = to_canonical(_py2024_style_df())
    for canonical in SOI_990_COLUMN_MAP:
        assert canonical in df.columns, f"unmapped: {canonical}"
    # EIN normalized through the case-insensitive rename
    assert df["ein"].tolist() == ["123456789", "987654321"]


def test_program_revenue_maps_from_totprgmrevnue():
    # Regression: the old guess "totprgmrevn" does not exist in 2024.
    df = to_canonical(_py2024_style_df())
    assert df["program_revenue"].tolist() == [1_800_000, 400_000]


def test_missing_required_field_raises():
    bad = _py2024_style_df().drop(columns=["totrevenue"])
    try:
        to_canonical(bad)
    except ValueError as e:
        assert "total_revenue" in str(e)
    else:
        raise AssertionError("expected ValueError for missing required field")


def test_not_in_extract_fields_stay_na_and_never_flag():
    """The 2024 extract has no Part IX (B)/(D) breakdown: program and
    fundraising expense metrics must be NA, and ZERO_FUNDRAISING_COST
    must never fire on column absence — even with huge contributions."""
    for field in ("program_expenses", "fundraising_expenses"):
        assert field in NOT_IN_EXTRACT

    df = metrics.compute_all(to_canonical(_py2024_style_df()))
    assert df["program_expense_ratio"].isna().all()
    assert df["fundraising_efficiency"].isna().all()

    hits = flags.evaluate(df, THRESHOLDS)
    assert "ZERO_FUNDRAISING_COST" not in set(hits["flag_id"]), (
        "flag fired on a dataset that never carried fundraising_expenses"
    )


def test_zero_fundraising_prefers_private_basis():
    """Org with $10M total contributions but only $0.5M private (the
    rest is government grants): fires on the TOTAL basis, must NOT
    fire once the private basis is available."""
    base = {
        "ein": ["000000090"],
        "total_contributions": [10_000_000],
        "fundraising_expenses": [0],
    }
    t = dict(THRESHOLDS, large_contributions_floor=5_000_000)
    hits = flags.evaluate(pd.DataFrame(base), t)
    assert "ZERO_FUNDRAISING_COST" in set(hits.flag_id)  # fallback basis fires
    with_private = pd.DataFrame({**base, "private_contributions": [500_000]})
    hits2 = flags.evaluate(with_private, t)
    assert "ZERO_FUNDRAISING_COST" not in set(hits2.flag_id)  # private basis governs


def test_zero_fundraising_semantics_kept_when_column_present():
    """Blank-but-present fundraising on a filed return still counts
    as a reported zero — the pattern the flag exists to catch."""
    df = to_canonical(_py2024_style_df())
    df["fundraising_expenses"] = [None, None]  # present, blank
    df = metrics.compute_all(df)
    hits = flags.evaluate(df, THRESHOLDS)
    zf = hits[hits["flag_id"] == "ZERO_FUNDRAISING_COST"]
    assert set(zf["ein"]) == {"123456789", "987654321"}


def test_evaluate_survives_minimal_schema():
    """Only the REQUIRED trio present: nothing crashes, no flag fires
    off missing data."""
    df = pd.DataFrame(
        {
            "ein": ["000000009"],
            "total_revenue": [2_000_000],
            "total_expenses": [1_500_000],
            "total_contributions": [2_000_000],
        }
    )
    df = metrics.compute_all(df)
    hits = flags.evaluate(df, THRESHOLDS)
    assert hits.empty, f"flags fired on missing data: {set(hits['flag_id'])}"


def test_loader_strips_utf8_bom():
    """PY2022/PY2023 extracts ship with a BOM; the first header must
    not come back as '\\ufeffefile'."""
    import tempfile
    from pathlib import Path

    from watchdog990.ingest import soi_extract

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bom.csv"
        p.write_bytes(
            b"\xef\xbb\xbfefile,EIN,tax_pd,totrevenue,totfuncexpns\n"
            b"E,12-3456789,202212,100,90\n"
        )
        df = soi_extract.load(p)
    assert "efile" in df.columns
    assert df["ein"].iloc[0] == "123456789"


def test_report_lists_flag_ids_per_org():
    """Regression: a column named 'flags' collides with the pandas
    Series.flags attribute and the summary printed the internal
    object instead of the flag IDs."""
    import tempfile
    from pathlib import Path

    from watchdog990 import report

    hits = pd.DataFrame(
        {
            "ein": ["000000001", "000000001", "000000002"],
            "flag_id": ["NEGATIVE_NET_ASSETS", "THIN_RUNWAY", "OFFICER_COMP_HEAVY"],
            "severity": ["high", "low", "medium"],
            "description": ["d1", "d2", "d3"],
        }
    )
    with tempfile.TemporaryDirectory() as d:
        _, md = report.write(hits, d, "t")
        text = Path(md).read_text()
    assert "NEGATIVE_NET_ASSETS, THIN_RUNWAY" in text
    assert "<Flags(" not in text
    assert report.DISCLAIMER.splitlines()[0] in text


def test_settings_extract_file_keys_are_strings():
    """Unquoted YAML year keys parse as ints; load_settings must
    normalize them so `--label 2024` finds the file."""
    import tempfile
    from pathlib import Path

    from watchdog990.utils import load_settings

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "s.yaml"
        p.write_text("extract_files:\n  2024: data/raw/x.csv\n")
        s = load_settings(p)
    assert s["extract_files"].get("2024") == "data/raw/x.csv"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("All tests passed.")

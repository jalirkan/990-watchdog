"""Phase-3 tests: governance parsing from e-file XML fixtures.

Synthetic returns in the modern (TY2013+) namespaced shape — no
downloads, no network. The ALTERNATES names these fixtures exercise
still carry VERIFY status until a real TEOS batch is parsed.

Run with either:
    pytest -q
    python tests/test_efile_xml.py
"""

from __future__ import annotations

import pandas as pd

from watchdog990.ingest import efile_xml

NS = "http://www.irs.gov/efile"

CLEAN = f"""<?xml version="1.0" encoding="utf-8"?>
<Return xmlns="{NS}" returnVersion="2023v5.0">
  <ReturnHeader>
    <TaxPeriodEndDt>2023-12-31</TaxPeriodEndDt>
    <Filer><EIN>111000111</EIN></Filer>
  </ReturnHeader>
  <ReturnData>
    <IRS990>
      <GoverningBodyVotingMembersCnt>9</GoverningBodyVotingMembersCnt>
      <IndependentVotingMemberCnt>8</IndependentVotingMemberCnt>
      <MaterialDiversionOrMisuseInd>false</MaterialDiversionOrMisuseInd>
      <LoanOutstandingInd>false</LoanOutstandingInd>
    </IRS990>
  </ReturnData>
</Return>
"""

DIRTY = f"""<?xml version="1.0" encoding="utf-8"?>
<Return xmlns="{NS}" returnVersion="2022v4.1">
  <ReturnHeader>
    <TaxPeriodEndDt>2022-06-30</TaxPeriodEndDt>
    <Filer><EIN>22-2000222</EIN></Filer>
  </ReturnHeader>
  <ReturnData>
    <IRS990>
      <GoverningBodyVotingMembersCnt>9</GoverningBodyVotingMembersCnt>
      <IndependentVotingMemberCnt>2</IndependentVotingMemberCnt>
      <MaterialDiversionOrMisuseInd>X</MaterialDiversionOrMisuseInd>
      <LoanOutstandingInd>1</LoanOutstandingInd>
    </IRS990>
    <IRS990ScheduleL><Anything/></IRS990ScheduleL>
  </ReturnData>
</Return>
"""

EZ = f"""<?xml version="1.0" encoding="utf-8"?>
<Return xmlns="{NS}" returnVersion="2023v5.0">
  <ReturnHeader>
    <TaxPeriodEndDt>2023-12-31</TaxPeriodEndDt>
    <Filer><EIN>333000333</EIN></Filer>
  </ReturnHeader>
  <ReturnData><IRS990EZ/></ReturnData>
</Return>
"""


def test_clean_return_parses():
    rec = efile_xml.parse_return(CLEAN.encode())
    assert rec["ein"] == "111000111"
    assert rec["tax_period"] == 202312
    assert rec["material_diversion"] is False
    assert rec["loans_to_insiders"] is False
    assert rec["voting_members"] == 9 and rec["independent_members"] == 8
    assert abs(rec["board_independence"] - 8 / 9) < 1e-9
    assert rec["schedule_l_present"] is False
    assert rec["is_form_990"] is True
    assert rec["schema_version"] == "2023v5.0"


def test_dirty_return_checkbox_and_numeric_bools():
    rec = efile_xml.parse_return(DIRTY.encode())
    assert rec["material_diversion"] is True  # "X" checkbox style
    assert rec["loans_to_insiders"] is True  # "1" style
    assert rec["schedule_l_present"] is True
    assert abs(rec["board_independence"] - 2 / 9) < 1e-9
    assert rec["tax_period"] == 202206


def test_ez_return_marked_not_form_990():
    rec = efile_xml.parse_return(EZ.encode())
    assert rec["is_form_990"] is False
    assert pd.isna(rec["material_diversion"])  # absent, never fake-False


def test_load_dir_and_zip_and_ein_normalization():
    import tempfile
    import zipfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "a.xml").write_text(CLEAN)
        (d / "b.xml").write_text(DIRTY)
        (d / "broken.xml").write_text("<not-xml")
        with zipfile.ZipFile(d / "batch.zip", "w") as zf:
            zf.writestr("sub/c.xml", EZ)
            zf.writestr("readme.txt", "not xml")
        df = efile_xml.load(d)

    assert len(df) == 3  # clean + dirty + zipped EZ; broken skipped
    assert set(df.ein) == {"111000111", "222000222", "333000333"}  # dash stripped
    dirty = df[df.ein == "222000222"].iloc[0]
    assert dirty.material_diversion == True  # noqa: E712


def test_xml_cli_end_to_end():
    import os
    import tempfile
    from pathlib import Path

    from watchdog990 import cli

    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        try:
            os.chdir(d)
            Path("xmls").mkdir()
            Path("xmls/a.xml").write_text(CLEAN)
            Path("xmls/b.xml").write_text(DIRTY)
            Path("s.yaml").write_text("output_dir: out\n")
            rc = cli.main(
                ["xml", "--path", "xmls", "--label", "t", "--config", "s.yaml"]
            )
            assert rc == 0
            gov = pd.read_csv("out/governance_t.csv", dtype={"ein": "string"})
            assert len(gov) == 2
            assert set(gov.columns) >= {
                "ein", "tax_period", "material_diversion",
                "loans_to_insiders", "board_independence",
                "schedule_l_present", "schema_version",
            }
        finally:
            os.chdir(cwd)


def test_governance_flags_fire_for_panel_orgs_only():
    from watchdog990 import flags

    gov = pd.DataFrame(
        {
            "ein": ["000000070", "000000071", "000000072", "000000073"],
            "material_diversion": [True, True, False, pd.NA],
        }
    )
    hits = flags.governance_flags(gov, panel_eins={"000000070", "000000072", "000000073"})
    assert set(hits.ein) == {"000000070"}  # in panel + admitted
    assert hits.iloc[0].flag_id == "MATERIAL_DIVERSION"
    assert hits.iloc[0].severity == "high"
    # org 71 admitted but not in panel; 72 answered No; 73 unknown -> none fire


def test_xml_plan_ranks_batches_by_flagged_coverage():
    import os
    import tempfile
    from pathlib import Path

    from watchdog990 import cli

    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        try:
            os.chdir(d)
            Path("flags.csv").write_text(
                "ein,flag_id\n111000111,THIN_RUNWAY\n222000222,CHRONIC_DEFICITS\n"
            )
            Path("index.csv").write_text(
                "RETURN_ID,FILING_TYPE,EIN,TAX_PERIOD,SUB_DATE,TAXPAYER_NAME,"
                "RETURN_TYPE,DLN,OBJECT_ID,XML_BATCH_ID\n"
                "1,EFILE,111000111,202312,2024,A,990,d1,o1,2024_TEOS_XML_02A\n"
                "2,EFILE,222000222,202306,2024,B,990,d2,o2,2024_TEOS_XML_02A\n"
                "3,EFILE,999999999,202312,2024,C,990,d3,o3,2024_TEOS_XML_03A\n"
            )
            Path("s.yaml").write_text("output_dir: out\n")
            rc = cli.main(
                ["xml-plan", "--flags", "flags.csv", "--index", "index.csv",
                 "--label", "t", "--config", "s.yaml"]
            )
            assert rc == 0
            plan = pd.read_csv("out/xml_plan_t.csv")
            top = plan.iloc[0]
            assert top.XML_BATCH_ID == "2024_TEOS_XML_02A"
            assert top.flagged_orgs == 2
            assert "2024_TEOS_XML_03A" not in set(plan.XML_BATCH_ID)
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("All tests passed.")

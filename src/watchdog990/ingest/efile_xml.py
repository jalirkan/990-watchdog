"""Phase 3: governance signals from IRS Form 990 e-file XML.

The SOI extracts will never carry these; the full e-filed return
does. This module parses the four governance signals the roadmap
names, from local XML files or the IRS's monthly TEOS zip archives
(no extraction needed — zips are read in place).

Signals (Form 990, 2013+ schema era):
  material_diversion    Part VI line 5   -- "did you discover a
                        material diversion of assets?" checkbox
  loans_to_insiders     Part IV line 26  -- loan to/from interested
                        person outstanding?
  board independence    Part I lines 3-4 -- voting members vs
                        independent voting members
  schedule_l_present    Schedule L filed -- transactions with
                        interested persons

Design notes, same discipline as schema.py:
- ALTERNATES maps each canonical field to the XML element names it
  may appear under across schema versions. Names marked VERIFY are
  best-effort from the modern (TY2013+) schemas and must be checked
  against the first real TEOS batch: an unexpectedly high NA rate in
  the output IS the alarm.
- Every parsed row records the return's schema version and, per
  field, nothing is guessed: unmatched -> NA, never a fake False.
- Namespace handling uses the {*} wildcard, so the IRS namespace
  URI (which has drifted) never matters.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd

from watchdog990.schema import normalize_ein

log = logging.getLogger(__name__)

# canonical -> candidate element local-names, tried in order. VERIFY
# entries are unconfirmed against a real TEOS batch.
ALTERNATES: dict[str, list[str]] = {
    "ein": ["EIN"],
    "tax_period_end": ["TaxPeriodEndDt", "TaxPeriodEndDate"],  # VERIFY older name
    "material_diversion": ["MaterialDiversionOrMisuseInd"],
    "loans_to_insiders": ["LoanOutstandingInd"],  # VERIFY (Part IV-26)
    "voting_members": [
        "GoverningBodyVotingMembersCnt",
        "GoverningBodyVotingMembersCount",  # VERIFY older name
    ],
    "independent_members": [
        "IndependentVotingMemberCnt",
        "IndependentVotingMembersCnt",  # VERIFY variant
    ],
}

_TRUE = {"true", "1", "x", "yes"}
_FALSE = {"false", "0", "no"}


def _to_bool(text: str | None):
    if text is None:
        return pd.NA
    t = text.strip().lower()
    if t in _TRUE:
        return True
    if t in _FALSE:
        return False
    return pd.NA


def _find_text(root, names: list[str]) -> str | None:
    for name in names:
        el = root.find(f".//{{*}}{name}")
        if el is not None and el.text is not None:
            return el.text
    return None


def parse_return(source) -> dict:
    """Parse one e-filed return (path, bytes, or file-like) into a
    flat governance record. Missing/unmatched fields come back NA."""
    if isinstance(source, (str, Path)):
        tree = ElementTree.parse(source)
        root = tree.getroot()
    else:
        root = ElementTree.fromstring(source)

    rec: dict = {"schema_version": root.attrib.get("returnVersion", pd.NA)}

    ein = _find_text(root, ALTERNATES["ein"])
    rec["ein"] = ein if ein else pd.NA

    tpe = _find_text(root, ALTERNATES["tax_period_end"])
    # YYYY-MM-DD -> YYYYMM to match the extract convention
    rec["tax_period"] = (
        int(tpe[:7].replace("-", "")) if tpe and len(tpe) >= 7 else pd.NA
    )

    rec["material_diversion"] = _to_bool(
        _find_text(root, ALTERNATES["material_diversion"])
    )
    rec["loans_to_insiders"] = _to_bool(
        _find_text(root, ALTERNATES["loans_to_insiders"])
    )

    vm = _find_text(root, ALTERNATES["voting_members"])
    im = _find_text(root, ALTERNATES["independent_members"])
    rec["voting_members"] = int(vm) if vm and vm.strip().isdigit() else pd.NA
    rec["independent_members"] = (
        int(im) if im and im.strip().isdigit() else pd.NA
    )
    if rec["voting_members"] is not pd.NA and rec["independent_members"] is not pd.NA:
        rec["board_independence"] = (
            rec["independent_members"] / rec["voting_members"]
            if rec["voting_members"]
            else pd.NA
        )
    else:
        rec["board_independence"] = pd.NA

    rec["schedule_l_present"] = root.find(".//{*}IRS990ScheduleL") is not None
    # A record is only a Form 990 governance record if the core 990
    # form is present (the TEOS batches also carry 990-EZ/PF).
    rec["is_form_990"] = root.find(".//{*}IRS990") is not None
    return rec


def load(path: str | Path) -> pd.DataFrame:
    """Parse every return under `path`.

    Accepts a directory (reads *.xml recursively, plus any *.zip in
    it) or a single .zip / .xml file. Malformed files are logged and
    skipped, never fatal — one broken return must not sink a batch.
    """
    path = Path(path)
    records: list[dict] = []
    bad = 0

    def _from_zip(zp: Path):
        nonlocal bad
        with zipfile.ZipFile(zp) as zf:
            for name in zf.namelist():
                if not name.lower().endswith(".xml"):
                    continue
                try:
                    records.append(parse_return(zf.read(name)))
                except ElementTree.ParseError:
                    bad += 1

    if path.is_dir():
        for f in sorted(path.rglob("*.xml")):
            try:
                records.append(parse_return(f))
            except ElementTree.ParseError:
                bad += 1
        for z in sorted(path.glob("*.zip")):
            _from_zip(z)
    elif path.suffix.lower() == ".zip":
        _from_zip(path)
    else:
        records.append(parse_return(path))

    if bad:
        log.warning("Skipped %d unparseable XML file(s)", bad)
    df = pd.DataFrame.from_records(records)
    if not df.empty:
        df["ein"] = normalize_ein(df["ein"])
    return df

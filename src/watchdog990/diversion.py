"""Phase 5: the material-diversion review workpaper.

`watchdog990 xml` writes one governance CSV per TEOS batch, each row a
parsed return. The manual-review gate (docs/methodology.md, and the
protocol in docs/ai-assisted-review.md) needs the other shape: one row
per *admission* — an organization-fiscal-year whose Form 990 checked
Part VI line 5 — carrying that filing's own Schedule O explanation.

Until now that file was assembled by hand ("concatenate the governance
CSVs"), so the exact rule behind the recorded counts was never written
down and could not be re-run. This module IS the rule.

Selection rule (deliberate, and each leg is load-bearing):

1. **Form 990 only.** `is_form_990` marks returns carrying the core
   IRS990 form. Part VI line 5 exists nowhere else, so a 990-EZ/PF row
   can only ever contribute NA — and, critically, must never be
   allowed to supersede a real admission (see leg 3).
2. **`material_diversion is True`.** A checked box on a signed return.
   NA is unknown, never a fake False, same discipline as everywhere.
3. **Supersede on (ein, tax_period), last wins — among admissions.**
   Files stack in sorted order, so a later batch supersedes an earlier
   one and, within a file, the last occurrence wins: the same rule
   panel.py documents for filings. It is applied to the *admissions*,
   not to the whole governance base, and that distinction is the whole
   ballgame. Deduplicating the full base first lets a same-period
   990-EZ/PF row (material_diversion NA) evict a genuine admission —
   measured on the 2024+2025 base, 12 organizations vanish that way.
   An admission is a statement that was filed; a different return for
   the same period does not unfile it.
4. **A Schedule O explanation must be present.** The workpaper exists
   to put the explanation in front of a reviewer; an admission with no
   text is a different (and reportable) condition, so it is dropped
   here and counted out loud rather than passed off as reviewable.

Reproduction check, 2026-08-28: legs 1-4 over the twelve 2024 batches
yield 327 admissions — exactly the count docs/data-sources.md records
for `diversion_review_2024.csv`, and exactly the "728,719 index rows
minus 3 duplicate diversion rows superseded" arithmetic recorded in
the same entry. The combined 2024-2025 figure does not reproduce; see
the dated note in docs/methodology.md.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from watchdog990.schema import normalize_ein

log = logging.getLogger(__name__)

# Reviewer-facing column order: identity, then the governance context
# that sorts the queue, then the long explanation text last so the CSV
# stays readable in a spreadsheet.
WORKPAPER_COLUMNS = [
    "ein",
    "tax_period",
    "schema_version",
    "voting_members",
    "independent_members",
    "board_independence",
    "loans_to_insiders",
    "schedule_l_present",
    "total_expenses_xml",
    "program_expenses",
    "fundraising_expenses",
    "source",
    "schedule_o_text",
]


def explanation_text(gov: pd.DataFrame) -> pd.Series:
    """Schedule O text as a stripped string ("" where absent)."""
    if "schedule_o_text" not in gov.columns:
        return pd.Series("", index=gov.index, dtype="object")
    return gov["schedule_o_text"].fillna("").astype(str).str.strip()


def admissions(gov: pd.DataFrame) -> pd.DataFrame:
    """Every Form 990 row admitting a material diversion (legs 1-2).

    Pre-supersede and pre-explanation-filter on purpose: the counts
    either side of those steps are what the runbook check reads.
    """
    if gov.empty or "material_diversion" not in gov.columns:
        return gov.iloc[0:0]
    is_990 = gov["is_form_990"] == True if "is_form_990" in gov.columns else True  # noqa: E712
    return gov[(gov["material_diversion"] == True) & is_990]  # noqa: E712


def build_workpaper(gov: pd.DataFrame) -> pd.DataFrame:
    """Governance records -> the review workpaper (legs 1-4 above).

    One row per superseded (ein, tax_period), sorted by (ein,
    tax_period) so the same inputs always produce the same file.
    """
    adm = admissions(gov)
    adm = adm[explanation_text(adm) != ""]
    adm = adm.drop_duplicates(subset=["ein", "tax_period"], keep="last")
    out = adm.sort_values(["ein", "tax_period"], kind="stable")
    # Known columns in reviewer order, anything else the parser gained
    # since, then the explanation text last whatever happens.
    named = [c for c in WORKPAPER_COLUMNS if c in out.columns]
    extra = [c for c in out.columns if c not in WORKPAPER_COLUMNS]
    tail = ["schedule_o_text"] if "schedule_o_text" in named else []
    cols = [c for c in named if c not in tail] + extra + tail
    return out[cols].reset_index(drop=True)


def load_governance(paths) -> pd.DataFrame:
    """Stack governance CSVs into the admissions frame.

    Paths are SORTED before stacking, because the supersede rule is
    "last wins" and a shell glob's order must not decide which return
    survives. Each surviving row records the file it came from.

    `ein` is read as a string and re-normalized: read as int64 pandas
    silently strips leading zeros from the ~4.5% of EINs that have
    them (docs/data-sources.md, "Assembly note, learned by getting it
    wrong"). Rows are filtered to admissions as each file is read —
    equivalent under the rule above, and it keeps a 1.4M-row base out
    of memory.
    """
    frames: list[pd.DataFrame] = []
    for p in sorted(Path(x) for x in paths):
        df = pd.read_csv(p, dtype={"ein": "string"}, low_memory=False)
        df = admissions(df).copy()
        df["source"] = p.stem.removeprefix("governance_")
        frames.append(df)
        log.info("%s: %s admission(s)", p, f"{len(df):,}")
    if not frames:
        return pd.DataFrame(columns=["ein", "tax_period", "material_diversion"])
    out = pd.concat(frames, ignore_index=True)
    out["ein"] = normalize_ein(out["ein"])
    return out

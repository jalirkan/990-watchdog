# Data sources

All public, all free. Links verified live July 2026; if one moves,
update `config/settings.yaml` -- code never hardcodes URLs.

## 1. IRS SOI Annual Extract of Tax-Exempt Organization Financial Data
Index: see `sources.soi_extract_index` in settings.

Selected financial fields from every Form 990 / 990-EZ / 990-PF filed
by active organizations in a calendar year, as CSV. This is the bulk
screening backbone: one file, hundreds of thousands of filers,
pandas-ready. Each year ships with a field layout doc -- use it to
confirm the VERIFY entries in `src/watchdog990/schema.py`.

Limitations: selected fields only (the functional expense breakdown
and governance checkboxes may not be present), IRS processing
adjustments, transcription noise on paper filings.

**Confirmed for PY2024 (2026-07-29):** the Form 990 extract reports
Part IX functional expenses as column (A) totals only — no program
(B) / management (C) / fundraising (D) breakdown. Therefore
`program_expense_ratio` and `fundraising_efficiency` are NA for every
org this phase, and `ZERO_FUNDRAISING_COST` cannot fire (by design —
see `NOT_IN_EXTRACT` in `src/watchdog990/schema.py`). E-file XML
(phase 3) is the route to those fields.

## Files used — phase 1 go-live (recorded 2026-07-29)

| File | Source URL | Notes |
|---|---|---|
| `data/raw/24eoextract990.csv` | https://www.irs.gov/pub/irs-soi/24eoextract990.zip (unzipped) | PY2024 Form 990 extract; 345,365 records — matches layout doc's stated count exactly |
| `data/raw/24eofinextractdoc.xlsx` | https://www.irs.gov/pub/irs-soi/24eofinextractdoc.xlsx | Official field layout doc used to verify every `schema.py` mapping; sheet "990", 246 elements (246/246 match the CSV header both directions) |
| `data/raw/eo_ny.csv` | https://www.irs.gov/pub/irs-soi/eo_ny.csv | EO BMF, New York; posting dated 2026-07-14 |
| `data/raw/eo_ca.csv` | https://www.irs.gov/pub/irs-soi/eo_ca.csv | EO BMF, California; posting dated 2026-07-14 |

A machine-readable copy of the layout doc's 990 sheet is kept at
`data/interim/990_layout_2024.csv` for grepping (gitignored, regenerate
from the xlsx).

## Files added — phase 2 (recorded 2026-07-29)

| File | Source URL | Notes |
|---|---|---|
| `data/raw/23eoextract990.csv` | https://www.irs.gov/pub/irs-soi/23eoextract990.zip | PY2023 Form 990 extract; layout doc count 338,048 |
| `data/raw/23eofinextractdoc.xlsx` | https://www.irs.gov/pub/irs-soi/23eofinextractdoc.xlsx | 246/246 elements match CSV both directions |
| `data/raw/22eoextract990.csv` | https://www.irs.gov/pub/irs-soi/22eoextract990.zip | PY2022 Form 990 extract; layout doc count 326,119 |
| `data/raw/22eofinextractdoc.xlsx` | https://www.irs.gov/pub/irs-soi/22eofinextractdoc.xlsx | 246/246 elements match CSV both directions |
| `data/raw/eo1.csv` … `eo4.csv` | https://www.irs.gov/pub/irs-soi/eo1.csv (…eo2, eo3, eo4) | Full-country EO BMF by region, posting dated 2026-07-14; NTEE source |

Cross-year layout finding: PY2022–PY2024 Form 990 extracts share an
identical 246-element layout (name-for-name), so one column map in
schema.py serves all three years. Cosmetic drift only: EIN header
case varies (2022 `EIN`, 2023 `ein`), and the 2022/2023 CSVs carry a
UTF-8 BOM (loader reads `utf-8-sig`). No year carries the Part IX
(B)/(C)/(D) functional-expense breakdown.

## Files added — six-year window (recorded 2026-07-30)

| File | Source URL | Notes |
|---|---|---|
| `data/raw/21eoextract990.csv` | https://www.irs.gov/pub/irs-soi/21eoextract990.zip | PY2021; 342,920 rows = doc count exactly |
| `data/raw/20eoextract990.csv` | https://www.irs.gov/pub/irs-soi/20eoextract990.zip | PY2020; 273,971 rows = doc count exactly; header has stray trailing commas (unnamed cols, unmapped, harmless) |
| `data/raw/19eoextract990.csv` | https://www.irs.gov/pub/irs-soi/19eoextract990.zip | PY2019; 304,441 rows = doc count exactly; e-file indicator named `elf` (doc agrees; unmapped) |
| matching `*eofinextractdoc.xlsx` | same index page | each verified 246 elements, all mapped fields present, no Part IX (B)/(C)/(D) any year 2019–2024 |

## 2. IRS Exempt Organizations Business Master File (EO BMF)
Index: see `sources.eo_bmf_index` in settings.

Cumulative org registry as per-state/region CSVs: EIN, name, address,
NTEE code, subsection. Join target for putting names on flagged EINs.

## 3. ProPublica Nonprofit Explorer API (v2)
Base: see `sources.propublica_api_base` in settings.

Free, keyless JSON API over the same IRS data -- org profiles,
per-year extracted financials, and links to filing documents. Used
here for spot lookups and enrichment, not bulk pulls. Subject to
ProPublica's Data Terms of Use; keep the courtesy rate limiting in
`ingest/propublica.py`.

## 4. IRS Form 990 e-file XML (phase 3, parser landed 2026-07-30)
Index: https://www.irs.gov/charities-non-profits/form-990-series-downloads

Full e-filed returns as XML — where the governance signals live
(material diversion checkbox, loans to insiders, board independence,
Schedule L). Distribution (verified live 2026-07-30):

- Monthly zips per calendar year, e.g.
  `https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_01A.zip`
  (large months split into A/B/... parts).
- **Per-year index CSV** listing every return and which zip carries
  it, e.g. `https://apps.irs.gov/pub/epostcard/990/xml/2024/index_2024.csv`
  — use it to find the exact zips covering flagged EINs instead of
  bulk-downloading a whole year.

`watchdog990 xml --path <dir-or-zip>` parses files or TEOS zips in
place (no extraction) into `outputs/governance_<label>.csv`, printing
per-field NA rates as the verification alarm. The `irsx` library
remains worth evaluating if parsing needs grow past these four
signals; the current hand-rolled parser is deliberately minimal.

**Validated 2026-07-30** on `2024_TEOS_XML_01A.zip` (105 MB, in
`data/raw/`): 17,246 returns (9,682 Form 990), schema versions
2021v4.0-2023v4.0, 0.00% NA on every parsed field, zero unparseable
files. Batch stats: material diversion 0.06% of 990s, insider loans
2.01%, median board fully independent, Schedule L on 6.38%. One
diversion admission tied to its real filing via ProPublica (a small
California housing organization; identity withheld pending the
Schedule O review gate). `index_2024.csv` (also in data/raw/) maps
every 2024 return to its batch zip for targeted downloads.

**Batches on hand (2026-07-30): ALL TWELVE 2024 monthly batches** —
728,716 records parsed (matches the index's 728,719 minus 3
duplicate diversion rows superseded during the Schedule O patch),
zero unparseable files, 363,097 Form 990s. 327 material-diversion
admissions, each carrying its Schedule O explanation
(outputs/diversion_review_2024.csv is the review workpaper).
Expense-breakdown coverage: 79.8% of the panel period-matched;
governance context on 83.0% of flagged orgs. index_2025.csv on hand;
outputs/xml_plan_2025.csv ranks 2025 batches for the next round
(top: 11A/11D/11C/04A).

**2025 targeted round (2026-07-30):** seven batches parsed (04A,
08A, 09A, 11A-11D), 379,996 returns, zero unparseable, 178 further
diversion admissions. Unified governance base
(outputs/governance_all.csv): 1,067,727 records; newer submissions
supersede on (EIN, tax period). Governance context now covers 84.4%
of flagged orgs; the combined diversion workpaper
(outputs/diversion_review_2024-2025.csv) holds 432 unique orgs, all
with Schedule O explanations.

**2025 completion round (2026-08-28):** the remaining eight batches
parsed (01A, 02A, 03A, 05A, 06A, 07A, 10A, 12A) — all fifteen 2025
batches now local. 287,140 returns parsed, zero unparseable, 140,668
Form 990s. Per-batch reconciliation against `index_2025.csv`:

| Batch | Index rows | Parsed | Unparseable | Form 990 |
|---|---:|---:|---:|---:|
| 2025_TEOS_XML_01A | 17,044 | 17,044 | 0 | 9,264 |
| 2025_TEOS_XML_02A | 41,855 | 41,855 | 0 | 21,917 |
| 2025_TEOS_XML_03A | 41,570 | 41,570 | 0 | 18,701 |
| 2025_TEOS_XML_05A | 163,540* | 81,770 | 0 | 35,943 |
| 2025_TEOS_XML_05B | (same label)* | 81,770 | 0 | 38,476 |
| 2025_TEOS_XML_06A | 44,824 | 44,824 | 0 | 22,445 |
| 2025_TEOS_XML_07A | 24,854 | 24,854 | 0 | 13,419 |
| 2025_TEOS_XML_10A | 9,836 | 9,836 | 0 | 5,085 |
| 2025_TEOS_XML_12A | 25,387 | 25,387 | 0 | 13,894 |

*Batch 05 is split across two files under one index label — see below.
All sixteen files tie to the index once 05A and 05B are read together (the seven from
the 2026-07-30 round re-verified at 379,996, matching that record).

**Resolved — batch 05 ships as two files under one index label.**
The index assigns 163,540 returns to `2025_TEOS_XML_05A`, but that zip
carries 81,770. This looks exactly like a truncated download and is
not one: the server reports `content-length: 495924982` for 05A, byte
for byte what is on disk, so re-fetching returns the identical file.
**`2025_TEOS_XML_05B.zip` exists on the server and is not named
anywhere in the index** (every one of its returns is labelled
`2025_TEOS_XML_05A` there). The two partition the batch exactly:
81,770 members each, zero overlap, and their union reproduces the
index's 163,540 `OBJECT_ID`s — 05A holds the first half sorted by
`OBJECT_ID`, 05B the second. Both are Deflate64.

The lesson is a check, not a filename: **an archive that opens
cleanly is not the same as an archive that is complete.** Every
integrity test 05A passes — valid central directory, every member
extracts — and it still held half the batch. Reconcile member counts
against the index per batch, and when a batch comes up exactly short,
probe for a `<batch>B` sibling before concluding the retrieval failed.
No other 2025 batch has one; the remaining fourteen tie to the index.

Per-field NA rates on the eight batches are in line with the 2024
base — core governance fields (tax_period, material_diversion,
loans_to_insiders, voting_members, independent_members) 0.00% on
every batch, board_independence 1.3–2.1%, program/fundraising
expenses 4.2–6.8%, total_contributions 13.7–15.8%, govt_grants
61.7–69.5% (the 2024 batches run 62–71% on the same field; the
element is simply absent when there are no government grants). No
field moved enough to suspect an element rename.

Unified governance base rebuilt over all 2024 + all sixteen 2025
files (`outputs/governance_all.csv`): **1,420,080 records** (from
1,067,727), 57,545 superseded on (EIN, tax period). Governance
context now covers **86.8% of flagged orgs** (109,244 of 125,833),
up from 84.9% (106,817 of 125,749) measured on the same code with the
pre-round base. The last 0.2pp came from 05B alone, which is the
practical reason the split above is worth documenting rather than
filing as a curiosity.

Assembly note, learned by getting it wrong: concatenate the per-batch
CSVs with `dtype={"ein": "string"}`. Read without it, pandas infers
`ein` as int64 and silently strips leading zeros; the rebuilt file
then fails to join for the ~4.5% of orgs whose EIN starts with 0, and
the symptom is *coverage going down* after adding batches. The check
that catches it: the unified base must have 9-character EINs on every
row. Rebuilding the 2026-07-30 base with the correct dtype reproduces
1,067,727 records and 47,699 leading-zero EINs exactly.

**Gotcha, learned the hard way:** some TEOS batches ship with
Deflate64 compression, which Python's zipfile cannot read. Confirmed
on **2025_TEOS_XML_11B, 2025_TEOS_XML_05A and 2025_TEOS_XML_05B**
(all entirely compression method 9; every other batch on hand is
method 8). Fix:
extract with Info-ZIP `unzip` (supports enhanced deflate) and point
the parser at the folder. Note the actual symptom with the current
parser: `_from_zip` catches only `ElementTree.ParseError`, so a
Deflate64 member raises `NotImplementedError: That compression method
is not supported` and the command aborts on the first file — it does
not report "~100% unparseable" as the runbook's wording suggests.
Either way, check the compression method before suspecting the
parser.

## Corrections to earlier records (recorded 2026-08-28)

Verified during the completion round; the original entries above are
left as written and corrected here rather than edited in place.

- **UTF-8 BOM is wider than recorded.** The phase-2 note says the
  2022 and 2023 extract CSVs carry a BOM. Checked byte-for-byte on
  all six: 2019, 2020, 2021, 2022 and 2023 all begin `EF BB BF`;
  **2024 does not**. Harmless — the loader reads `utf-8-sig` — but
  the record was incomplete.
- **The combined diversion workpaper's 432 does not reproduce.** The
  2025-round entry above records
  `outputs/diversion_review_2024-2025.csv` at 432 unique
  organizations; no command built that file, and the rule was never
  written down. There is one now — `watchdog990 diversion` — and it
  reproduces the 2024 workpaper's 327 exactly (including the "minus 3
  duplicate diversion rows" arithmetic in the 2026-07-30 entry) while
  yielding **440** on the same seven-batch 2025 base that 432 was
  measured on, and 560 on today's sixteen-file base. Growth is not
  the explanation; the restricted rebuild ties to 1,067,727 records
  exactly. The 432 stands as written above. Rule, the alternatives
  measured, and the two filters that hit 432 by fabrication rather
  than by method: `methodology.md`, entry dated 2026-08-28.
- **2024_TEOS_XML_01A schema versions.** Recorded above as
  "2021v4.0-2023v4.0". Observed on the parsed batch: **2020v1.3 through
  2023v4.0**, ten distinct versions (2020v1.3, 2020v4.0, 2020v4.1,
  2020v4.2, 2021v4.0, 2021v4.1, 2021v4.2, 2022v5.0, 2022v7.0,
  2023v4.0); the bulk is 2022v5.0 (15,369 of 17,246). The recorded
  floor was two minor versions too high. For contrast, the 2025 01A
  batch spans 2021v4.0-2024v5.0 across thirteen versions.

Targeted acquisition workflow:
1. `watchdog990 xml-plan --flags outputs/flags_<label>.csv --index
   data/raw/index_<year>.csv` ranks batch zips by flagged-org
   coverage (2024 result: 82.1% of flagged orgs have a 2024 e-filed
   return; batches 11A + 05A alone cover ~39k of 74k).
2. Download the top batches, `watchdog990 xml --path <zip>` each.
3. `watchdog990 trend --stage report --governance <governance csv>`
   joins the signals onto flagged orgs (context columns in the flags
   CSV + a summary section).

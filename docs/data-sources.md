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
diversion admission tied to its real filing via ProPublica (EIN
943292800, FY 2023-09). `index_2024.csv` (also in data/raw/) maps
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

Targeted acquisition workflow:
1. `watchdog990 xml-plan --flags outputs/flags_<label>.csv --index
   data/raw/index_<year>.csv` ranks batch zips by flagged-org
   coverage (2024 result: 82.1% of flagged orgs have a 2024 e-filed
   return; batches 11A + 05A alone cover ~39k of 74k).
2. Download the top batches, `watchdog990 xml --path <zip>` each.
3. `watchdog990 trend --stage report --governance <governance csv>`
   joins the signals onto flagged orgs (context columns in the flags
   CSV + a summary section).

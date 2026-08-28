# Annual Refresh Runbook

How to keep 990 Watchdog current, once a year (or whenever the IRS
posts new files). Written so that anyone — including you in twelve
months — can run the cycle without rediscovering it. Each step names
its check; a refresh without the checks is not a refresh.

## 1. New SOI extract year (when the IRS posts it)

Source: https://www.irs.gov/statistics/soi-tax-stats-annual-extract-of-tax-exempt-organization-financial-data

Download the new year's Form 990 extract zip AND its layout doc
(`<yy>eofinextractdoc.xlsx`) into `data/raw/`, unzip the extract.

**Verification drill (never skip — this is where the IRS breaks
things):** compare the layout doc's 990 sheet against the CSV header
in both directions; confirm every `SOI_990_COLUMN_MAP` source name
resolves; confirm the physical row count ties to the doc's stated
count; check for Part IX (B)/(C)/(D) columns (if the IRS ever adds
the functional breakdown to the extract, update `NOT_IN_EXTRACT` and
celebrate). Historical quirks to expect: BOM on some years, EIN
header case drift, stray trailing commas, the e-file indicator
renamed (`elf` in 2019). If names drifted: fix `schema.py` only, add
a test pinned to the real names, record the finding in
`data-sources.md`.

Then add the year under `extract_files` in `config/settings.yaml`
(quote the key: `"2025":`) and record the files in
`data-sources.md`.

## 2. Refresh the BMF

Source: https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf

Re-download `eo1.csv`–`eo4.csv` (it's cumulative; the posting date is
on the page). Note the posting date in `data-sources.md`.

## 3. Re-run the trend screen

```
watchdog990 trend
```

(or the staged form on small machines: `--stage panel`, then
`--stage names --bmf data/raw/eo1.csv data/raw/eo2.csv`, then
`--stage names --bmf data/raw/eo3.csv data/raw/eo4.csv`, then
`--stage report --governance <governance csv>`).

**Checks:** panel row count reconciles to the sum of per-year counts
minus dropped/deduped rows (the log prints each); per-flag rates
compared against the tuning log's last measurements — drift of a few
tenths is life, a flag doubling or halving is a finding. If any flag
fires on a dramatically different share, do not retune silently:
measure alternatives, write the evidence, propose. The tuning log in
`methodology.md` shows the format.

## 4. New XML year (governance + expense breakdown)

Source: https://www.irs.gov/charities-non-profits/form-990-series-downloads

Download the new year's `index_<year>.csv`, then run the planner to
target batches instead of hoarding them:

```
watchdog990 xml-plan --flags outputs/flags_<label>.csv --index data/raw/index_<year>.csv --label <year>
```

Download the top-ranked batch zips, then parse each (no unzipping):

```
watchdog990 xml --path data/raw/<batch>.zip --label <batch>
```

**Checks:** zero (or near-zero) unparseable files; per-field NA
rates printed by the command — a jump on any field means the IRS
renamed an element; fix `ALTERNATES` in `ingest/efile_xml.py`, add
the old name as a fallback, test, note it. If a batch aborts with
`NotImplementedError: That compression method is not supported` (or
reports ~100% unparseable), it is Deflate64 compression — seen on
2025_TEOS_XML_11B, 05A and 05B: extract with `unzip` and parse the
folder.

Always reconcile each batch's parsed count against
`index_<year>.csv` before moving on — a batch can be a perfectly
valid, fully readable zip and still be missing half its returns
(2025_TEOS_XML_05A, 2026-08-28: 81,770 of 163,540). "Opens cleanly"
is not "is complete".

When a batch comes up short, **check for a `<batch>B` sibling on the
server before assuming the download failed.** 05A was exactly half,
and the missing half was `2025_TEOS_XML_05B.zip` — a real file the
index never names, since it labels those returns `05A` too. Confirm
which it is from `content-length`: if the server's length equals the
file on disk, the download is complete and the batch is split; if it
is larger, the retrieval genuinely truncated.

Concatenate the parsed CSVs into one governance file **reading `ein`
as a string** (`dtype={"ein": "string"}` — otherwise leading zeros
are stripped and coverage silently drops), then re-run the report
stage with `--governance`.

## 4b. Rebuild the diversion review workpaper

```
watchdog990 diversion --governance outputs/governance_*.csv --label <years>
```

Writes `outputs/diversion_review_<years>.csv` — one row per
(EIN, tax period) that checked Part VI line 5 on a Form 990 and filed
a Schedule O explanation, superseded on (EIN, tax period) with the
last file winning. Paths are sorted before stacking, so the output
does not depend on your shell's glob order. This is the file the
Phase 5 review protocol reads (`docs/ai-assisted-review.md`); do not
hand-assemble it. The rule and the argument for each leg of it live
in `src/watchdog990/diversion.py`.

**Checks:** the command prints admissions -> rows -> unique orgs, and
all three reconcile: rows = admissions minus superseded minus any
admission lacking an explanation (it warns when that last number is
non-zero — a checked box with no Schedule O text is a finding about
the filing, not a parser bug, but confirm which before publishing a
count). Compare the org count against the last round's; the cohort
grows roughly with parsed Form 990s.

Do **not** build this file by deduplicating the whole governance base
and then filtering to admissions. A same-period 990-EZ/PF row carries
`material_diversion` NA — Part VI line 5 is not on that form — and
supersedes a real admission out of the queue; that cost 12
organizations on the 2024+2025 base. See the 2026-08-28 entry in
`methodology.md`.

## 5. Close the loop

- `pytest -q` (or `python tests/test_*.py`) — everything green.
- Update `data-sources.md` (files, dates, counts) and, if any
  threshold moved, `methodology.md` with a dated, evidenced entry.
- Commit in increments with the evidence in the messages. The audit
  trail is the product as much as the screen is.

## Cadence reference

The IRS posts: SOI extracts annually (usually mid-year for the prior
processing year); BMF continuously (grab it whenever refreshing);
XML batches monthly during the year, with the per-year index growing
as batches land. A twice-a-year XML top-up plus one annual full
cycle keeps the screen honest.

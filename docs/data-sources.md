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

## Phase 2: IRS Form 990 e-file XML
The IRS also releases full e-filed returns as XML. That is where the
governance signals live (material diversion of assets checkbox,
loans to insiders, independent-board counts, Schedule L related-party
transactions). Parsing is schema-version pain; evaluate the `irsx`
library before hand-rolling. Not needed for the MVP.

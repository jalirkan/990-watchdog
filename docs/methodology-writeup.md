# Screening the Nonprofit Sector in Public: Methodology

*990 Watchdog — methodology write-up, v1.0, July 2026.*
*Published before any findings, on purpose.*

## What this is, and what it is not

990 Watchdog is an open-source screening analytic over the financial
reports that United States tax-exempt organizations file with the
IRS. It reads six years of Form 990 data — 1,930,856 filings from
404,005 organizations — computes a small set of audit-style ratios
and multi-year trends, and raises flags on patterns that warrant a
closer look.

Every output leads with the same disclaimer, and it is the honest
center of the method: **a flag is not a finding.** Filings contain
transcription errors; thresholds are judgment calls; and a legitimate
explanation exists for every rule in this document — startup years,
planned endowment spend-down, hospital systems, subsidized-housing
accounting, all-volunteer boards. The analytic raises the question;
only a manual review of the actual filing can answer it. Nothing
about a specific organization should be published from this tool
without that review. The same standard as audit fieldwork.

## Data

Three public IRS sources, all free, all documented in the
repository's `data-sources.md` with download URLs and dates:

1. **SOI Annual Extracts of Form 990 data**, processing years
   2019–2024. Every extract year was verified against the field
   layout documentation the IRS publishes alongside it: all six years
   share a 246-element layout, every mapped field was confirmed
   name-by-name, and physical row counts reconcile to the layout
   docs' stated counts exactly (e.g. PY2022's four surplus rows are
   precisely the four rows lacking a tax period). One material
   limitation was confirmed in every year: the extracts carry Part IX
   functional expenses as totals only — no program / management /
   fundraising breakdown — so the popular "program expense ratio"
   cannot be computed from this source and is never faked.
2. **Exempt Organizations Business Master File**, the IRS registry of
   organizations, used to attach names, NTEE sector codes, and 501(c)
   subsections.
3. **Form 990 e-file XML** (the complete filed returns), used for
   governance signals the extracts cannot see. The parser was
   validated on 360,115 real returns across three IRS batches: zero
   unparseable files and 0.00% missing-field rates on every element
   name across schema versions 2021v4.0–2023v4.0.

## Pipeline

All IRS column-name quirks are quarantined in one schema module; the
rest of the code speaks canonical names. Filings are assembled into a
panel of one row per organization per fiscal period; where the same
return appears in multiple processing years (amendments,
reprocessing), the latest processing year wins — a documented,
deliberate rule. Screening evaluates each organization's **latest
filing only**: point-in-time rules on current numbers, trend rules on
the trailing streaks. Missing data follows one discipline throughout:
a blank on a filed return can count as a reported zero where a rule
targets the reported value, but data the source never carried is "no
data," and no rule ever fires on it.

## The rules, their thresholds, and their measured rates

All thresholds live in a plain-text config file, in the open. Every
change is a dated methodology entry with its evidence. Rates below
are from the six-year panel (404,005 organizations); 22.4% carry at
least one flag.

| Flag | Rule (defaults) | Severity | Rate |
|---|---|---|---:|
| THIN_RUNWAY | net assets cover < 1 month of spending | low | 6.4% |
| NEGATIVE_NET_ASSETS | liabilities exceed assets | high | 5.7% |
| OFFICER_COMP_HEAVY | officer comp > 30% of expenses | medium | 5.6% |
| DETERIORATING_RUNWAY | runway fell 2+ straight years, ending < 3 months | medium | 5.6% |
| PERSISTENT_DEFICITS | deficits in 4+ consecutive filings | medium | 4.8% |
| SECTOR_OUTLIER_OFFICER_COMP | officer comp above own sector's 95th percentile | low | 3.3% |
| CHRONIC_DEFICITS | a deficit in *every* observed year (5+ years) | high | 2.7% |
| MATERIAL_DIVERSION | org reported discovering diversion of assets | high | 151 orgs |

Two threshold decisions were made *from the data*, and the reasoning
is part of the method. The deteriorating-runway cap was tightened
from 6 to 3 months after measurement showed that a two-year runway
decline alone described 32% of multi-year organizations — COVID-era
reserves normalizing — so the rule's information lived in the "ends
thin" leg. The persistent-deficit streak was raised from 3 to 4
consecutive years once six years of history made 4-year streaks
observable: a 3-year streak can sit entirely inside 2020–2023 and
functions as an era detector rather than an organization signal.

A deliberate design split: registry rules are row-local (an
organization's own numbers decide), while the sector-relative rule
requires the whole population to define "unusual," runs only where
sector data exists, and records the sector cutoff each hit cleared.

## Context before comparison

Flag rates differ across the sector for structural reasons, and the
reports print that context rather than pretending a single scale
exists. By NTEE sector, flag rates run from 45.2% (housing and
shelter — mortgaged real estate plus depreciation produces negative
or thin net assets by design) down to 13.3% (public safety). By
501(c) subsection, labor unions (24.9%) and business leagues (23.0%)
sit above charities (22.2%), largely because their officers *are*
their staff; veterans posts run 10.8%. Reviews of charities should
read from the charity row. Sector-relative thresholds beyond the one
outlier rule remain future work and will be proposed from these
tables' evidence, not assumed.

## Governance signals

From the full e-filed returns, four signals the extracts cannot see:
the Part VI line 5 admission that the organization discovered a
material diversion of assets (checked on 0.09% of Form 990s parsed),
outstanding loans to or from interested persons (2.65%), board
independence (12.5% of organizations report boards with a minority of
independent voting members), and whether Schedule L interested-person
transactions were filed (7.7%).

Only the diversion admission is a flag — it is a literal statement on
a signed return, and it is rare enough that it cannot flood a review
queue. It fires even when an organization's ratios are clean, and
that mattered: of 151 panel organizations with the admission, 111
carried no financial flag at all. The counterweight is stated
wherever the flag appears: an organization that self-reports a
diversion and explains its remediation is exhibiting transparency,
and the flag means "read their explanation," never more. Insider
loans and board independence remain context columns — a 2.65%
base-rate boolean and a continuous share make better sort keys than
alarms.

## Validation

Three rounds, all against sources independent of the pipeline:
seven flagged filings compared field-by-field with ProPublica's
Nonprofit Explorer records (28 of 28 values exact); two trend-flagged
organizations' full multi-year series verified the same way; and one
diversion admission traced to the organization's actual filing.
Forty-one automated tests pin the schema to real IRS column names,
the missing-data discipline, the streak logic, and the report
outputs — several of them regression tests for bugs that only real
data exposed.

## Limitations

Everything here is self-reported filing data, with IRS processing
adjustments and transcription noise on paper returns. The extracts
omit the functional expense breakdown entirely. "Consecutive years"
means consecutive filings; fiscal-year changes produce short years we
count as steps. Governance coverage currently reaches 41.8% of
flagged organizations (three of twelve monthly XML batches for 2024).
The trailing window includes the pandemic years, which lifts every
deficit-related base rate; thresholds were tuned with that in view.
And the deepest limitation is the design premise itself: ratios and
checkboxes can only ever say *where to look*.

## Reproducibility

The entire method is inspectable: code, thresholds, tests, tuning
log, and this document live in one repository, and every screening
run is reproducible from public IRS files with documented URLs. The
tool runs on a modest laptop; large steps are resumable. Fork it,
audit it line by line, disagree with a threshold — the transparency
is the product.

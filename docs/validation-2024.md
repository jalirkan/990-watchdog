# Flag validation workpaper — PY2024 first run (2026-07-29)

Five flagged organizations (seven filings) pulled independently from
the ProPublica Nonprofit Explorer API v2 and compared field-by-field
against the extract rows that fired the flags. Purpose: confirm flags
reflect the actual filings, not schema-mapping bugs.

Comparison fields: totrevenue, totfuncexpns, compnsatncurrofcr,
totnetassetend (canonical: total_revenue, total_expenses,
officer_comp, net_assets_eoy).

| EIN | Org | Tax period | Flag(s) fired | Extract vs ProPublica |
|---|---|---|---|---|
| 010551364 | Tech Coast Angels Inc (CA) | 202312 | OFFICER_COMP_HEAVY (0.351) | exact match, all 4 fields |
| 010566012 | Anahuak Youth Soccer Assn (CA) | 202312 | THIN_RUNWAY (0.25 mo) | exact match, all 4 fields |
| 010607626 | Providence Westside Housing DFC (NY) | 202312 | NEGATIVE_NET_ASSETS (−1,302,391) | exact match, all 4 fields |
| 274171187 | San Diego Football Academy (CA) | 202112 | NEG_NET_ASSETS, OFFICER_COMP_HEAVY (0.466) | exact match, all 4 fields |
| 274171187 | 〃 | 202212 | OFFICER_COMP_HEAVY (0.464), THIN_RUNWAY (0.23 mo) | exact match, all 4 fields |
| 465215702 | Transforming the Bay With Christ (CA) | 202306 | OFFICER_COMP_HEAVY (0.644), THIN_RUNWAY (0.24 mo) | exact match, all 4 fields |
| 465215702 | 〃 | 202406 | NEG_NET_ASSETS (−281,108), OFFICER_COMP_HEAVY (0.574) | exact match, all 4 fields |

Verdict: 7/7 filings, 28/28 field comparisons exact. Flags reflect
filings; no mapping artifacts observed. BMF name join verified for
both states (CA and NY orgs carried correct names in the report).

Fieldwork notes (context, not findings — see methodology posture):

- Multi-filing EINs: the PY2024 file contains late-filed prior-year
  returns (e.g. SDFA's FY2021+FY2022 both processed in 2024), and the
  report's per-org rollup unions flags across filings. A "3-flag org"
  can be 3 flags across 2 fiscal years. Phase-2 candidate: keep
  latest tax_period per EIN, or report per (ein, tax_period).
- Comp-line migration: two orgs show compensation moving between
  Part IX line 5 (officers) and line 7 (other salaries) across years
  (Tech Coast Angels 2022→2023; Transforming the Bay 2022→2023).
  OFFICER_COMP_HEAVY is sensitive to that classification choice —
  a legitimate explanation to check during any manual review.
- Providence Westside: classic subsidized-housing pattern (large
  secured mortgage, depreciation-driven deficits deepening 5 straight
  years). Flag is accurate; explanation likely structural.

Method note: lookups performed via the same ProPublica v2 endpoints
the CLI `org` command uses (sandbox network restrictions prevented
running the CLI itself this session); one request at a time, matching
the client's rate courtesy.

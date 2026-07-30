# Methodology

## Posture
This project screens; it does not accuse. Every output leads with the
disclaimer in `report.py` and it is never to be removed. A flag means
"this self-reported filing pattern warrants a closer look." Filings
contain errors, thresholds are judgment calls, and legitimate
explanations exist for every rule. Before anything about a specific
organization is published anywhere, it gets a manual review of the
actual filing -- the same standard as audit fieldwork: the analytic
raises the question, the workpaper answers it.

## Metrics (src/watchdog990/metrics.py)
- program_expense_ratio = program expenses / total expenses
- officer_comp_ratio = officer compensation / total expenses
- fundraising_efficiency = contributions / fundraising expenses
- surplus_margin = (revenue - expenses) / revenue
- months_net_assets = net assets / (expenses / 12)

Missing or zero denominators produce NA, and NA never fires a flag.

## Trend metrics (src/watchdog990/trends.py, phase 2)
Computed on a multi-processing-year panel (src/watchdog990/panel.py),
one row per (EIN, tax period); the same return appearing in several
processing-year files is deduplicated with the latest processing year
winning (amended data supersedes).

- consec_deficit_years: consecutive filings, ending at this one, with
  surplus_margin < 0. An NA margin breaks the streak — absence of
  evidence is not evidence of a deficit.
- runway_drop_streak / runway_change: consecutive filings with falling
  months_net_assets, and the latest step's change.

"Consecutive" means consecutive *filings* ordered by tax period. An
org that changes fiscal year end files a short year; we count it as a
step rather than calendar-normalizing, and accept the small noise.

Trend screening evaluates each org's LATEST filing only (point rules
on current numbers, trend rules on trailing streaks). This avoids the
phase-1 rollup confusion where flags from different fiscal years
unioned into one org line.

A note on the "overhead ratio": low overhead is popularly read as
virtue, but starving admin/infrastructure often harms effectiveness.
This project flags *extreme* patterns in both directions and says so,
rather than ranking charities by overhead.

## Flags (src/watchdog990/flags.py)
Thresholds live in `config/settings.yaml`, in the open, on purpose.
Changing them is a methodology change and should be committed with a
rationale in the message.

Missing-data semantics (clarified 2026-07-29): a field that is blank
on a filed return counts as a reported zero where a rule targets the
reported value (e.g. ZERO_FUNDRAISING_COST). A field the dataset
never carried at all is "no data" — rules must never fire on it.
This distinction is implemented in flags.py and tested.

Trend rules (added 2026-07-29, phase 2):
- PERSISTENT_DEFICITS (medium): expenses exceeded revenue in
  persistent_deficit_years_min (default 4) consecutive filings.
  Innocent explanations include planned endowment spend-down and
  multi-year capital projects — which is why this is medium, not
  high.

  Tuning log. 2026-07-29 (3-year panel): kept at 3 with an era note —
  the elevated 7.1% base rate read as 2020-2023 signal, with a
  revisit promised once longer streaks became observable.
  2026-07-30 (6-year panel, PY2019-2024, 404,005 orgs, median 6
  filings/org): raised 3 -> 4. At 3 the flag hit 8.0% of all orgs
  (largest in the report) and a 3-streak can sit entirely inside
  2020-2023, making the rule substantially an era detector. At 4 a
  streak must extend beyond that stretch: 4.77% of all orgs (6.35%
  of orgs with 4+ filings), in line with the other flags. Cost,
  accepted: orgs with under 4 observed filings cannot fire this rule
  (75% of orgs have 4+); point-in-time rules cover short histories.
  Observed but not acted on: 2.2% of orgs ran deficits in every
  observable year — candidate for a future "chronic" severity tier.
- DETERIORATING_RUNWAY (medium): months_net_assets fell in
  runway_drop_streak_min (default 2) consecutive filings AND ended
  below runway_deteriorating_latest_max (default 3 months). Both legs
  required: a fall from 60 to 40 months is not distress.

  Tuning log 2026-07-29 (PY2022-2024 panel, 370,245 orgs): the cap
  was tightened 6.0 -> 3.0 months. Evidence: 32% of orgs with 3+
  filings showed 2+ consecutive runway drops (COVID-era reserves
  normalizing), so the streak leg alone carries little signal in this
  window and the cap does the work; at 6.0 the flag hit 7.8% of all
  orgs (largest in the report), at 3.0 it hits 4.9% — in line with
  the other flags, and "under a quarter-year of runway and still
  falling" is the crisper screening statement. A 3-drop streak
  (0.36%) is not viable until more processing years widen the window.
- Trend rules only fire when the trend columns exist (multi-year
  runs); single-year runs are unaffected.

NTEE sectors: the trend summary reports flag rates per NTEE major
group (from the EO BMF). Reporting only, for now — sector-aware
thresholds are a methodology change that will be proposed from that
table's evidence, not assumed.

501(c) subsection (added 2026-07-29): the trend summary also reports
flag rates per subsection. Unions, business leagues, and social clubs
are structurally unlike charities (officer-heavy comp and thin
reserves by design), so charity-focused review should read from the
(c)(3) row. Reporting only, same rule as sectors.

Added 2026-07-30:

- CHRONIC_DEFICITS (high): expenses exceeded revenue in EVERY
  observed filing, with at least chronic_deficit_min_years (default
  5) of history. Tier above PERSISTENT_DEFICITS (a chronic org also
  carries the persistent flag; the severity difference is the point).
  First measurement on the six-year panel: 2.67% of orgs. High
  severity because never once breaking even across 5+ observable
  years is qualitatively different from a streak — but planned
  endowment spend-down remains an innocent explanation, so the
  disclaimer still governs.

- SECTOR_OUTLIER_OFFICER_COMP (low): officer comp share above the
  sector_outlier_pctl (default 0.95) quantile of the org's own NTEE
  major group, computed only in sectors with at least
  sector_outlier_min_group (default 300) computable orgs. This is
  the first sector-AWARE rule: relative, not absolute — a hospital
  is compared to hospitals. It runs only in the trend pipeline's
  report stage (the only place the population carries sectors), and
  each hit records the sector cutoff it cleared. Severity low while
  the rule is young; an upgrade proposal should cite validation
  against actual filings. First measurement: 13,458 hits (~3.3% of
  all orgs; ~5% of eligible-by-construction).

## Governance signals (phase 3, parser landed 2026-07-30)
`watchdog990 xml` parses material diversion, insider loans, board
independence, and Schedule L presence from e-filed returns into a
governance CSV; `trend --stage report --governance <csv>` joins them
onto the screen.

MATERIAL_DIVERSION (high) — adopted 2026-07-30, after the parser
validated at 0.00% NA on a real TEOS batch. A checked Part VI line 5
is a self-reported discovery of material diversion of assets on a
signed return; base rate ~0.06% of Form 990s, so the queue cannot
flood. It fires for any panel org with the admission, including orgs
whose ratios are clean. Counterweight, stated everywhere the flag
appears: an org that self-reports and explains remediation in
Schedule O is exhibiting transparency — the flag means "read
Schedule O," never more.

Insider loans and board independence remain context columns, not
flags: a 2% base-rate boolean and a continuous share are better
review-queue sort keys than binary alarms. Any promotion is its own
dated proposal.

## Expense-breakdown rules go live via XML (2026-07-30)

The e-filed Part IX carries the functional expense breakdown the
extracts never did. The trend report now enriches each org whose
LATEST panel filing has a parsed XML twin — strictly period-matched
on (EIN, tax period) — and evaluates the two long-dormant rules on
that subset (currently 167,831 orgs, 41.5% of the panel):

- LOW_PROGRAM_RATIO (< 0.50 of expenses to programs): measured at
  11.4% of covered orgs / 4.7% of the panel. Kept at 0.50: the left
  tail is fat rather than clustered at the line (0.33 would still
  catch 8.8%), no sector dominates the hits, and 0.50 is the
  established public floor. Median program ratio in the covered
  population is 0.855.
- ZERO_FUNDRAISING_COST: the scaffold rule ($1M+ contributions, zero
  reported fundraising expense) failed contact with data — 37.9% of
  eligible orgs fire, because line 1h contributions INCLUDE
  government grants and grant-funded orgs genuinely raise nothing.
  Interim: floor raised $1M -> $5M (2.4% of covered orgs). Planned rebase, next parse cycle: private contributions
  (line 1h minus government grants minus related-org support, all
  now parsed from Part VIII) at a $1M floor — the pattern the rule
  always meant. The rebase will be measured before it ships.

  Rebase shipped 2026-07-30, measured first on the full 2024 XML
  base: private-basis $1M fires on 3.3% of the with-breakdown
  population (4,322 orgs on the panel at full coverage, 1.3% of
  period-matched). The rule now prefers the private basis wherever
  the breakdown exists and falls back to total-basis $5M elsewhere.
  Honest caveat, kept in the rule text: about one in four orgs with
  $1M+ private support reports zero fundraising cost — bequests and
  single major gifts are common — so severity remains medium and
  every hit is a question, not an answer.

## Known limitations
- Extract files carry selected fields; some metrics are NA until the
  XML phase (see docs/data-sources.md).
- Single-year snapshots; trend analysis (a stronger signal) is a
  roadmap item.
- Sector matters: hospitals, universities, foundations, and
  pass-through grantmakers have structurally different ratios.
  NTEE-code peer-grouping is a roadmap item before any public
  comparisons.

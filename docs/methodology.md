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

### The diversion workpaper: rule written down (2026-08-28)

`outputs/diversion_review_2024-2025.csv` is what the Phase 5 review
protocol reads, and until today no command built it. The runbook said
"concatenate the governance CSVs"; `data-sources.md` records the
result — **432 unique organizations, all with Schedule O
explanations** — without the rule that produced it. A headline figure
that cannot be regenerated from the repo is a reproducibility hole in
a project whose whole claim is reproducibility, so the rule is now
code: `watchdog990 diversion`, with each leg argued in
`src/watchdog990/diversion.py` and pinned in `tests/test_diversion.py`.

The rule: Form 990 records only (`is_form_990` — Part VI line 5 exists
on no other form), `material_diversion` True, a non-empty Schedule O
explanation, then supersede on (ein, tax period) with the last
occurrence winning, files stacked in sorted order. That is panel.py's
supersede, applied to the **admissions** rather than to the whole
governance base.

| Base | Admissions | Rows | Unique orgs | Recorded |
|---|---:|---:|---:|---|
| 2024, twelve batches | 330 | 327 | 309 | 327 — reproduces |
| + the seven 2025 batches 432 was measured on | 508 | 503 | **440** | 432 — does not |
| + all sixteen 2025 files (today's base) | 675 | 666 | 560 | — |

**The 2024 figure reproduces exactly, and independently.** 330
admissions minus 3 superseded is the same arithmetic `data-sources.md`
records from that round — "728,719 index rows minus 3 duplicate
diversion rows superseded during the Schedule O patch". Two different
statements, one rule, same three rows. That is good evidence this is
the rule that built the 2024 workpaper.

**The combined figure does not reproduce, and growth is not the
reason.** Restricted to exactly the batches on hand when 432 was
recorded — the same seven 2025 batches, on a base that rebuilds to
1,067,727 records exactly, matching that entry — the rule yields
**440**, not 432. The difference is 8 organizations and it is not a
coverage artifact. Alternatives measured on that same base, none of
them 432 either:

- **440** — the rule above.
- **438** — supersede among all Form 990 records *before* filtering to
  admissions, i.e. a later amended 990 that unchecks the box retracts
  the admission. Defensible; costs 2 organizations. Rejected because
  the 2024 workpaper reproduces at 327 only without it (it gives 325),
  and because an admission is a statement that was filed — the review
  queue should still see it.
- **426** — supersede across the whole governance base, admissions and
  all, which is what "concatenate the CSVs and filter" most naturally
  does. This one is not merely different, it is wrong: 12 of the 14
  organizations it loses are evicted by a same-period 990-EZ/PF row
  whose `material_diversion` is NA *because Part VI line 5 is not on
  that form*. `test_a_non_990_return_never_supersedes_an_admission`
  is the regression that would have caught it.
- 423 (keep-first), 437 (keying on ein + tax period + schema version),
  415 (restricted to panel organizations), 305 (each organization's
  latest filing only).

**Two filters do land on 432 and both are fabrications**, recorded
here so nobody re-derives them and believes them: dropping the 2024
01A batch, and requiring a Schedule O explanation of at least 61
characters. Neither has any basis in the method. They are what tuning
to a number looks like.

Standing position: **432 came from an unrecorded rule.** It stays in
`data-sources.md` as the historical record of what was measured that
day; it is not restated, and the new counts are not bent toward it.
440 is what the written-down rule yields on that day's inputs, 560 on
today's. What changed is that the next refresh regenerates the file
with a command instead of reconstructing the rule from memory.

Unresolved and worth saying plainly: the 8-organization gap has no
explanation. The workpaper CSV from that day is not in the repo
(`outputs/` is gitignored), so the surviving evidence is the sentence
in `data-sources.md` and nothing else.

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

  Tuning log 2026-08-28 (2025 completion round — all 2024 + all
  sixteen 2025 files, including the 05B half found after the first
  rebuild; governance base 1,420,080 records). Measured, not retuned:
  **ZERO_FUNDRAISING_COST fires on 9,683 orgs — 3.59% of the
  with-breakdown population and 3.06% of period-matched (316,893)**.
  The figure is stable across three independently built bases this
  day (9,662 pre-round, 9,686 at fifteen files, 9,683 at sixteen),
  which is itself evidence the gap is not a coverage artifact. Against the 2026-07-30 rebase entry above (4,322 orgs,
  3.3% of with-breakdown, 1.3% of period-matched) that is **2.24x the
  recorded count**, which clears the runbook's "a flag doubling or
  halving is a finding" bar. Both figures stand as measured; neither
  is restated to match the other.

  The threshold is not what moved. The fire rate on the population
  the rule actually tests barely shifted (3.3% -> 3.59%), and the
  neighbouring rule reproduces: LOW_PROGRAM_RATIO measures 38,176
  here and 38,115 on the pre-round base, against the 38,117 that
  ground-truth-lab's `docs/MEMO-001-stewardship-arm.md` recorded from
  the shipped artifact at this same repo SHA (ce9902f) — while that
  same memo records 4,248 for ZERO_FUNDRAISING_COST. Median program
  ratio 0.856 against the recorded 0.855. The disagreement is
  specific to this one flag, so it is not a coverage artifact
  reaching every rule.

  What moved is the population. The Part VIII contribution breakdown
  now parses on 85.2% of period-matched rows; the 2026-07-30 entry's
  own two percentages imply roughly 39% at the time. Because the rule
  prefers the private basis wherever the breakdown exists, far more
  orgs are now tested on the sensitive $1M private basis instead of
  falling back to the $5M total basis — more coverage, same rule,
  more hits. Read the 2026-07-30 count as "the rule at ~39% breakdown
  coverage" and this one as "the rule at 85% coverage"; they are not
  competing measurements of the same quantity.

  Not acted on here, flagged for the owner: `_zero_fundraising_cost`
  chooses its basis with a column-level test
  (`if "private_contributions" in df.columns`), while its docstring
  describes a per-row fallback to the total basis "where the
  breakdown is absent". Once the column exists, the 46,905
  period-matched rows with NA private contributions fire on nothing
  rather than falling back. Measured impact today: **zero** — no
  additional hit appears if the documented per-row fallback is
  applied, even though `total_contributions` is populated for all
  46,905. So this is a docstring-accuracy question, not a live
  miscount; it would only start to bite if a future parse lost
  contribution data on orgs above the $5M total floor.

## Known limitations
- SOI extracts omit Part IX functional expense columns; program /
  fundraising ratios require period-matched e-file XML (see
  docs/data-sources.md). Coverage is wide but not complete.
- Sector-aware absolute thresholds (beyond the relative
  SECTOR_OUTLIER_OFFICER_COMP rule) are still open — the summary's
  sector and subsection tables are the evidence base, not yet a
  full peer-threshold set.
- A flag is never a finding. Manual review of the actual return
  remains the gate before naming any organization in public.

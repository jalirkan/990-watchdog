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
  persistent_deficit_years_min (default 3) consecutive filings. One
  deficit year is noise; three is a pattern. Innocent explanations
  include planned endowment spend-down and multi-year capital
  projects — which is why this is medium, not high.

  Base-rate note 2026-07-29 (PY2022-2024 panel): fires on 7.1% of all
  orgs / 9.5% of orgs with 3+ filings. Elevated, and deliberately
  left alone: the trailing window is 2020-2023 fiscal years, a
  genuinely hard stretch for the sector, so the elevated rate is
  era signal rather than mistuning. Revisit (e.g. 4+ consecutive)
  when more processing years make longer streaks observable.
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

## Known limitations
- Extract files carry selected fields; some metrics are NA until the
  XML phase (see docs/data-sources.md).
- Single-year snapshots; trend analysis (a stronger signal) is a
  roadmap item.
- Sector matters: hospitals, universities, foundations, and
  pass-through grantmakers have structurally different ratios.
  NTEE-code peer-grouping is a roadmap item before any public
  comparisons.

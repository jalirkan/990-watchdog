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

## Known limitations
- Extract files carry selected fields; some metrics are NA until the
  XML phase (see docs/data-sources.md).
- Single-year snapshots; trend analysis (a stronger signal) is a
  roadmap item.
- Sector matters: hospitals, universities, foundations, and
  pass-through grantmakers have structurally different ratios.
  NTEE-code peer-grouping is a roadmap item before any public
  comparisons.

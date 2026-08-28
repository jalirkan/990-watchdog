# 990 Watchdog

Public-benefit screening analytics on IRS Form 990 data: load a
year's worth of nonprofit filings, compute audit-style ratios, and
surface filing patterns that warrant a closer look — for donors,
journalists, and small nonprofit boards that can't afford an analyst.

**Posture:** this screens, it never accuses. See `docs/methodology.md`
before sharing any output.

## Quickstart

```bash
# Requires Python 3.10+ (3.12 recommended)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q                        # should pass out of the box
```

Then get data (all free, all public — links in `config/settings.yaml`):

1. Download the latest **SOI Annual Extract** Form 990 CSV into
   `data/raw/`.
2. (Optional, for org names) download one or more **EO BMF** state
   CSVs into `data/raw/`.
3. Run:

```bash
watchdog990 run --extract data/raw/<extract>.csv --bmf data/raw/<bmf>.csv --label 2023
```

With several years in `extract_files`, run the multi-year trend screen
(point flags on each org's latest filing + deficit/runway streaks;
sector table needs BMF files in `bmf_files`):

```bash
watchdog990 trend                      # all configured years
watchdog990 trend --stage panel        # resumable, for small machines:
watchdog990 trend --stage names --bmf data/raw/eo1.csv data/raw/eo2.csv
watchdog990 trend --stage report
```

Outputs land in `outputs/`: a full `flags_<label>.csv` and a readable
`summary_<label>.md`. Spot-check any org against its actual filing:

```bash
watchdog990 org --ein 142007220
```

## First-run reality check

The IRS renames fields between forms and years. If the run warns
about unmapped fields, open `src/watchdog990/schema.py` and fix the
entries marked `VERIFY` against the field layout doc that ships with
your extract year. That file is the only place mappings live.

## Layout

```
config/         settings.yaml — sources, file paths, thresholds
data/           raw / interim / processed (gitignored)
docs/           data-sources.md, methodology.md
notebooks/      scratch exploration (promote real work to src/)
outputs/        generated reports (gitignored)
src/watchdog990/
  ingest/       soi_extract.py, bmf.py, propublica.py
  schema.py     canonical fields + IRS column maps (fix names HERE)
  metrics.py    ratio layer
  flags.py      screening rules registry
  diversion.py  material-diversion review workpaper (phase 5)
  report.py     CSV + markdown outputs, disclaimer built in
tests/          synthetic-data tests, no network needed
```

## Roadmap

- **Phase 1 (done):** extract-based screening, single year.
- **Phase 2 (done):** multi-year trends (`watchdog990 trend`) and
  NTEE sector rate reporting. Sector-aware *thresholds* beyond
  `SECTOR_OUTLIER_OFFICER_COMP` remain open — the summary's sector
  table is the evidence base.
- **Phase 3 (done):** e-file XML governance signals — material
  diversion flag, insider-loan / board-independence context columns,
  Schedule L presence, period-matched expense-breakdown rules via
  `watchdog990 xml` and `trend --governance`.
- **Phase 4 (done):** methodology write-up first, findings companion
  second (`docs/methodology-writeup.md`, `docs/findings-writeup.md`).
  Annual refresh cycle: `docs/refresh-runbook.md`.
- **Phase 5 (current):** AI-assisted review of the diversion cohort —
  the model proposes, a human disposes, and only the human column can
  publish. Protocol and controls: `docs/ai-assisted-review.md`. The
  review queue itself is built by `watchdog990 diversion --governance
  outputs/governance_*.csv --label <years>`.

## License

MIT — see `LICENSE`. The methodology's screening posture travels with
any fork: a flag means "look closer," never "wrongdoing," and the
report disclaimer stays.

# What the Screen Found: Six Years of Form 990 Filings

*990 Watchdog — findings companion, v1.1, 2026-08-28.*
*Read the methodology write-up first; its disclaimer governs every
sentence here. A flag is a reason to look closer. It is never a
finding of wrongdoing, and this document names no organization it
has not manually reviewed.*

*Every figure below is measured on the 2026-08-28 run: the six-year
panel PY2019-2024 (404,005 organizations) and a governance base of
1,420,080 parsed e-filings. The v1.0 figures of 2026-07-30 are not
discarded — every one of them is preserved, with the reason it
moved, in "Reconciliation to v1.0" at the end. If you are holding a
number from v1.0, read that section before you use it.*

## The queue, in numbers

Screening 404,005 organizations' latest filings against six years of
history produces a review queue of 127,214 organizations — 31.5% —
carrying at least one flag. Most carry exactly one (84,165
organizations), which is what a healthy screening tail looks like.
Concentration is where attention should go: 31,550 organizations
carry two distinct flags, 8,160 carry three, and 3,339 carry four or
more. 30,593 organizations carry at least one high-severity flag
(negative net assets, a deficit in every observable year, or a
reported diversion of assets).

No reviewer reads 127,214 files. The queue is built to be sorted:
severity first, flag count second, governance context alongside, and
sector row kept in view throughout.

## Trend rules see what snapshots cannot

The project's founding hypothesis was that deteriorating ratios beat
snapshots. Measured: **18,075 organizations are flagged only by
trend rules** — persistent or chronic deficits, deteriorating
runway — while every single-year test comes back clean. One
flagged organization in seven is invisible to the way nonprofit
finances are usually screened, which is one year at a time.

That count is lower than v1.0's not because fewer organizations show
deteriorating trends — the trend rules run on the same panel and
fire on the same organizations — but because 2,220 of them now also
carry an expense-breakdown or diversion flag, so they are no longer
flagged *only* by trend rules. The thesis is unchanged; the
exclusive claim is narrower because the rest of the screen sees more
than it did. This is also the one v1.0 figure that does not
reconcile exactly — see the reconciliation for the residual.

The starkest cohort inside that: 10,771 organizations (2.7%) ran a
deficit in every single year we can observe, five or more years
straight. About a third of them (3,410) have already burned through
to negative net assets; the other two-thirds are on the way down but
not yet underwater — which is precisely the window in which a closer
look is most useful. Both figures are unchanged from v1.0, to the
organization: this cohort is computed entirely from the SOI panel,
which has not moved. The innocent explanation — a foundation
deliberately spending down — is real, common, and checkable in
minutes against any individual filing.

## Structure, not scandal, drives most flag rates

The largest differences in flag rates are structural. Housing and
shelter organizations flag at 49.7% — not because the sector is
troubled, but because mortgaged real estate plus depreciation
produces thin or negative net assets by accounting construction.
Public-safety organizations flag at 19.6%. Labor unions (49.7%) and
business leagues (44.2%) sit above charities (28.7%) almost entirely
because their officers are their staff, which lifts the
officer-compensation rules. Housing remains the highest-rate sector
and public safety the lowest, as in v1.0; the whole table shifted
upward together when the expense rules went live, which is one more
reason these rates are context and not a ranking. Any use of this
screen that compares an organization to the whole sector rather than
to its own row is a misuse; the reports print the rows.

## Governance signals change the queue's composition

From 717,950 parsed Form 990 returns — the 990 slice of 1,420,080
parsed e-filings across the series — 0.09% checked the box reporting
a discovered material diversion of assets; 2.38% report outstanding
loans to or from interested persons; and 13.1% of the 705,201
returns that report board composition show independent members in a
minority.

Joined to the screen, two results stand out. First, of 288 panel
organizations with a diversion admission, **180 carry no other flag
at all** — their ratios are unremarkable, and the only visible
signal is the admission itself. Financial screening alone would have
missed them entirely; this is the concrete case for parsing the full
returns, and it has held its shape as the parsed base doubled. The
108 organizations carrying both an admission and financial flags
sort, on any reasonable weighting, to the very top of the queue.
Second, flagged organizations carry insider loans at 3.32% (3,632 of
109,244 covered) against a 2.37% base rate across all 374,903
organizations with parsed Form 990 governance — both measured per
organization on its latest parsed return, so the two rates are
comparable. The financial screen and the governance signals still
point at overlapping populations, but less sharply than v1.0
reported: at wider coverage the ratio is 1.40x rather than 1.68x.
Widening the parse pulled in ordinary filers, and the base rate fell
with it.

## What one reviewed example looks like

The repository's validation workpaper documents a handful of
organizations whose filings were traced number-for-number to source.
One, a community night school, shows the mechanics: deficits in
three consecutive filings, runway falling from 7.72 months to 2.48
to −3.86, and net assets ending at −$115,005. Four flags fire on the
current run — negative net assets, deteriorating runway,
officer-comp heavy, and a sector-relative officer-comp outlier — and
every underlying number matches the organization's actual filings.
The workpaper's own run, on 2026-07-29, fired four as well but not
the same four: it recorded PERSISTENT_DEFICITS, which no longer
applies now that the streak minimum has moved from three filings to
four, and it predates the sector-relative rule that takes that place
in today's count. Same organization, same filings, two rule sets —
worth knowing before comparing any two runs of this screen by flag
count. The same workpaper notes the organization dipped negative once
before, in 2016, and recovered — the kind of context that is
invisible to a threshold and obvious to a reviewer. That is the
division of labor this tool assumes.

## The review gate

Nothing in the diversion cohort is named here or anywhere else in
this project's outputs to date. A diversion admission's meaning
lives in the organization's own Schedule O explanation — discovered
theft, remediation completed, insurance recovered, board acted — and
the reading of those explanations is Phase 5's subject, under the
protocol in `docs/ai-assisted-review.md`. Until a filing's
explanation has been read and a human has disposed of it, the
organization's name does not leave the workpaper. That gate is the
methodology's core promise, and it binds the authors of this
document first.

## What would extend these findings

Both of v1.0's extensions have since shipped, and they are what moved
the numbers above. Coverage: the nine outstanding 2024 XML batches
and all sixteen 2025 batches are parsed, and governance context now
reaches 86.8% of flagged organizations against 41.8% in v1.0. (That
86.8% is 109,244 of 125,833 as the report prints it; the printed
denominator is the flag set *before* the sector-relative rule is
added, so measured against the full queue of 127,214 the figure is
85.9%. Both are given here because the report prints the first.)
Depth: the functional expense breakdown — the one number the public
most wants and the extracts least contain — is parsed from Part IX,
and the two rules it feeds account for the queue's growth.

What is still open: sector-aware absolute thresholds, for which the
summary's sector and subsection tables remain the evidence base and
not yet a decision; and the Schedule O reading of the diversion
cohort, which is the gate above and the only route from 288 checked
boxes to anything anyone should call a finding.

## Reconciliation to v1.0 (2026-08-28)

v1.0 was published 2026-07-30 (commit `5aeb24b`, where its text
stands unedited). Its figures were correct when measured and are
preserved here rather than overwritten, in the same spirit as the
tuning log in `methodology.md`. They should not be quoted as current.

| Figure | v1.0, 2026-07-30 | v1.1, 2026-08-28 |
|---|---:|---:|
| Organizations screened | 404,005 | 404,005 |
| Review queue | 90,640 (22.4%) | 127,214 (31.5%) |
| Carrying exactly one flag | 54,681 | 84,165 |
| Two flags | 27,973 | 31,550 |
| Three flags | 5,235 | 8,160 |
| Four or more | 2,751 | 3,339 |
| At least one high-severity flag | 30,455 | 30,593 |
| Flagged only by trend rules | 20,390 | 18,075 |
| Chronic-deficit cohort | 10,771 (2.7%) | 10,771 (2.7%) |
| — of which negative net assets | 3,410 | 3,410 |
| Housing & shelter flag rate | 45.2% | 49.7% |
| Public safety flag rate | 13.3% | 19.6% |
| Labor unions, 501(c)(5) | 24.9% | 49.7% |
| Business leagues, 501(c)(6) | 23.0% | 44.2% |
| Charities, 501(c)(3) | 22.2% | 28.7% |
| Parsed e-filed returns | 360,115 | 717,950 Form 990s of 1,420,080 |
| Material-diversion base rate | 0.09% | 0.09% |
| Insider-loan base rate | 2.65% | 2.38% |
| Minority-independent boards | 12.5% | 13.1% |
| Panel orgs with a diversion admission | 151 | 288 |
| — carrying no other flag | 111 | 180 |
| — carrying financial flags too | 40 | 108 |
| Insider loans among flagged orgs | 4.45% of 37,209 | 3.32% of 109,244 |
| Governance coverage of flagged orgs | 41.8% | 86.8% |

**Why the queue grew.** The screening logic did not change; the
input coverage did. v1.0 was written before the expense-breakdown
rules went live against period-matched e-file XML later the same day
(`72a6408`), so its queue was built from the SOI panel rules plus
MATERIAL_DIVERSION and nothing else. Today's queue also contains
LOW_PROGRAM_RATIO (38,170 organizations) and ZERO_FUNDRAISING_COST
(9,683), and 36,465 organizations are in the queue on those two
rules alone. The remaining 109 of the 36,574 difference is the
diversion cohort: 220 organizations now carry an admission and no
financial flag, against 111 in v1.0.

**The arithmetic reconciles.** Recomputing today's outputs with the
two expense rules removed gives a queue of 90,529 — 22.4% of the
panel, the rate v1.0 reported — and adding the 111 organizations
whose only flag was a diversion admission gives exactly v1.0's
90,640. The concentration buckets close on the same account
(54,594 / 27,964 / 5,220 / 2,751 today without the expense rules),
consistent with the 111 landing in the one-flag bucket and 39 of the
40 already-flagged admissions each moving up one rung. That last
split is an inference, not a measurement: the admissions cohort has
grown from 151 to 288 and its 2026-07-30 composition can no longer
be recovered from `outputs/`.

**What the thresholds did not do.** The rules that moved were not
retuned. LOW_PROGRAM_RATIO fires on 12.0% of the 316,893
period-matched organizations it can now test, against 11.4% of the
167,831 it could test on 2026-07-30 — the fire rate barely moved and
the testable population nearly doubled. Read v1.0's queue as "the
screen at ~41% expense-breakdown coverage" and this one as "the
screen at 85% coverage"; they are not competing measurements of the
same quantity.

**Two figures that barely moved, and why that is not luck.** The
chronic-deficit cohort (10,771 / 3,410) is computed from the SOI
panel alone, which has not changed, so it reproduces to the
organization. High-severity is a near-tie at +0.5% for a different
reason: its financial half — organizations with negative net assets
or chronic deficits — measures 30,319 on both runs, and the whole of
the +138 is the diversion cohort growing from 151 admissions to 288.

**Three figures that moved the other way.** The insider-loan base
rate fell (2.65% to 2.38%), the insider-loan rate among flagged
organizations fell further (4.45% to 3.32%), and the trend-only
count fell (20,390 to 18,075). The first two are one effect seen
from both sides: at 41.8% coverage the parsed base was skewed toward
organizations the screen had already flagged, and widening it toward
the whole filing population lowered both rates. The overlap between
the financial screen and the governance signals is real in both runs
and weaker in this one.

**One figure that does not reproduce.** v1.0's 20,390 trend-only
organizations cannot be recovered from current outputs. Removing the
expense rules gives 20,295 on the same rule set, and adding diversion
flags can only lower that further, so 20,390 sits about 95
organizations (0.5%) above anything today's outputs can produce.
Every other v1.0 queue figure reconciles exactly, so this is recorded
as an unexplained residual rather than dismissed. It does not change
the finding it supports.

**Two claims carried forward from v1.0 that this run cannot check.**
The night-school example's "$150,000 note appearing on the balance
sheet" and the description of the organization as seventy years old
are not verifiable from anything in `outputs/` or from
`docs/validation-2024.md`: the panel carries no balance-sheet detail
below net assets, and the workpaper records neither. They were
dropped from the narrative above rather than restated as measured.
Confirming them needs a lookup against the filing itself.

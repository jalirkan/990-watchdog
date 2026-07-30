# What the Screen Found: Six Years of Form 990 Filings

*990 Watchdog — findings companion, v1.0, July 2026.*
*Read the methodology write-up first; its disclaimer governs every
sentence here. A flag is a reason to look closer. It is never a
finding of wrongdoing, and this document names no organization it
has not manually reviewed.*

## The queue, in numbers

Screening 404,005 organizations' latest filings against six years of
history produces a review queue of 90,640 organizations — 22.4% —
carrying at least one flag. Most carry exactly one (54,681
organizations), which is what a healthy screening tail looks like.
Concentration is where attention should go: 27,973 organizations
carry two distinct flags, 5,235 carry three, and 2,751 carry four or
more. 30,455 organizations carry at least one high-severity flag
(negative net assets, a deficit in every observable year, or a
reported diversion of assets).

No reviewer reads 90,640 files. The queue is built to be sorted:
severity first, flag count second, governance context alongside, and
sector row kept in view throughout.

## Trend rules see what snapshots cannot

The project's founding hypothesis was that deteriorating ratios beat
snapshots. Measured: **20,390 organizations are flagged only by
trend rules** — persistent or chronic deficits, deteriorating
runway — while every single-year test comes back clean. A fifth of
the entire queue is invisible to the way nonprofit finances are
usually screened, which is one year at a time.

The starkest cohort inside that: 10,771 organizations (2.7%) ran a
deficit in every single year we can observe, five or more years
straight. About a third of them (3,410) have already burned through
to negative net assets; the other two-thirds are on the way down but
not yet underwater — which is precisely the window in which a closer
look is most useful. The innocent explanation — a foundation
deliberately spending down — is real, common, and checkable in
minutes against any individual filing.

## Structure, not scandal, drives most flag rates

The largest differences in flag rates are structural. Housing and
shelter organizations flag at 45.2% — not because the sector is
troubled, but because mortgaged real estate plus depreciation
produces thin or negative net assets by accounting construction.
Public-safety organizations flag at 13.3%. Labor unions (24.9%) and
business leagues (23.0%) sit above charities (22.2%) almost entirely
because their officers are their staff, which lifts the
officer-compensation rules. Any use of this screen that compares an
organization to the whole sector rather than to its own row is a
misuse; the reports print the rows.

## Governance signals change the queue's composition

From 360,115 parsed e-filed returns: 0.09% of Form 990 filers
checked the box reporting a discovered material diversion of assets;
2.65% report outstanding loans to or from interested persons; 12.5%
report boards where independent members are a minority.

Joined to the screen, two results stand out. First, of 151 panel
organizations with a diversion admission, **111 carried no financial
flag at all** — their ratios are unremarkable, and the only visible
signal is the admission itself. Financial screening alone would have
missed them entirely; this is the concrete case for parsing the full
returns. The 40 organizations carrying both an admission and
financial flags sort, on any reasonable weighting, to the very top
of the queue. Second, flagged organizations carry insider loans at
4.45% against the 2.65% base rate — the financial screen and the
governance signals point at overlapping populations, measured across
37,209 covered organizations.

## What one reviewed example looks like

The repository's validation workpaper documents a handful of
organizations whose filings were traced number-for-number to source.
One, a seventy-year-old community night school, shows the mechanics:
deficits in three consecutive filings, runway falling from 7.7
months to 2.5 to below zero, a $150,000 note appearing on the
balance sheet, and net assets ending at −$115,005. Four flags fired;
every underlying number matches the organization's actual filings.
The same workpaper notes the organization dipped negative once
before, in 2016, and recovered — the kind of context that is
invisible to a threshold and obvious to a reviewer. That is the
division of labor this tool assumes.

## The review gate

Nothing in the diversion cohort is named here or anywhere else in
this project's outputs to date. A diversion admission's meaning
lives in the organization's own Schedule O explanation — discovered
theft, remediation completed, insurance recovered, board acted — and
none of those explanations have been read yet. Until a filing's
explanation has been read, the organization's name does not leave
the workpaper. That gate is the methodology's core promise, and it
binds the authors of this document first.

## What would extend these findings

Coverage: nine more monthly XML batches complete 2024 governance
coverage (currently 41.8% of flagged organizations), and the 2025
index will catch flagged organizations' newer filings. Depth: the
functional expense breakdown — the one number the public most wants
and the extracts least contain — exists in the same XML and is the
natural next parsing target. Both are mechanical extensions of a
pipeline that is now validated end to end.

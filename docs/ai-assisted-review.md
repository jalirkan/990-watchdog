# AI-Assisted Review Protocol

*Added July 2026. This document describes how generative AI is used
in the diversion-cohort review, and — more importantly — how it is
controlled. The protocol is part of the methodology and changes to
it are dated entries like any other.*

## The division of labor

**The model proposes; a human disposes.** A large language model
reads each organization's Schedule O explanation and produces, per
organization: a rubric scorecard, a *proposed* disposition, and a
one-line rationale grounded in the text it read. A human reviewer
then reads the same text with the proposal beside it and records the
actual disposition. The model's column is a reading aid with a
memory for 432 texts; the human's column is the review of record.
Nothing in this project treats a model proposal as a completed
review, and the publication gate — no organization is named publicly
until its explanation has been read and judged by a person — is
satisfied only by the human column.

## The rubric (same for model and human)

A complete explanation answers four questions: **W**hat happened and
how much; how it was **D**iscovered; what **R**emediation followed
(recovery, insurance, termination, referral); what **C**ontrols
changed. Each is scored Y / P (partial) / N, and the scorecard maps
to a proposed disposition: substantially complete → *Explained — no
further action*; partial or open → *Follow up — pull full filing*;
vague, non-responsive, or troubling on its face (insider
perpetrators, large magnitudes relative to org size, multi-year
undetected schemes, weak surrounding governance) → *Concerning —
open workpaper*; no substantive explanation filed → *Not reviewable —
insufficient text*.

## Process and honesty rules

Batches run in reading-order (highest-signal tier first). The model
reads the extracted Schedule O text, not the full return; where its
batch view truncates a long filing, it must say so and propose
*Follow up — read full text* rather than judging a fragment. Every
rationale must point at something actually in the text — a model
rationale that cannot be traced to the filing's words is treated as
an error. Proposals are written into clearly-marked columns of the
review tracker (blue, labeled "AI proposed (verify)"), visually and
structurally separate from the human disposition column.

## What is published and what is gated

The repository publishes this protocol and aggregate results only.
Per-organization model output — a named organization labeled
"concerning" by a machine — is exactly the kind of adverse
characterization the review gate exists to prevent, so it stays in
local workpapers (gitignored) until a human review either clears or
confirms it.

Batch 1 aggregate (first 100 organizations, highest-signal tier,
July 2026): 12 proposed *Explained* (typically external fraud —
phishing, check-washing — with amounts, dates, and recovery or
insurance documented), 55 *Follow up* (partial explanations, open
investigations, or filings the batch view truncated), 9 *Concerning*
(insider perpetrators with unresolved recovery, multi-year
undetected schemes, six- and seven-figure magnitudes at small
organizations, or related-party structures described in lieu of an
explanation), and 24 *Not reviewable* (the checkbox is checked but
no substantive explanation was filed — itself a pattern worth
noting, and in several cases the checkbox appears to be a preparer
error, answered with asset sales or program changes).

## Measuring the model

The tracker records both columns, so human–model agreement is
measurable per batch: overall agreement rate, and the direction of
disagreements (model too lenient vs. too strict) by disposition.
Persistent disagreement patterns feed back into this protocol as
dated amendments. Until such measurements exist across full batches,
the model's error rate is unknown and the protocol treats every
proposal accordingly.

## Limitations

The model reads what filers wrote, in the batch's extracted form —
not the full return, not attachments, not amounts elsewhere in the
filing. It can be wrong confidently; a fluent rationale is not
evidence of a correct judgment. Truncation handling reduces but does
not eliminate the risk of judging partial text. And the deepest
limitation is inherited from the project itself: explanations are
self-reported, and reading them — by human or machine — can only
ever say where to look next.

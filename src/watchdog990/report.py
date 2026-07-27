"""Turn flag hits into outputs a human can use.

Two artifacts per run:
  outputs/flags_<label>.csv    -- the full long table, analysis-ready
  outputs/summary_<label>.md   -- counts per flag + most-flagged orgs

Every rendered report leads with the screening disclaimer. That is
non-negotiable: these are patterns worth a closer look, not findings,
and the report must never read like an accusation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DISCLAIMER = (
    "> **How to read this:** rows below are *screening signals* derived "
    "from self-reported IRS filing data. A flag means the pattern "
    "warrants a closer look; it is **not** a finding of wrongdoing. "
    "Filings contain transcription errors, and legitimate explanations "
    "exist for every pattern flagged. Methodology: docs/methodology.md."
)


def write(
    hits: pd.DataFrame,
    out_dir: str | Path,
    label: str,
    names: pd.DataFrame | None = None,
) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if names is not None and not names.empty:
        hits = hits.merge(
            names[[c for c in ("ein", "name", "state") if c in names.columns]],
            on="ein",
            how="left",
        )

    csv_path = out_dir / f"flags_{label}.csv"
    hits.to_csv(csv_path, index=False)

    lines = [f"# Screening summary - {label}", "", DISCLAIMER, ""]
    if hits.empty:
        lines.append("No flags fired on this dataset with current thresholds.")
    else:
        lines.append("## Hits per flag")
        counts = hits.groupby(["flag_id", "severity"]).size().reset_index(name="orgs")
        for _, row in counts.sort_values("orgs", ascending=False).iterrows():
            lines.append(f"- `{row.flag_id}` ({row.severity}): {row.orgs:,} organizations")

        lines += ["", "## Most-flagged organizations (top 25)"]
        per_org = (
            hits.groupby("ein")
            .agg(
                n_flags=("flag_id", "nunique"),
                flags=("flag_id", lambda s: ", ".join(sorted(set(s)))),
                name=("name", "first") if "name" in hits.columns else ("flag_id", "size"),
            )
            .sort_values("n_flags", ascending=False)
            .head(25)
            .reset_index()
        )
        for _, row in per_org.iterrows():
            display = row.get("name") if isinstance(row.get("name"), str) else row.ein
            lines.append(f"- **{display}** (EIN {row.ein}) - {row.n_flags} flags: {row.flags}")

    md_path = out_dir / f"summary_{label}.md"
    md_path.write_text("\n".join(lines) + "\n")
    return csv_path, md_path

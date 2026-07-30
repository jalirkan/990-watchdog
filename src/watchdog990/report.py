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

# NTEE major groups (first letter of the NTEE code).
NTEE_MAJOR_NAMES = {
    "A": "Arts & culture", "B": "Education", "C": "Environment",
    "D": "Animals", "E": "Health care", "F": "Mental health",
    "G": "Disease-specific", "H": "Medical research",
    "I": "Crime & legal", "J": "Employment", "K": "Food & agriculture",
    "L": "Housing & shelter", "M": "Public safety & disaster",
    "N": "Recreation & sports", "O": "Youth development",
    "P": "Human services", "Q": "International",
    "R": "Civil rights & advocacy", "S": "Community improvement",
    "T": "Philanthropy & grantmaking", "U": "Science & technology",
    "V": "Social science", "W": "Public & societal benefit",
    "X": "Religion", "Y": "Mutual benefit", "Z": "Unknown",
}


def sector_rates(population: pd.DataFrame, flagged_eins: set) -> pd.DataFrame:
    """Flag rate per NTEE major group.

    population: one row per org with `ein` and `ntee_major` (NA where
    the BMF had no usable code). Reporting only — sectors have
    structurally different ratios, and this table is how we SEE that
    before proposing any sector-aware thresholds.
    """
    pop = population[["ein", "ntee_major"]].copy()
    pop["flagged"] = pop["ein"].isin(flagged_eins)
    pop["ntee_major"] = pop["ntee_major"].fillna("(no NTEE)")
    out = (
        pop.groupby("ntee_major")
        .agg(n_orgs=("ein", "size"), n_flagged=("flagged", "sum"))
        .reset_index()
    )
    out["rate"] = out["n_flagged"] / out["n_orgs"]
    out["sector"] = out["ntee_major"].map(
        lambda m: NTEE_MAJOR_NAMES.get(m, m)
    )
    return out.sort_values("rate", ascending=False).reset_index(drop=True)


def write(
    hits: pd.DataFrame,
    out_dir: str | Path,
    label: str,
    names: pd.DataFrame | None = None,
    sector_table: pd.DataFrame | None = None,
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
        # NB: the column must not be named "flags" — attribute access
        # on a pandas row (row.flags) resolves to Series.flags, the
        # pandas-internal object, silently breaking the output.
        per_org = (
            hits.groupby("ein")
            .agg(
                n_flags=("flag_id", "nunique"),
                flag_list=("flag_id", lambda s: ", ".join(sorted(set(s)))),
                name=("name", "first") if "name" in hits.columns else ("flag_id", "size"),
            )
            .sort_values("n_flags", ascending=False)
            .head(25)
            .reset_index()
        )
        for _, row in per_org.iterrows():
            display = row.get("name") if isinstance(row.get("name"), str) else row["ein"]
            lines.append(
                f"- **{display}** (EIN {row['ein']}) - "
                f"{row['n_flags']} flags: {row['flag_list']}"
            )

    if sector_table is not None and not sector_table.empty:
        lines += [
            "",
            "## Flag rate by NTEE sector",
            "",
            "Sectors have structurally different ratios (hospitals are "
            "not food banks); rate differences below are context, not "
            "rankings. This table is the evidence base for any future "
            "sector-aware thresholds.",
            "",
            "| Sector | Orgs | Flagged | Rate |",
            "|---|---:|---:|---:|",
        ]
        for _, r in sector_table.iterrows():
            lines.append(
                f"| {r['sector']} | {r['n_orgs']:,} | {r['n_flagged']:,} "
                f"| {r['rate']:.1%} |"
            )

    md_path = out_dir / f"summary_{label}.md"
    md_path.write_text("\n".join(lines) + "\n")
    return csv_path, md_path

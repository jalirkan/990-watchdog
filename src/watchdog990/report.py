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


# IRS EO BMF subsection codes -> 501(c)(n) labels (common ones; rare
# codes render as the raw code).
SUBSECTION_NAMES = {
    "01": "501(c)(1) federal instrumentality",
    "02": "501(c)(2) title-holding",
    "03": "501(c)(3) charitable/educational/religious",
    "04": "501(c)(4) social welfare",
    "05": "501(c)(5) labor/agricultural",
    "06": "501(c)(6) business league",
    "07": "501(c)(7) social club",
    "08": "501(c)(8) fraternal beneficiary",
    "09": "501(c)(9) employee beneficiary (VEBA)",
    "10": "501(c)(10) domestic fraternal",
    "12": "501(c)(12) benevolent life / mutual utility",
    "13": "501(c)(13) cemetery",
    "14": "501(c)(14) credit union",
    "15": "501(c)(15) mutual insurance",
    "19": "501(c)(19) veterans",
    "25": "501(c)(25) title-holding, multi-parent",
}


def group_rates(
    population: pd.DataFrame,
    flagged_eins: set,
    col: str,
    name_map: dict[str, str],
    na_label: str,
) -> pd.DataFrame:
    """Flag rate per group of `col`. Reporting only — group
    differences are context for future methodology proposals, never
    silent threshold changes."""
    pop = population[["ein", col]].copy()
    pop["flagged"] = pop["ein"].isin(flagged_eins)
    pop[col] = pop[col].fillna(na_label)
    out = (
        pop.groupby(col)
        .agg(n_orgs=("ein", "size"), n_flagged=("flagged", "sum"))
        .reset_index()
    )
    out["rate"] = out["n_flagged"] / out["n_orgs"]
    out["group"] = out[col].map(lambda m: name_map.get(m, m))
    return out.sort_values("rate", ascending=False).reset_index(drop=True)


def sector_rates(population: pd.DataFrame, flagged_eins: set) -> pd.DataFrame:
    """Flag rate per NTEE major group (see group_rates)."""
    out = group_rates(
        population, flagged_eins, "ntee_major", NTEE_MAJOR_NAMES, "(no NTEE)"
    )
    # backwards-compatible column name used by the summary/tests
    out["sector"] = out["group"]
    return out


def subsection_rates(population: pd.DataFrame, flagged_eins: set) -> pd.DataFrame:
    """Flag rate per 501(c) subsection. The review queue reads very
    differently for charities vs unions vs business leagues; this
    table keeps that visible."""
    pop = population[["ein", "subsection"]].copy()
    # Accept "03", "3", 3, and float-contaminated "3.0" (a NaN-bearing
    # code column read back from CSV without dtype comes in as float).
    pop["subsection"] = (
        pop["subsection"]
        .astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(2)
    )
    return group_rates(
        pop, flagged_eins, "subsection", SUBSECTION_NAMES, "(no subsection)"
    )


def write(
    hits: pd.DataFrame,
    out_dir: str | Path,
    label: str,
    names: pd.DataFrame | None = None,
    sector_table: pd.DataFrame | None = None,
    subsection_table: pd.DataFrame | None = None,
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

    if subsection_table is not None and not subsection_table.empty:
        lines += [
            "",
            "## Flag rate by 501(c) subsection",
            "",
            "Unions, business leagues, and social clubs are built "
            "differently from charities (officers often ARE the staff; "
            "reserves run thin by design). Read charity findings from "
            "the (c)(3) row, not the blended totals.",
            "",
            "| Subsection | Orgs | Flagged | Rate |",
            "|---|---:|---:|---:|",
        ]
        for _, r in subsection_table.iterrows():
            lines.append(
                f"| {r['group']} | {r['n_orgs']:,} | {r['n_flagged']:,} "
                f"| {r['rate']:.1%} |"
            )

    md_path = out_dir / f"summary_{label}.md"
    md_path.write_text("\n".join(lines) + "\n")
    return csv_path, md_path

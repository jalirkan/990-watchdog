"""Command-line entry point.

    watchdog990 run --extract data/raw/23eoextract990.csv --label 2023
    watchdog990 run --label 2023            # paths from settings.yaml
    watchdog990 org --ein 142007220         # ProPublica spot lookup
    watchdog990 diversion --governance outputs/governance_*.csv --label 2025

`run` is fully offline once the IRS files are on disk; `org` needs
internet (it calls the ProPublica API).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

from watchdog990 import diversion, flags, metrics, panel, report, trends
from watchdog990.ingest import bmf, efile_xml, propublica, soi_extract
from watchdog990.utils import load_settings

log = logging.getLogger("watchdog990")


def _cmd_run(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)

    extract_path = args.extract or settings["extract_files"].get(args.label)
    if not extract_path:
        log.error(
            "No extract file: pass --extract or add extract_files[%s] "
            "to %s",
            args.label,
            args.config,
        )
        return 2

    log.info("Loading extract: %s", extract_path)
    df = soi_extract.load(extract_path)
    log.info("Rows: %s", f"{len(df):,}")

    df = metrics.compute_all(df)
    hits = flags.evaluate(df, settings["thresholds"])
    log.info("Flag hits: %s", f"{len(hits):,}")

    names = None
    bmf_paths = args.bmf or settings.get("bmf_files") or []
    if bmf_paths:
        log.info("Loading BMF name table (%d file(s))", len(bmf_paths))
        names = bmf.load(bmf_paths, keep_eins=set(hits["ein"]))

    csv_path, md_path = report.write(
        hits, settings["output_dir"], args.label, names=names
    )
    log.info("Wrote %s and %s", csv_path, md_path)
    return 0


_CKPT_DIR = Path("data/interim")


def _ckpt(name: str) -> Path:
    return _CKPT_DIR / name


def _trend_stage_panel(settings: dict, labels: list[str]) -> int:
    """Stage 1: build the panel, screen the latest filing per org,
    checkpoint latest + hits to data/interim/."""
    frames = {}
    for lb in labels:
        path = settings["extract_files"].get(lb)
        if not path:
            log.error("No extract file for label %r", lb)
            return 2
        log.info("Loading extract %s (mapped columns only): %s", lb, path)
        frames[lb] = soi_extract.load_slim(path)
        log.info("Rows: %s", f"{len(frames[lb]):,}")

    pnl = panel.build_panel(frames)
    frames.clear()  # release source frames; the panel supersedes them
    log.info("Panel: %s filings, %s orgs", f"{len(pnl):,}", f"{pnl.ein.nunique():,}")
    pnl = trends.add_trend_metrics(metrics.compute_all(pnl))
    latest = panel.latest_per_org(pnl)
    del pnl  # screening evaluates the latest filing per org only

    hits = flags.evaluate(latest, settings["thresholds"])
    log.info("Flag hits (latest filing per org): %s", f"{len(hits):,}")

    # Context columns so the CSV reads like a workpaper — including
    # every flag input, so hits are recomputable from the checkpoint.
    context_cols = [
        c
        for c in (
            "ein", "tax_period", "n_filings", "consec_deficit_years",
            "runway_drop_streak", "months_net_assets", "surplus_margin",
            "officer_comp_ratio", "total_revenue", "total_expenses",
            "total_contributions", "net_assets_eoy",
        )
        if c in latest.columns
    ]
    hits = hits.merge(latest[context_cols], on="ein", how="left")

    _CKPT_DIR.mkdir(parents=True, exist_ok=True)
    latest[context_cols].to_csv(_ckpt("trend_latest.csv"), index=False)
    hits.to_csv(_ckpt("trend_hits.csv"), index=False)
    _ckpt("trend_meta.json").write_text(json.dumps({"labels": labels}))
    stale = _ckpt("trend_names.csv")
    if stale.exists():
        stale.unlink()  # a fresh panel invalidates appended names
    log.info("Checkpointed latest + hits to %s", _CKPT_DIR)
    return 0


def _read_ckpt(name: str) -> pd.DataFrame:
    # Code-like columns must survive the CSV round-trip as strings —
    # NaN-bearing "03" columns otherwise come back as float 3.0.
    return pd.read_csv(
        _ckpt(name),
        dtype={
            "ein": "string",
            "subsection": "string",
            "ntee_cd": "string",
            "ntee_major": "string",
        },
    )


def _trend_stage_names(settings: dict, args: argparse.Namespace) -> int:
    """Stage 2: filter BMF file(s) to panel EINs and append to the
    names checkpoint. Callable repeatedly with --bmf subsets so large
    region files can be processed a few at a time."""
    latest = _read_ckpt("trend_latest.csv")
    bmf_paths = args.bmf or settings.get("bmf_files") or []
    if not bmf_paths:
        log.warning("No BMF files given; skipping names stage")
        return 0
    log.info("Names stage: %d BMF file(s)", len(bmf_paths))
    names = bmf.load(bmf_paths, keep_eins=set(latest["ein"]))
    out = _ckpt("trend_names.csv")
    append = out.exists() and bool(args.bmf)
    names.to_csv(out, mode="a" if append else "w", header=not append, index=False)
    log.info(
        "%s %s name rows -> %s",
        "Appended" if append else "Wrote",
        f"{len(names):,}",
        out,
    )
    return 0


def _trend_stage_report(settings: dict, args: argparse.Namespace) -> int:
    """Stage 3: assemble checkpoints into the flags CSV + summary."""
    meta = json.loads(_ckpt("trend_meta.json").read_text())
    labels = meta["labels"]
    latest = _read_ckpt("trend_latest.csv")
    hits = _read_ckpt("trend_hits.csv")

    gov_stats = None
    gov_path = getattr(args, "governance", None)
    if gov_path and Path(gov_path).exists():
        gov = pd.read_csv(gov_path, dtype={"ein": "string"})
        gov = gov[gov.get("is_form_990", True) == True]  # noqa: E712

        # Expense-breakdown enrichment: strictly period-matched — the
        # XML return must be the SAME filing as the org's latest panel
        # row, otherwise ratios from different years would mix.
        exp_cols = ["program_expenses", "fundraising_expenses", "total_expenses_xml"]
        if all(c in gov.columns for c in exp_cols):
            xml_fin = gov[["ein", "tax_period", *exp_cols]].drop_duplicates(
                subset=["ein", "tax_period"], keep="last"
            )
            enriched = latest.drop(
                columns=[c for c in exp_cols if c in latest.columns]
            ).merge(xml_fin, on=["ein", "tax_period"], how="inner")
            te = pd.to_numeric(enriched["total_expenses_xml"], errors="coerce")
            pe = pd.to_numeric(enriched["program_expenses"], errors="coerce")
            enriched["program_expense_ratio"] = pe / te.replace(0, pd.NA)
            # Private contributions for the rebased zero-fundraising
            # rule (NA when the breakdown wasn't parsed for this row).
            if "total_contributions_xml" in gov.columns:
                cb = gov[["ein", "tax_period", "total_contributions_xml",
                          "govt_grants_xml", "related_org_contrib_xml"]
                         ].drop_duplicates(["ein", "tax_period"], keep="last")
                enriched = enriched.merge(cb, on=["ein", "tax_period"], how="left")
                tc = pd.to_numeric(
                    enriched["total_contributions_xml"], errors="coerce"
                )
                gg = pd.to_numeric(
                    enriched["govt_grants_xml"], errors="coerce"
                ).fillna(0)
                ro = pd.to_numeric(
                    enriched["related_org_contrib_xml"], errors="coerce"
                ).fillna(0)
                enriched["private_contributions"] = tc - gg - ro
            exp_hits = flags.xml_expense_flags(enriched, settings["thresholds"])
            log.info(
                "Expense enrichment: %s orgs period-matched; "
                "LOW_PROGRAM_RATIO %s, ZERO_FUNDRAISING_COST %s",
                f"{len(enriched):,}",
                (exp_hits.flag_id == "LOW_PROGRAM_RATIO").sum(),
                (exp_hits.flag_id == "ZERO_FUNDRAISING_COST").sum(),
            )
            if not exp_hits.empty:
                hits = pd.concat([hits, exp_hits], ignore_index=True)
        gov = (
            gov.sort_values("tax_period")
            .groupby("ein", sort=False)
            .tail(1)[
                [
                    "ein", "tax_period", "material_diversion",
                    "loans_to_insiders", "board_independence",
                    "schedule_l_present",
                ]
            ]
            .rename(columns={"tax_period": "gov_tax_period"})
        )
        gov_hits = flags.governance_flags(gov, set(latest["ein"]))
        if not gov_hits.empty:
            log.info("MATERIAL_DIVERSION hits (panel-wide): %s", len(gov_hits))
            hits = pd.concat([hits, gov_hits], ignore_index=True)
        before_cov = hits["ein"].isin(set(gov["ein"])).sum()
        hits = hits.merge(gov, on="ein", how="left")
        flagged_gov = gov[gov["ein"].isin(set(hits["ein"]))]
        gov_stats = {
            "flagged_covered": int(flagged_gov["ein"].nunique()),
            "flagged_total": int(hits["ein"].nunique()),
            "diversion": int((flagged_gov.material_diversion == True).sum()),  # noqa: E712
            "insider_loans": int((flagged_gov.loans_to_insiders == True).sum()),  # noqa: E712
            "median_independence": float(
                pd.to_numeric(
                    flagged_gov.board_independence, errors="coerce"
                ).median()
            ),
            "schedule_l": int((flagged_gov.schedule_l_present == True).sum()),  # noqa: E712
        }
        log.info(
            "Governance join: %s of %s flagged orgs covered (%s hit rows)",
            f"{gov_stats['flagged_covered']:,}",
            f"{gov_stats['flagged_total']:,}",
            f"{before_cov:,}",
        )

    names = None
    sector_table = None
    subsection_table = None
    names_path = _ckpt("trend_names.csv")
    if names_path.exists():
        names = _read_ckpt("trend_names.csv").drop_duplicates(
            subset="ein", keep="last"
        )
        join_cols = [
            c for c in ("ntee_major", "subsection") if c in names.columns
        ]
        if join_cols:
            pop = latest[["ein"]].merge(
                names[["ein", *join_cols]], on="ein", how="left"
            )
            if "ntee_major" in join_cols:
                # Sector-relative screen runs here — the only stage
                # where the population carries its sector.
                latest_sect = latest.merge(
                    names[["ein", "ntee_major"]], on="ein", how="left"
                )
                sector_hits = flags.sector_outliers(
                    latest_sect, settings["thresholds"]
                )
                if not sector_hits.empty:
                    log.info(
                        "Sector-relative hits: %s", f"{len(sector_hits):,}"
                    )
                    hits = pd.concat([hits, sector_hits], ignore_index=True)
            flagged = set(hits["ein"])
            if "ntee_major" in join_cols:
                sector_table = report.sector_rates(pop, flagged)
            if "subsection" in join_cols:
                subsection_table = report.subsection_rates(pop, flagged)

    label = f"{labels[0]}-{labels[-1]}_trend"
    csv_path, md_path = report.write(
        hits, settings["output_dir"], label, names=names,
        sector_table=sector_table, subsection_table=subsection_table,
        gov_stats=gov_stats,
    )
    log.info("Wrote %s and %s", csv_path, md_path)
    return 0


def _cmd_trend(args: argparse.Namespace) -> int:
    """Multi-year screen: point flags on each org's latest filing,
    trend flags on its trailing streaks.

    --stage panel|names|report runs one checkpointed step at a time
    (for small machines or short execution windows); default runs all
    three in sequence.
    """
    settings = load_settings(args.config)

    labels = args.labels or sorted(settings["extract_files"])
    if len(labels) < 2:
        log.error(
            "Trend needs >=2 processing years; have %s. Add files to "
            "extract_files in %s or pass --labels.",
            labels,
            args.config,
        )
        return 2

    stage = getattr(args, "stage", None)
    if stage in (None, "panel"):
        rc = _trend_stage_panel(settings, labels)
        if rc or stage == "panel":
            return rc
    if stage in (None, "names"):
        rc = _trend_stage_names(settings, args)
        if rc or stage == "names":
            return rc
    return _trend_stage_report(settings, args)


def _cmd_xml_plan(args: argparse.Namespace) -> int:
    """Targeted-acquisition planner: which TEOS batch zips cover the
    flagged orgs' e-filed returns, ranked by coverage.

    Reads the IRS per-year index CSV(s) and a flags CSV; writes
    outputs/xml_plan_<label>.csv with one row per batch zip. Download
    the top few batches instead of whole years."""
    from watchdog990.schema import normalize_ein as _norm

    settings = load_settings(args.config)
    hits = pd.read_csv(args.flags, dtype={"ein": "string"})
    eins = set(_norm(hits["ein"]))
    log.info("Flagged orgs: %s", f"{len(eins):,}")

    frames = []
    for ix in args.index:
        df = pd.read_csv(
            ix,
            usecols=["EIN", "TAX_PERIOD", "RETURN_TYPE", "XML_BATCH_ID"],
            dtype="string",
        )
        frames.append(df)
        log.info("Index %s: %s returns", ix, f"{len(df):,}")
    idx = pd.concat(frames, ignore_index=True)
    frames.clear()
    idx["EIN"] = _norm(idx["EIN"])

    m = idx[idx["EIN"].isin(eins)]
    covered = m["EIN"].nunique()
    log.info(
        "Flagged orgs with an e-filed return in these indexes: %s (%.1f%%)",
        f"{covered:,}", 100 * covered / max(len(eins), 1),
    )

    plan = (
        m.groupby("XML_BATCH_ID")
        .agg(returns=("EIN", "size"), flagged_orgs=("EIN", "nunique"))
        .sort_values("flagged_orgs", ascending=False)
        .reset_index()
    )
    out_dir = Path(settings["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / f"xml_plan_{args.label}.csv"
    plan.to_csv(plan_path, index=False)
    log.info("Wrote %s", plan_path)
    for _, r in plan.head(8).iterrows():
        log.info(
            "  %s: %s flagged orgs (%s returns)",
            r["XML_BATCH_ID"], f"{r['flagged_orgs']:,}", f"{r['returns']:,}",
        )
    return 0


def _cmd_xml(args: argparse.Namespace) -> int:
    """Parse governance signals from local e-file XML (files, dirs,
    or TEOS monthly zips) into outputs/governance_<label>.csv.

    Prints per-field NA rates: on a real batch, a high NA rate means
    an ALTERNATES name in ingest/efile_xml.py needs fixing — same
    drill as the extract schema verification."""
    settings = load_settings(args.config)
    df = efile_xml.load(args.path)
    if df.empty:
        log.error("No parseable XML under %s", args.path)
        return 2

    out_dir = Path(settings["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"governance_{args.label}.csv"
    df.to_csv(csv_path, index=False)

    n = len(df)
    core = df[df["is_form_990"]]
    log.info("Parsed %s return(s); %s are Form 990", f"{n:,}", f"{len(core):,}")
    if not core.empty:
        log.info(
            "material_diversion=True: %s | loans_to_insiders=True: %s | "
            "median board independence: %s | Schedule L present: %s",
            f"{(core.material_diversion == True).sum():,}",  # noqa: E712
            f"{(core.loans_to_insiders == True).sum():,}",  # noqa: E712
            f"{pd.to_numeric(core.board_independence, errors='coerce').median():.2f}",
            f"{core.schedule_l_present.mean():.1%}",
        )
        for col in ("tax_period", "material_diversion", "loans_to_insiders",
                    "voting_members", "independent_members"):
            na = core[col].isna().mean()
            if na > 0.05:
                log.warning(
                    "VERIFY: %s is NA on %.1f%% of Form 990 returns — "
                    "check ALTERNATES in ingest/efile_xml.py", col, na * 100
                )
    log.info("Wrote %s", csv_path)
    return 0


def _cmd_diversion(args: argparse.Namespace) -> int:
    """Build the manual-review workpaper for the material-diversion
    cohort into outputs/diversion_review_<label>.csv.

    One row per superseded (ein, tax period) that admitted a diversion
    on Part VI line 5 and filed a Schedule O explanation. The rule and
    why each leg of it exists is documented in diversion.py; this
    command exists so the file is regenerated rather than
    reconstructed from memory at the next refresh."""
    settings = load_settings(args.config)
    adm = diversion.load_governance(args.governance)
    if adm.empty:
        log.error("No material-diversion admissions in %s", args.governance)
        return 2

    wp = diversion.build_workpaper(adm)
    out_dir = Path(settings["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"diversion_review_{args.label}.csv"
    wp.to_csv(csv_path, index=False)

    # The three counts a refresh should reconcile: what was filed,
    # what survived the supersede, and how many organizations that is.
    no_text = int((diversion.explanation_text(adm) == "").sum())
    if no_text:
        log.warning(
            "%s admission(s) carry no Schedule O explanation and are NOT "
            "in the workpaper — investigate before publishing a count",
            f"{no_text:,}",
        )
    log.info(
        "Admissions %s -> workpaper %s row(s), %s unique organization(s) "
        "(%s superseded on (ein, tax_period))",
        f"{len(adm):,}",
        f"{len(wp):,}",
        f"{wp.ein.nunique():,}",
        f"{len(adm) - no_text - len(wp):,}",
    )
    log.info("Wrote %s", csv_path)
    return 0


def _cmd_org(args: argparse.Namespace) -> int:
    data = propublica.get_organization(args.ein)
    org = data.get("organization", {})
    print(json.dumps(org, indent=2)[:4000])
    filings = data.get("filings_with_data", [])
    print(f"\nfilings_with_data: {len(filings)} year(s) available")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(prog="watchdog990")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Screen an SOI extract file")
    p_run.add_argument("--extract", help="Path to the extract CSV")
    p_run.add_argument("--bmf", nargs="*", help="BMF CSV path(s) for org names")
    p_run.add_argument("--label", default="latest", help="Label for output files")
    p_run.add_argument("--config", default="config/settings.yaml")
    p_run.set_defaults(fn=_cmd_run)

    p_trend = sub.add_parser(
        "trend", help="Multi-year screen across processing-year extracts"
    )
    p_trend.add_argument(
        "--labels", nargs="*",
        help="extract_files labels to stack (default: all, ascending)",
    )
    p_trend.add_argument("--bmf", nargs="*", help="BMF CSV path(s)")
    p_trend.add_argument(
        "--stage", choices=["panel", "names", "report"],
        help="Run one checkpointed stage (resumable); default: all",
    )
    p_trend.add_argument(
        "--governance",
        help="governance_<label>.csv from `watchdog990 xml` to join "
        "onto flagged orgs (context columns + summary section)",
    )
    p_trend.add_argument("--config", default="config/settings.yaml")
    p_trend.set_defaults(fn=_cmd_trend)

    p_plan = sub.add_parser(
        "xml-plan", help="Rank TEOS batch zips by flagged-org coverage"
    )
    p_plan.add_argument("--flags", required=True, help="flags_*.csv from a run")
    p_plan.add_argument(
        "--index", nargs="+", required=True, help="IRS index_<year>.csv file(s)"
    )
    p_plan.add_argument("--label", default="plan")
    p_plan.add_argument("--config", default="config/settings.yaml")
    p_plan.set_defaults(fn=_cmd_xml_plan)

    p_xml = sub.add_parser(
        "xml", help="Parse governance signals from local e-file XML"
    )
    p_xml.add_argument(
        "--path", required=True,
        help="XML file, directory of XMLs, or TEOS monthly .zip",
    )
    p_xml.add_argument("--label", default="xml", help="Label for output file")
    p_xml.add_argument("--config", default="config/settings.yaml")
    p_xml.set_defaults(fn=_cmd_xml)

    p_div = sub.add_parser(
        "diversion",
        help="Build the material-diversion review workpaper from "
        "parsed governance CSVs",
    )
    p_div.add_argument(
        "--governance", nargs="+", required=True,
        help="governance_<label>.csv file(s) from `watchdog990 xml`; "
        "sorted before stacking so the supersede rule is deterministic",
    )
    p_div.add_argument("--label", default="review", help="Label for output file")
    p_div.add_argument("--config", default="config/settings.yaml")
    p_div.set_defaults(fn=_cmd_diversion)

    p_org = sub.add_parser("org", help="Look up one org via ProPublica")
    p_org.add_argument("--ein", required=True)
    p_org.set_defaults(fn=_cmd_org)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

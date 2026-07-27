"""Command-line entry point.

    watchdog990 run --extract data/raw/23eoextract990.csv --label 2023
    watchdog990 run --label 2023            # paths from settings.yaml
    watchdog990 org --ein 142007220         # ProPublica spot lookup

`run` is fully offline once the IRS files are on disk; `org` needs
internet (it calls the ProPublica API).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from watchdog990 import flags, metrics, report
from watchdog990.ingest import bmf, propublica, soi_extract
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
        names = bmf.load(bmf_paths)

    csv_path, md_path = report.write(
        hits, settings["output_dir"], args.label, names=names
    )
    log.info("Wrote %s and %s", csv_path, md_path)
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

    p_org = sub.add_parser("org", help="Look up one org via ProPublica")
    p_org.add_argument("--ein", required=True)
    p_org.set_defaults(fn=_cmd_org)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

"""Shared helpers: settings loading with sane defaults."""

from __future__ import annotations

from pathlib import Path

import yaml

DEFAULTS: dict = {
    "sources": {
        "propublica_api_base": "https://projects.propublica.org/nonprofits/api/v2",
    },
    "extract_files": {},
    "bmf_files": [],
    "thresholds": {
        "officer_comp_ratio_max": 0.30,
        "program_expense_ratio_min": 0.50,
        "months_net_assets_min": 1.0,
        "large_contributions_floor": 1_000_000,
    },
    "output_dir": "outputs",
}


def load_settings(path: str | Path = "config/settings.yaml") -> dict:
    """Read settings.yaml over DEFAULTS (shallow merge per top-level key)."""
    merged = {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    p = Path(path)
    if p.exists():
        with p.open() as fh:
            user = yaml.safe_load(fh) or {}
        for key, value in user.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key].update(value)
            else:
                merged[key] = value
    # YAML parses an unquoted `2024:` as an int key while CLI labels
    # are strings; normalize so the lookup can't silently miss.
    merged["extract_files"] = {
        str(k): v for k, v in (merged.get("extract_files") or {}).items()
    }
    return merged

"""Persisted query settings (country, start/end date range) for the CLI.

Stored in dunkelflauten.config.json at the repository root so repeated runs
don't need to repeat --start/--end on the command line. "end" is optional and
defaults to today, so simply re-running the script extends the analysed range.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("dunkelflauten.config.json")


@dataclass
class QueryConfig:
    country: str
    start: date
    end: date | None = None


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> QueryConfig:
    if not path.exists():
        raise SystemExit(
            f"Config file {path} not found. Create it with e.g. "
            '{"country": "de", "start": "2025-01-01"}, or pass --start/--end explicitly.'
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return QueryConfig(
        country=raw.get("country", "de"),
        start=date.fromisoformat(raw["start"]),
        end=date.fromisoformat(raw["end"]) if raw.get("end") else None,
    )

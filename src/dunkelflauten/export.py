"""Write classified Dunkelflaute events to the data/ folder as JSON and CSV."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import DunkelflauteEvent


def write_json(events: list[DunkelflauteEvent], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump([event.to_dict() for event in events], f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_csv(events: list[DunkelflauteEvent], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(DunkelflauteEvent.csv_header())
        for event in events:
            writer.writerow(event.to_csv_row())

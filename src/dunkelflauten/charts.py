"""Generate yearly development charts (PNG) from the classified data/ CSV files,
for embedding in README.md (see `## Charts` section).

Usage:
    python -m dunkelflauten.charts
    python -m dunkelflauten.charts --country de --data data --outdir docs/charts
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless rendering, no display needed
import matplotlib.pyplot as plt

CATEGORY_COLORS = {"A": "#c0392b", "B": "#f39c12"}


def _read_year_stats(year_dir: Path) -> dict:
    """Read event count, critical days and residual energy per category for one year folder."""
    stats = {
        "events": {"A": 0, "B": 0},
        "critical_days": {"A": 0, "B": 0},
        "residual_energy_gwh": {"A": 0.0, "B": 0.0},
    }
    for category in ("A", "B"):
        csv_path = year_dir / f"dunkelflauten_{category}.csv"
        if not csv_path.exists():
            continue
        with csv_path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                stats["events"][category] += 1
                stats["critical_days"][category] += int(row["critical_days"])
                energy = row.get("residual_energy_gwh")
                if energy:
                    stats["residual_energy_gwh"][category] += float(energy)
    return stats


def collect_yearly_stats(country_dir: Path) -> dict[int, dict]:
    """Collect per-year stats for every year folder found under data/<country>/."""
    yearly = {}
    for year_dir in sorted(country_dir.iterdir()):
        if year_dir.is_dir() and year_dir.name.isdigit():
            yearly[int(year_dir.name)] = _read_year_stats(year_dir)
    return yearly


def _stacked_bar_chart(
    years: list[int],
    a_values: list[float],
    b_values: list[float],
    title: str,
    ylabel: str,
    path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(years, a_values, label="A (0-40 %)", color=CATEGORY_COLORS["A"])
    ax.bar(years, b_values, bottom=a_values, label="B (40-60 %)", color=CATEGORY_COLORS["B"])
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.set_xticks(years)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def generate_charts(data_dir: Path, outdir: Path, country: str) -> list[Path]:
    """Generate all yearly development charts for `country` and return the written file paths."""
    country_dir = data_dir / country
    yearly = collect_yearly_stats(country_dir)
    years = sorted(yearly)

    written: list[Path] = []

    events_path = outdir / "dunkelflauten_events_per_year.png"
    _stacked_bar_chart(
        years,
        [yearly[y]["events"]["A"] for y in years],
        [yearly[y]["events"]["B"] for y in years],
        "Dunkelflauten events per year",
        "Number of events",
        events_path,
    )
    written.append(events_path)

    critical_days_path = outdir / "dunkelflauten_critical_days_per_year.png"
    _stacked_bar_chart(
        years,
        [yearly[y]["critical_days"]["A"] for y in years],
        [yearly[y]["critical_days"]["B"] for y in years],
        "Critical days (not yet battery-bufferable) per year",
        "Days",
        critical_days_path,
    )
    written.append(critical_days_path)

    energy_path = outdir / "dunkelflauten_residual_energy_per_year.png"
    _stacked_bar_chart(
        years,
        [yearly[y]["residual_energy_gwh"]["A"] for y in years],
        [yearly[y]["residual_energy_gwh"]["B"] for y in years],
        "Residual load energy per year",
        "GWh",
        energy_path,
    )
    written.append(energy_path)

    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", default="de", help="Country code folder under data/ (default: de)")
    parser.add_argument("--data", default="data", type=Path, help="Input data folder (default: data)")
    parser.add_argument("--outdir", default=Path("docs/charts"), type=Path, help="Output folder for PNGs (default: docs/charts)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    written = generate_charts(args.data, args.outdir, args.country)
    for path in written:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()

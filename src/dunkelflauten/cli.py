"""Command line script: fetch Dunkelflaute events from the Energy-Charts API
and write them to data/<country>/<year>/ as JSON and CSV, one calendar year
at a time. Complete past years are only fetched once and then left untouched;
only the current (still incomplete) year - or years that don't have data yet
- are re-fetched on subsequent runs. Use --force to refresh past years too
(e.g. after Energy-Charts revises historical values).

The queried date range (country, start, optional end) is persisted in
dunkelflauten.config.json so it doesn't need to be repeated on every run.
--end defaults to today when neither --end nor a config "end" is set.

Usage:
    python -m dunkelflauten.cli                              # uses dunkelflauten.config.json
    python -m dunkelflauten.cli --start 2025-01-01 --end 2025-10-21   # overrides config
    python -m dunkelflauten.cli --force                      # re-fetch past years too
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .api_client import get_daily_renewable_share_range
from .classification import classify_events, summarize
from .config import DEFAULT_CONFIG_PATH, load_config
from .energy_analysis import annotate_energy_metrics, fetch_power_series
from .export import write_csv, write_json

CATEGORY_A_BAND_PERCENT = (0.0, 40.0)
CATEGORY_B_BAND_PERCENT = (40.0, 60.0)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, type=Path, help="Path to config JSON (default: dunkelflauten.config.json)")
    parser.add_argument("--country", default=None, help="Energy-Charts country code (overrides config)")
    parser.add_argument("--start", default=None, type=date.fromisoformat, help="Start date, YYYY-MM-DD (overrides config)")
    parser.add_argument("--end", default=None, type=date.fromisoformat, help="End date, YYYY-MM-DD (overrides config, default: today)")
    parser.add_argument("--outdir", default="data", type=Path, help="Output folder (default: data)")
    parser.add_argument("--force", action="store_true", help="Re-fetch and overwrite complete past years too")
    return parser.parse_args(argv)


def _year_bounds(year: int, start: date, end: date) -> tuple[date, date]:
    return max(start, date(year, 1, 1)), min(end, date(year, 12, 31))


def _process_year(country: str, year_start: date, year_end: date, year_dir: Path) -> None:
    daily_shares = get_daily_renewable_share_range(country, year_start, year_end)
    if not daily_shares:
        print(f"  no renewable-share data available for {country} between {year_start} and {year_end}, skipping")
        return

    a_events = classify_events(daily_shares, *CATEGORY_A_BAND_PERCENT, "A", country)
    b_events = classify_events(daily_shares, *CATEGORY_B_BAND_PERCENT, "B", country)

    power_series = fetch_power_series(country, year_start, year_end)
    a_events = annotate_energy_metrics(a_events, power_series)
    b_events = annotate_energy_metrics(b_events, power_series)

    write_json(a_events, year_dir / "dunkelflauten_A.json")
    write_csv(a_events, year_dir / "dunkelflauten_A.csv")
    write_json(b_events, year_dir / "dunkelflauten_B.json")
    write_csv(b_events, year_dir / "dunkelflauten_B.csv")

    for label, events in (("A ([0, 40) %)", a_events), ("B ([40, 60) %)", b_events)):
        stats = summarize(events)
        print(f"  Category {label}: {stats['total_events']} events")
        for length, count in stats["counts_by_length"].items():
            print(f"    {count} x A{length}" if "A" in label else f"    {count} x B{length}")
        print(f"    total days below threshold: {stats['total_days_below_threshold']}")
        print(f"    total critical days (not battery-bufferable): {stats['total_critical_days']}")
        if stats["total_residual_energy_gwh"] is not None:
            print(f"    total residual energy (load - renewables): {stats['total_residual_energy_gwh']:,.1f} GWh")


def run(country: str, start: date, end: date, outdir: Path, force: bool = False) -> None:
    today = date.today()
    for year in range(start.year, end.year + 1):
        year_start, year_end = _year_bounds(year, start, end)
        year_dir = outdir / country / str(year)
        is_complete_past_year = year < today.year
        already_have_data = (year_dir / "dunkelflauten_A.json").exists()

        print(f"\n{country.upper()} {year} ({year_start.isoformat()}..{year_end.isoformat()})")
        if is_complete_past_year and already_have_data and not force:
            print("  already fetched, skipping (use --force to refresh)")
            continue

        _process_year(country, year_start, year_end, year_dir)

    print(f"\nData written under {outdir.resolve() / country}")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = load_config(args.config)
    country = args.country or config.country
    start = args.start or config.start
    end = args.end or config.end or date.today()
    run(country, start, end, args.outdir, args.force)


if __name__ == "__main__":
    main()

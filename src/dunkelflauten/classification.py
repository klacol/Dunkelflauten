"""Detection and classification of Dunkelflaute events from daily renewable-share data."""

from __future__ import annotations

from statistics import mean

from .api_client import DailyShare
from .models import DunkelflauteEvent

MIN_EVENT_LENGTH_DAYS = 2
"""A single day below the threshold can be buffered by batteries and does not count (no 'A1')."""


def _consecutive_runs_in_band(
    daily_shares: list[DailyShare], lower_percent: float, upper_percent: float
) -> list[list[DailyShare]]:
    """Split daily_shares (assumed date-sorted, possibly with gaps) into runs of
    consecutive calendar days where the share falls into [lower_percent, upper_percent).
    A gap in the date sequence (missing day), or a day outside the band, breaks a run.
    """
    runs: list[list[DailyShare]] = []
    current: list[DailyShare] = []

    for entry in daily_shares:
        in_band = lower_percent <= entry.renewable_share_percent < upper_percent
        continues_run = (
            current
            and in_band
            and (entry.day - current[-1].day).days == 1
        )
        if in_band and continues_run:
            current.append(entry)
        elif in_band:
            if current:
                runs.append(current)
            current = [entry]
        else:
            if current:
                runs.append(current)
            current = []

    if current:
        runs.append(current)

    return runs


def classify_events(
    daily_shares: list[DailyShare],
    lower_percent: float,
    upper_percent: float,
    category: str,
    country: str,
) -> list[DunkelflauteEvent]:
    """Detect Dunkelflaute events of one category (A or B) from daily share data.

    A and B are adjacent, non-overlapping bands (e.g. A = [0, 40), B = [40, 60)),
    so every day belongs to at most one category and the two event lists can be
    counted/summed without double-counting the same calendar days.
    """
    runs = _consecutive_runs_in_band(daily_shares, lower_percent, upper_percent)

    events: list[DunkelflauteEvent] = []
    sequence = 0
    for run in runs:
        if len(run) < MIN_EVENT_LENGTH_DAYS:
            continue  # single day: bufferable by batteries, not a Dunkelflaute

        sequence += 1
        length_days = len(run)
        shares = [entry.renewable_share_percent for entry in run]
        events.append(
            DunkelflauteEvent(
                id=f"{country.upper()}-{category}-{run[0].day.year}-{sequence:02d}",
                country=country,
                category=category,
                band_lower_percent=lower_percent,
                band_upper_percent=upper_percent,
                start_date=run[0].day,
                end_date=run[-1].day,
                length_days=length_days,
                battery_bufferable_days=1,
                critical_days=length_days - 1,
                min_renewable_share_percent=min(shares),
                avg_renewable_share_percent=mean(shares),
            )
        )
    return events


def summarize(events: list[DunkelflauteEvent]) -> dict:
    """Aggregate stats matching the style used to validate this tool (counts per length, day sums)."""
    counts_by_length: dict[int, int] = {}
    for event in events:
        counts_by_length[event.length_days] = counts_by_length.get(event.length_days, 0) + 1

    energies_gwh = [e.residual_energy_gwh for e in events if e.residual_energy_gwh is not None]

    return {
        "total_events": len(events),
        "counts_by_length": dict(sorted(counts_by_length.items(), reverse=True)),
        "total_days_below_threshold": sum(e.length_days for e in events),
        "total_critical_days": sum(e.critical_days for e in events),
        "total_residual_energy_gwh": round(sum(energies_gwh), 1) if energies_gwh else None,
    }

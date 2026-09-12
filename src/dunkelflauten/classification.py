"""Detection and classification of Dunkelflaute events from daily renewable-share data."""

from __future__ import annotations

from statistics import mean

from .api_client import DailyShare
from .models import DunkelflauteEvent

MIN_EVENT_LENGTH_DAYS = 2
"""A single day below the threshold can be buffered by batteries and does not count (no 'A1')."""


def _consecutive_runs_below_threshold(
    daily_shares: list[DailyShare], threshold_percent: float
) -> list[list[DailyShare]]:
    """Split daily_shares (assumed date-sorted, possibly with gaps) into runs of
    consecutive calendar days where the share is strictly below the threshold.
    A gap in the date sequence (missing day) breaks a run.
    """
    runs: list[list[DailyShare]] = []
    current: list[DailyShare] = []

    for entry in daily_shares:
        is_below = entry.renewable_share_percent < threshold_percent
        continues_run = (
            current
            and is_below
            and (entry.day - current[-1].day).days == 1
        )
        if is_below and continues_run:
            current.append(entry)
        elif is_below:
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
    threshold_percent: float,
    category: str,
    country: str,
) -> list[DunkelflauteEvent]:
    """Detect Dunkelflaute events of one category (A or B) from daily share data."""
    runs = _consecutive_runs_below_threshold(daily_shares, threshold_percent)

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
                threshold_percent=threshold_percent,
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


def annotate_nested_a_events(
    a_events: list[DunkelflauteEvent], b_events: list[DunkelflauteEvent]
) -> list[DunkelflauteEvent]:
    """Mark each B event that fully contains one or more A events.

    Category B (< 60 %) is not purely additive to category A (< 40 %): a
    severe A event is often a sub-period of a wider, less severe B event.
    Returns a new list of B events with contains_category_a / nested_event_ids set.
    """
    annotated: list[DunkelflauteEvent] = []
    for b_event in b_events:
        nested = [
            a_event.id
            for a_event in a_events
            if a_event.start_date >= b_event.start_date and a_event.end_date <= b_event.end_date
        ]
        if nested:
            annotated.append(
                DunkelflauteEvent(
                    **{
                        **b_event.__dict__,
                        "contains_category_a": True,
                        "nested_event_ids": nested,
                    }
                )
            )
        else:
            annotated.append(b_event)
    return annotated


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

"""Energy-based severity metrics for Dunkelflaute events.

A Dunkelflaute is ultimately an energy problem, not just a day count: the
(positive) gap between load and renewable generation, integrated over the
duration of the event. This module fetches the "Load" and "Residual load"
series (GET /public_power) and turns them into GW/GWh figures per event, so a
short cold-winter event and a longer mild-spring event can be compared fairly.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from .api_client import API_BASE_URL, REQUEST_TIMEOUT_SECONDS
from .models import DunkelflauteEvent

LOAD_SERIES_NAME = "Load"
RESIDUAL_LOAD_SERIES_NAME = "Residual load"

# Local timezone per country, used to map UTC timestamps to calendar days.
# Only Germany is supported so far; extend this when other countries are added.
COUNTRY_TIMEZONES = {"de": "Europe/Berlin"}
DEFAULT_TIMEZONE = "Europe/Berlin"


@dataclass(frozen=True)
class PowerTimeSeries:
    """Load and residual load (both MW) at their native reporting resolution."""

    timestamps: list[datetime]
    load_mw: list[float | None]
    residual_load_mw: list[float | None]


@dataclass(frozen=True)
class EnergyMetrics:
    avg_load_gw: float
    avg_residual_load_gw: float
    peak_residual_load_gw: float
    residual_energy_gwh: float


def fetch_power_series(country: str, start: date, end: date) -> PowerTimeSeries:
    """Fetch Load and Residual load for [start, end] in one request (GET /public_power)."""
    response = requests.get(
        f"{API_BASE_URL}/public_power",
        params={"country": country, "start": start.isoformat(), "end": end.isoformat()},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()

    tz = ZoneInfo(COUNTRY_TIMEZONES.get(country, DEFAULT_TIMEZONE))
    timestamps = [datetime.fromtimestamp(s, tz=tz) for s in payload["unix_seconds"]]
    series_by_name = {series["name"]: series["data"] for series in payload["production_types"]}

    return PowerTimeSeries(
        timestamps=timestamps,
        load_mw=series_by_name.get(LOAD_SERIES_NAME, []),
        residual_load_mw=series_by_name.get(RESIDUAL_LOAD_SERIES_NAME, []),
    )


def compute_energy_metrics(
    series: PowerTimeSeries, start_date: date, end_date: date
) -> EnergyMetrics | None:
    """Aggregate load/residual load over one event window (inclusive local calendar days)."""
    if len(series.timestamps) < 2:
        return None
    step_hours = (series.timestamps[1] - series.timestamps[0]).total_seconds() / 3600
    window_end_exclusive = end_date + timedelta(days=1)

    loads: list[float] = []
    residuals: list[float] = []
    for timestamp, load, residual in zip(series.timestamps, series.load_mw, series.residual_load_mw):
        if load is None or residual is None:
            continue
        if start_date <= timestamp.date() < window_end_exclusive:
            loads.append(load)
            residuals.append(residual)

    if not loads:
        return None

    residual_energy_mwh = sum(residual * step_hours for residual in residuals)
    return EnergyMetrics(
        avg_load_gw=(sum(loads) / len(loads)) / 1000,
        avg_residual_load_gw=(sum(residuals) / len(residuals)) / 1000,
        peak_residual_load_gw=max(residuals) / 1000,
        residual_energy_gwh=residual_energy_mwh / 1000,
    )


def annotate_energy_metrics(
    events: list[DunkelflauteEvent], series: PowerTimeSeries
) -> list[DunkelflauteEvent]:
    """Return a copy of events enriched with load/residual-load/energy figures."""
    annotated: list[DunkelflauteEvent] = []
    for event in events:
        metrics = compute_energy_metrics(series, event.start_date, event.end_date)
        if metrics is None:
            annotated.append(event)
            continue
        annotated.append(
            dataclasses.replace(
                event,
                avg_load_gw=round(metrics.avg_load_gw, 2),
                avg_residual_load_gw=round(metrics.avg_residual_load_gw, 2),
                peak_residual_load_gw=round(metrics.peak_residual_load_gw, 2),
                residual_energy_gwh=round(metrics.residual_energy_gwh, 1),
            )
        )
    return annotated

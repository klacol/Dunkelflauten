"""Thin client for the parts of the Energy-Charts API used by this project.

Data source: https://api.energy-charts.info/ (operated by Fraunhofer ISE).
Please respect the API's rate limits (see /README.md) and cache results
locally instead of re-fetching on every run.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import NamedTuple

import requests

API_BASE_URL = "https://api.energy-charts.info"
REQUEST_TIMEOUT_SECONDS = 60


class DailyShare(NamedTuple):
    day: date
    renewable_share_percent: float


def get_daily_renewable_share(country: str = "de", year: int = -1) -> list[DailyShare]:
    """Fetch the average daily renewable share of load for one calendar year.

    Uses GET /ren_share_daily_avg. ``year=-1`` returns the trailing 365 days.
    Returns a list of (day, share) sorted chronologically; days with a
    missing (null) value are omitted.
    """
    response = requests.get(
        f"{API_BASE_URL}/ren_share_daily_avg",
        params={"country": country, "year": year},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()

    days: list[str] = payload["days"]
    values: list[float | None] = payload["data"]

    result: list[DailyShare] = []
    for day_str, value in zip(days, values):
        if value is None:
            continue
        day = datetime.strptime(day_str, "%d.%m.%Y").date()
        result.append(DailyShare(day=day, renewable_share_percent=value))

    result.sort(key=lambda entry: entry.day)
    return result


def get_daily_renewable_share_range(
    country: str, start: date, end: date
) -> list[DailyShare]:
    """Fetch daily renewable shares covering [start, end], across calendar-year boundaries."""
    all_shares: dict[date, float] = {}
    for year in range(start.year, end.year + 1):
        for entry in get_daily_renewable_share(country=country, year=year):
            all_shares[entry.day] = entry.renewable_share_percent

    return sorted(
        (DailyShare(day=day, renewable_share_percent=share)
         for day, share in all_shares.items()
         if start <= day <= end),
        key=lambda entry: entry.day,
    )

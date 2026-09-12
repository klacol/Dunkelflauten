"""Data schema (master data) for a single Dunkelflaute event.

A "Dunkelflaute" is a run of two or more consecutive days on which the share
of renewable energy in the electricity mix stays below a given threshold.
See README.md for the full definition of categories A (< 40 %) and B (< 60 %).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any


@dataclass(frozen=True)
class DunkelflauteEvent:
    """Master data record describing one classified Dunkelflaute event."""

    id: str
    """Stable identifier, e.g. 'DE-A-2025-01'."""

    country: str
    """ISO-like country code as used by the Energy-Charts API, e.g. 'de'."""

    category: str
    """Category letter: 'A' (< 40 %) or 'B' (< 60 %)."""

    threshold_percent: float
    """Renewable share threshold that defines the category (40.0 or 60.0)."""

    start_date: date
    """First day of the event (share already below threshold)."""

    end_date: date
    """Last day of the event (share still below threshold)."""

    length_days: int
    """Duration x of the event in days below threshold (the 'x' in Ax/Bx)."""

    battery_bufferable_days: int
    """Number of days assumed coverable by short-term battery storage (always 1: the first day)."""

    critical_days: int
    """Days not coverable by batteries: length_days - battery_bufferable_days (the 'x-1')."""

    min_renewable_share_percent: float
    """Lowest daily renewable share observed during the event."""

    avg_renewable_share_percent: float
    """Average daily renewable share observed during the event."""

    contains_category_a: bool = False
    """For category B events only: True if a category A event is nested inside this event."""

    nested_event_ids: list[str] = field(default_factory=list)
    """IDs of category A events fully contained within this event (only used for category B)."""

    avg_load_gw: float | None = None
    """Average electricity load (demand) during the event, in gigawatt."""

    avg_residual_load_gw: float | None = None
    """Average residual load (load minus renewable generation) during the event, in gigawatt."""

    peak_residual_load_gw: float | None = None
    """Highest residual load observed during the event, in gigawatt."""

    residual_energy_gwh: float | None = None
    """Energy that had to be covered by non-renewable sources/storage/imports during the
    event: the residual load integrated over the event's duration (GW x h = GWh). This is
    the actual severity metric of a Dunkelflaute - a long event with low load (e.g. a mild
    spring week) can require less energy than a shorter event with high load (e.g. a cold
    winter cold snap)."""

    def label(self) -> str:
        """Short label such as 'A8' or 'B12'."""
        return f"{self.category}{self.length_days}"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["start_date"] = self.start_date.isoformat()
        d["end_date"] = self.end_date.isoformat()
        d["label"] = self.label()
        return d

    @staticmethod
    def csv_header() -> list[str]:
        return [
            "id",
            "country",
            "category",
            "label",
            "threshold_percent",
            "start_date",
            "end_date",
            "length_days",
            "battery_bufferable_days",
            "critical_days",
            "min_renewable_share_percent",
            "avg_renewable_share_percent",
            "contains_category_a",
            "nested_event_ids",
            "avg_load_gw",
            "avg_residual_load_gw",
            "peak_residual_load_gw",
            "residual_energy_gwh",
        ]

    def to_csv_row(self) -> list[Any]:
        return [
            self.id,
            self.country,
            self.category,
            self.label(),
            self.threshold_percent,
            self.start_date.isoformat(),
            self.end_date.isoformat(),
            self.length_days,
            self.battery_bufferable_days,
            self.critical_days,
            round(self.min_renewable_share_percent, 2),
            round(self.avg_renewable_share_percent, 2),
            self.contains_category_a,
            ";".join(self.nested_event_ids),
            self.avg_load_gw,
            self.avg_residual_load_gw,
            self.peak_residual_load_gw,
            self.residual_energy_gwh,
        ]

from datetime import date, timedelta

from dunkelflauten.api_client import DailyShare
from dunkelflauten.classification import annotate_nested_a_events, classify_events, summarize


def _shares(start: date, values: list[float]) -> list[DailyShare]:
    return [DailyShare(day=start + timedelta(days=i), renewable_share_percent=v) for i, v in enumerate(values)]


def test_single_day_dip_is_not_an_event():
    daily = _shares(date(2025, 1, 1), [80, 30, 80, 80])
    events = classify_events(daily, threshold_percent=40.0, category="A", country="de")
    assert events == []


def test_multi_day_run_is_classified_with_correct_length_and_critical_days():
    daily = _shares(date(2025, 1, 1), [80, 30, 25, 35, 80])
    events = classify_events(daily, threshold_percent=40.0, category="A", country="de")
    assert len(events) == 1
    event = events[0]
    assert event.length_days == 3
    assert event.critical_days == 2
    assert event.battery_bufferable_days == 1
    assert event.start_date == date(2025, 1, 2)
    assert event.end_date == date(2025, 1, 4)
    assert event.label() == "A3"


def test_gap_in_dates_breaks_the_run():
    daily = [
        DailyShare(day=date(2025, 1, 1), renewable_share_percent=30),
        DailyShare(day=date(2025, 1, 2), renewable_share_percent=30),
        # missing 2025-01-03
        DailyShare(day=date(2025, 1, 4), renewable_share_percent=30),
        DailyShare(day=date(2025, 1, 5), renewable_share_percent=30),
    ]
    events = classify_events(daily, threshold_percent=40.0, category="A", country="de")
    assert len(events) == 2
    assert all(e.length_days == 2 for e in events)


def test_nested_a_event_is_detected_inside_b_event():
    # 5 days below 60%, with the middle 3 days also below 40%
    daily = _shares(date(2025, 1, 1), [55, 35, 25, 35, 55])
    a_events = classify_events(daily, threshold_percent=40.0, category="A", country="de")
    b_events = classify_events(daily, threshold_percent=60.0, category="B", country="de")
    b_events = annotate_nested_a_events(a_events, b_events)

    assert len(a_events) == 1
    assert len(b_events) == 1
    assert b_events[0].contains_category_a is True
    assert b_events[0].nested_event_ids == [a_events[0].id]


def test_summarize_counts_and_sums():
    daily = _shares(date(2025, 1, 1), [30, 30, 80, 30, 30, 30])
    events = classify_events(daily, threshold_percent=40.0, category="A", country="de")
    stats = summarize(events)

    assert stats["total_events"] == 2
    assert stats["counts_by_length"] == {3: 1, 2: 1}
    assert stats["total_days_below_threshold"] == 5
    assert stats["total_critical_days"] == 3

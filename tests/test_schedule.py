from datetime import datetime

import pytest

from custom_components.taiwan_work_school.schedule import evening_minutes, next_evening_update


@pytest.mark.parametrize(
    ("interval", "count", "expected"),
    [
        (3, 6, (0, 3, 6, 9, 12, 15)),
        (5, 4, (0, 5, 10, 15)),
        (1, 16, tuple(range(16))),
        (15, 1, (0,)),
    ],
)
def test_minutes(interval, count, expected):
    assert evening_minutes(interval, count) == expected


@pytest.mark.parametrize(("interval", "count"), [(0, 3), (16, 1), (3, 0), (1, 17), (5, 5)])
def test_invalid(interval, count):
    with pytest.raises(ValueError):
        evening_minutes(interval, count)


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        ("2026-10-22T19:59:59+08:00", "2026-10-22T20:00:00+08:00"),
        ("2026-10-22T20:00:00+08:00", "2026-10-22T20:03:00+08:00"),
        ("2026-10-22T20:14:59+08:00", "2026-10-22T20:15:00+08:00"),
        ("2026-10-22T20:15:00+08:00", "2026-10-23T20:00:00+08:00"),
        ("2026-10-22T21:00:00+08:00", "2026-10-23T20:00:00+08:00"),
        ("2026-10-22T12:02:00+00:00", "2026-10-22T20:03:00+08:00"),
        ("2026-12-31T23:59:00+08:00", "2027-01-01T20:00:00+08:00"),
    ],
)
def test_next_update(now, expected):
    assert next_evening_update(datetime.fromisoformat(now), 3, 6).isoformat() == expected


@pytest.mark.parametrize(
    "now,expected,evening",
    [
        ("2026-10-23T23:59:59+08:00", "2026-10-24T00:00:00+08:00", True),
        ("2026-10-23T23:59:59+08:00", "2026-10-24T00:00:00+08:00", False),
        ("2026-10-24T00:00:00+08:00", "2026-10-24T01:00:00+08:00", True),
        ("2026-10-23T15:59:59+00:00", "2026-10-24T00:00:00+08:00", True),
        ("2026-10-23T19:59:59+08:00", "2026-10-23T20:00:00+08:00", True),
        ("2026-10-23T20:00:00+08:00", "2026-10-23T20:03:00+08:00", True),
        ("2026-10-23T20:14:59+08:00", "2026-10-23T20:15:00+08:00", True),
        ("2026-10-23T20:15:00+08:00", "2026-10-23T21:00:00+08:00", True),
        ("2026-10-23T20:00:00+08:00", "2026-10-23T21:00:00+08:00", False),
        ("2026-10-23T11:28:00+08:00", "2026-10-23T12:00:00+08:00", True),
        ("2026-12-31T23:59:59+08:00", "2027-01-01T00:00:00+08:00", True),
    ],
)
def test_combined_schedule(now, expected, evening):
    from custom_components.taiwan_work_school.schedule import next_scheduled_update

    actual = next_scheduled_update(datetime.fromisoformat(now), 3, 6, evening)
    assert actual.isoformat() == expected


@pytest.mark.parametrize("count,expected_count", [(1, 24), (6, 29), (16, 39)])
def test_daily_schedule_deduplicates_20_and_includes_midnight(count, expected_count):
    from custom_components.taiwan_work_school.schedule import next_scheduled_update

    interval = 1 if count == 16 else 3
    cursor = datetime.fromisoformat("2026-10-22T23:59:59+08:00")
    slots = []
    while True:
        cursor = next_scheduled_update(cursor, interval, count)
        if cursor.day != 23:
            break
        slots.append(cursor)
    assert len(slots) == expected_count
    assert len(set(slots)) == len(slots)
    assert sum(point.hour == 20 and point.minute == 0 for point in slots) == 1
    assert slots[0].hour == slots[0].minute == slots[0].second == 0
    assert {point.hour for point in slots if point.minute == 0} == set(range(24))

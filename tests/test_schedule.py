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

"""Pure functions for the Taipei evening window."""

from datetime import datetime, time, timedelta

from .const import TAIPEI


def evening_minutes(interval: int, count: int) -> tuple[int, ...]:
    """Count includes 20:00; the window includes 20:15."""
    if not 1 <= interval <= 15 or not 1 <= count <= 16:
        raise ValueError("Invalid evening interval/count")
    if (count - 1) * interval > 15:
        raise ValueError("The configured count exceeds 20:15")
    return tuple(index * interval for index in range(count))


def next_evening_update(now: datetime, interval: int, count: int) -> datetime:
    local = now.astimezone(TAIPEI)
    minutes = evening_minutes(interval, count)
    for offset in (0, 1):
        start = datetime.combine(local.date() + timedelta(days=offset), time(20), TAIPEI)
        for minute in minutes:
            candidate = start + timedelta(minutes=minute)
            if candidate > local:
                return candidate
    raise AssertionError("Next day always has an update")

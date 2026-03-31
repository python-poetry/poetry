from __future__ import annotations

import re

from datetime import datetime
from datetime import timezone

import pytimeparse

from dateutil.relativedelta import relativedelta


def parse_duration(duration_str: str) -> datetime:
    """
    Parse a human-readable duration string to a datetime.

    Converts strings like "1 week", "3 days", "2 months" to a datetime
    representing the cutoff point (current time minus the duration).

    :param duration_str: A human-readable duration string (e.g., "1 week")
    :return: A datetime object representing the cutoff time
    :raises ValueError: If the duration string is invalid
    """
    if not duration_str:
        raise ValueError("Invalid duration: empty string")

    # Handle month-based durations explicitly since pytimeparse doesn't support them
    month_match = re.match(r"^(\d+)\s*months?$", duration_str.strip(), re.IGNORECASE)
    if month_match:

        months = int(month_match.group(1))
        now = datetime.now(timezone.utc)
        return now - relativedelta(months=months)

    # pytimeparse returns seconds as an integer or None on failure
    seconds = pytimeparse.parse(duration_str)

    if seconds is None:
        raise ValueError(f"Invalid duration: {duration_str!r}")

    now = datetime.now(timezone.utc)
    return now - relativedelta(seconds=seconds)

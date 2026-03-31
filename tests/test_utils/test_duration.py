from __future__ import annotations

from datetime import datetime, timezone

import pytest
from dateutil.relativedelta import relativedelta

from poetry.utils.duration import parse_duration


def test_parse_duration_valid_formats():
    """Test various valid duration formats."""
    now = datetime.now(timezone.utc)

    # "1 week"
    result = parse_duration("1 week")
    expected = now - relativedelta(weeks=1)
    assert abs((result - expected).total_seconds()) < 2  # within 2 seconds

    # "3 days"
    result = parse_duration("3 days")
    expected = now - relativedelta(days=3)
    assert abs((result - expected).total_seconds()) < 2

    # "2 months"
    result = parse_duration("2 months")
    expected = now - relativedelta(months=2)
    assert abs((result - expected).total_seconds()) < 2


def test_parse_duration_invalid_format():
    """Test that invalid formats raise ValueError."""
    with pytest.raises(ValueError, match="Invalid duration"):
        parse_duration("invalid")
    with pytest.raises(ValueError, match="Invalid duration"):
        parse_duration("1")
    with pytest.raises(ValueError, match="Invalid duration"):
        parse_duration("week")

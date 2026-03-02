"""Tests for gcalx.shared.dates — date/time parsing and formatting."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from gcalx.shared.dates import (
    event_duration_minutes,
    format_date_header,
    format_duration,
    format_full_date,
    format_relative_date,
    format_time,
    is_all_day,
    parse_date,
    parse_datetime,
    parse_event_time,
    rfc3339,
    rfc3339_date,
)

# ── parse_date ─────────────────────────────────────────────────────


class TestParseDate:
    """Tests for natural language date parsing."""

    @pytest.mark.parametrize("text", ["today", "tod", "TODAY", " Today "])
    def test_today(self, text: str) -> None:
        assert parse_date(text) == date.today()

    @pytest.mark.parametrize("text", ["tomorrow", "tmrw", "tom"])
    def test_tomorrow(self, text: str) -> None:
        assert parse_date(text) == date.today() + timedelta(days=1)

    @pytest.mark.parametrize("text", ["yesterday", "yday"])
    def test_yesterday(self, text: str) -> None:
        assert parse_date(text) == date.today() - timedelta(days=1)

    def test_weekday_name_next_occurrence(self) -> None:
        # Monday is weekday 0
        with patch("gcalx.shared.dates.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 2)  # a Monday
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            # "monday" on a Monday → next Monday (7 days)
            result = parse_date("monday")
            assert result == date(2026, 3, 9)

    def test_weekday_name_later_this_week(self) -> None:
        with patch("gcalx.shared.dates.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 2)  # Monday
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            # "wednesday" (2) on Monday (0) → 2 days later
            result = parse_date("wed")
            assert result == date(2026, 3, 4)

    @pytest.mark.parametrize(
        "text, expected_days",
        [("3d", 3), ("1day", 1), ("10days", 10)],
    )
    def test_relative_days(self, text: str, expected_days: int) -> None:
        assert parse_date(text) == date.today() + timedelta(days=expected_days)

    @pytest.mark.parametrize(
        "text, expected_weeks",
        [("2w", 2), ("1week", 1), ("3weeks", 3)],
    )
    def test_relative_weeks(self, text: str, expected_weeks: int) -> None:
        assert parse_date(text) == date.today() + timedelta(weeks=expected_weeks)

    def test_relative_months(self) -> None:
        result = parse_date("1m")
        today = date.today()
        # Should be roughly 28-31 days ahead
        assert result.month != today.month or result.year != today.year

    def test_iso_date(self) -> None:
        assert parse_date("2026-03-15") == date(2026, 3, 15)

    def test_us_date(self) -> None:
        assert parse_date("03/15/2026") == date(2026, 3, 15)


# ── parse_datetime ─────────────────────────────────────────────────


class TestParseDatetime:
    """Tests for datetime parsing."""

    def test_iso_with_timezone(self) -> None:
        dt = parse_datetime("2026-03-02T15:00:00+05:30")
        assert dt.tzinfo is not None
        assert dt.hour == 15

    def test_naive_gets_local_tz(self) -> None:
        dt = parse_datetime("2026-03-02 15:00:00")
        assert dt.tzinfo is not None
        # Should be local timezone, not UTC
        # We can verify it's tz-aware without asserting specific tz
        assert dt.utcoffset() is not None

    def test_iso_z_suffix(self) -> None:
        dt = parse_datetime("2026-03-02T10:00:00Z")
        assert dt.tzinfo is not None


# ── format_time ────────────────────────────────────────────────────


class TestFormatTime:
    """Tests for time formatting."""

    def test_military(self) -> None:
        dt = datetime(2026, 3, 2, 14, 30, tzinfo=timezone.utc)
        assert format_time(dt, military=True) == "14:30"

    def test_military_midnight(self) -> None:
        dt = datetime(2026, 3, 2, 0, 0, tzinfo=timezone.utc)
        assert format_time(dt, military=True) == "00:00"

    def test_ampm(self) -> None:
        dt = datetime(2026, 3, 2, 14, 30, tzinfo=timezone.utc)
        result = format_time(dt, military=False)
        assert "2:30" in result
        assert "PM" in result

    def test_ampm_morning(self) -> None:
        dt = datetime(2026, 3, 2, 9, 5, tzinfo=timezone.utc)
        result = format_time(dt, military=False)
        assert "9:05" in result
        assert "AM" in result


# ── format_date_header ─────────────────────────────────────────────


class TestFormatDateHeader:
    def test_basic(self) -> None:
        d = date(2026, 3, 2)
        result = format_date_header(d)
        assert "Mon" in result
        assert "Mar" in result
        assert "02" in result


# ── format_full_date ───────────────────────────────────────────────


class TestFormatFullDate:
    def test_basic(self) -> None:
        d = date(2026, 3, 2)
        result = format_full_date(d)
        assert "Monday" in result
        assert "March" in result
        assert "2" in result
        assert "2026" in result

    def test_no_leading_zero(self) -> None:
        d = date(2025, 3, 2)
        result = format_full_date(d)
        # Day should be "2" not "02" — check after the month name
        assert "March 2," in result


# ── format_relative_date ───────────────────────────────────────────


class TestFormatRelativeDate:
    def test_today(self) -> None:
        assert format_relative_date(date.today()) == "today"

    def test_tomorrow(self) -> None:
        assert format_relative_date(date.today() + timedelta(days=1)) == "tmrw"

    def test_yesterday(self) -> None:
        assert format_relative_date(date.today() - timedelta(days=1)) == "yday"

    def test_far_future(self) -> None:
        d = date.today() + timedelta(days=30)
        result = format_relative_date(d)
        # Should fall back to date header format
        assert result != "today"
        assert result != "tmrw"


# ── format_duration ────────────────────────────────────────────────


class TestFormatDuration:
    @pytest.mark.parametrize(
        "minutes, expected",
        [
            (30, "30m"),
            (60, "1h"),
            (90, "1h30m"),
            (120, "2h"),
            (0, "0m"),
            (5, "5m"),
        ],
    )
    def test_durations(self, minutes: int, expected: str) -> None:
        assert format_duration(minutes) == expected


# ── rfc3339 helpers ────────────────────────────────────────────────


class TestRfc3339:
    def test_datetime(self) -> None:
        dt = datetime(2026, 3, 2, 15, 0, 0, tzinfo=timezone.utc)
        result = rfc3339(dt)
        assert "2026-03-02" in result
        assert "15:00" in result

    def test_date(self) -> None:
        d = date(2026, 3, 2)
        assert rfc3339_date(d) == "2026-03-02"


# ── event helpers ──────────────────────────────────────────────────


class TestEventHelpers:
    def test_event_duration_minutes(self) -> None:
        start = datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 2, 11, 30, tzinfo=timezone.utc)
        assert event_duration_minutes(start, end) == 90

    def test_is_all_day_true(self) -> None:
        event = {"start": {"date": "2026-03-02"}, "end": {"date": "2026-03-03"}}
        assert is_all_day(event) is True

    def test_is_all_day_false(self) -> None:
        event = {"start": {"dateTime": "2026-03-02T10:00:00Z"}}
        assert is_all_day(event) is False

    def test_is_all_day_missing_start(self) -> None:
        assert is_all_day({}) is False

    def test_parse_event_time_datetime(self) -> None:
        event = {"start": {"dateTime": "2026-03-02T10:00:00+00:00"}}
        result = parse_event_time(event, "start")
        assert isinstance(result, datetime)

    def test_parse_event_time_date(self) -> None:
        event = {"start": {"date": "2026-03-02"}}
        result = parse_event_time(event, "start")
        assert isinstance(result, date)
        assert not isinstance(result, datetime)

    def test_parse_event_time_missing_raises(self) -> None:
        with pytest.raises(ValueError, match="missing"):
            parse_event_time({}, "start")

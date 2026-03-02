"""Date/time parsing and formatting utilities."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta

if TYPE_CHECKING:
    pass

# ── Natural language shortcuts ────────────────────────────────────

_RELATIVE_PATTERNS: dict[str, int] = {
    "today": 0,
    "tod": 0,
    "tomorrow": 1,
    "tmrw": 1,
    "tom": 1,
    "yesterday": -1,
    "yday": -1,
}

_WEEKDAYS = {
    "mon": 0, "monday": 0,
    "tue": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}

_RELATIVE_DELTA_RE = re.compile(
    r"^(\d+)\s*(d|day|days|w|week|weeks|m|month|months)$", re.IGNORECASE
)


def parse_date(text: str) -> date:
    """Parse a date string with natural language support.

    Supports:
    - ``today``, ``tomorrow``, ``yesterday`` (and aliases)
    - Weekday names (``mon``, ``friday``) → next occurrence
    - Relative deltas: ``3d``, ``2w``, ``1m``
    - Anything ``dateutil.parser`` can handle (ISO, US, EU)
    """
    lowered = text.strip().lower()

    # Relative words
    if lowered in _RELATIVE_PATTERNS:
        return date.today() + timedelta(days=_RELATIVE_PATTERNS[lowered])

    # Weekday names → next occurrence
    if lowered in _WEEKDAYS:
        target_wd = _WEEKDAYS[lowered]
        today = date.today()
        diff = (target_wd - today.weekday()) % 7
        if diff == 0:
            diff = 7  # next week if today is that day
        return today + timedelta(days=diff)

    # Relative delta (3d, 2w, 1m)
    m = _RELATIVE_DELTA_RE.match(lowered)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        today = date.today()
        if unit.startswith("d"):
            return today + timedelta(days=n)
        if unit.startswith("w"):
            return today + timedelta(weeks=n)
        if unit.startswith("m"):
            return today + relativedelta(months=n)

    # dateutil fallback
    return dateutil_parser.parse(text).date()


def parse_datetime(text: str) -> datetime:
    """Parse a datetime string, returning a timezone-aware datetime.

    Naive datetimes are assumed to represent local time.
    """
    dt = dateutil_parser.parse(text)
    if dt.tzinfo is None:
        dt = dt.astimezone()  # assume local time
    return dt


# ── Formatting helpers ────────────────────────────────────────────


def format_time(dt: datetime, *, military: bool = True) -> str:
    """Format a datetime's time component."""
    if military:
        return dt.strftime("%H:%M")
    return dt.strftime("%-I:%M %p")


def format_date_header(d: date) -> str:
    """Format a date for display as a section header.

    Example: ``Mon Mar 02``
    """
    return d.strftime("%a %b %d")


def format_full_date(d: date) -> str:
    """Full date for the today banner.

    Example: ``Monday, March 2, 2026``
    """
    return d.strftime("%A, %B %-d, %Y")


def format_relative_date(d: date) -> str:
    """Format date relative to today if close, else absolute.

    Returns: ``today``, ``yesterday``, ``tomorrow``, ``Mon Mar 02``.
    """
    delta = (d - date.today()).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "tmrw"
    if delta == -1:
        return "yday"
    return format_date_header(d)


def format_duration(minutes: int) -> str:
    """Human-friendly duration string.

    Examples: ``30m``, ``1h``, ``1h30m``
    """
    if minutes < 60:
        return f"{minutes}m"
    hours, mins = divmod(minutes, 60)
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h{mins}m"


def rfc3339(dt: datetime) -> str:
    """Format a datetime as RFC 3339 for the Google API."""
    return dt.isoformat()


def rfc3339_date(d: date) -> str:
    """Format a date as an ISO date string for the Google API."""
    return d.isoformat()


def event_duration_minutes(start: datetime, end: datetime) -> int:
    """Compute event duration in minutes."""
    return int((end - start).total_seconds() / 60)


def is_all_day(event: dict) -> bool:
    """True if the event is an all-day event (date vs dateTime)."""
    return "date" in event.get("start", {})


def parse_event_time(event: dict, key: str = "start") -> datetime | date:
    """Parse the start or end time from an event dict.

    Returns a date for all-day events, datetime otherwise.
    """
    info = event.get(key, {})
    if "dateTime" in info:
        return parse_datetime(info["dateTime"])
    if "date" in info:
        return date.fromisoformat(info["date"])
    raise ValueError(f"Event missing {key}.dateTime or {key}.date")

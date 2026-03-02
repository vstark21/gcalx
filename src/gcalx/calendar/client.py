"""Thin wrapper around the Google Calendar API v3."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from gcalx.shared.cache import Cache, TTL_CAL_LIST, TTL_EVENTS
from gcalx.shared.dates import rfc3339, rfc3339_date


class CalendarClient:
    """Google Calendar API helper with cache integration."""

    def __init__(self, service: Any, cache: Cache) -> None:
        self._svc = service
        self._cache = cache

    # ── Calendar list ──────────────────────────────────────────────

    def list_calendars(self, *, refresh: bool = False) -> list[dict]:
        """Return all visible calendars.

        Cached for 24 h unless *refresh* is set.
        """
        key = "cal:list"
        if not refresh:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

        items: list[dict] = []
        page_token: str | None = None
        while True:
            resp = (
                self._svc.calendarList()
                .list(pageToken=page_token)
                .execute()
            )
            items.extend(resp.get("items", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        self._cache.set(key, items, TTL_CAL_LIST)
        return items

    def _resolve_calendar_id(self, name: str) -> str:
        """Resolve a calendar *name* to its ID.

        If *name* looks like a calendar ID already (contains ``@``),
        return it as-is.  Otherwise search the calendar list for a
        case-insensitive summary match.
        """
        if "@" in name or name == "primary":
            return name
        cals = self.list_calendars()
        for cal in cals:
            if cal.get("summary", "").lower() == name.lower():
                return cal["id"]
        return name  # fall through — let the API error if invalid

    # ── Events ─────────────────────────────────────────────────────

    def list_events(
        self,
        *,
        calendar_id: str = "primary",
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        query: str | None = None,
        max_results: int = 250,
        refresh: bool = False,
    ) -> list[dict]:
        """Fetch events in a time window.

        Results are cached for 5 min keyed on the query parameters.
        """
        calendar_id = self._resolve_calendar_id(calendar_id)

        if time_min is None:
            time_min = datetime.now(timezone.utc)
        if time_max is None:
            time_max = time_min + timedelta(days=5)

        min_str = rfc3339(time_min)
        max_str = rfc3339(time_max)
        q_part = query or ""
        cache_key = f"events:{calendar_id}:{min_str}:{max_str}:{q_part}"

        if not refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        items: list[dict] = []
        page_token: str | None = None
        kwargs: dict[str, Any] = {
            "calendarId": calendar_id,
            "timeMin": min_str,
            "timeMax": max_str,
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": max_results,
        }
        if query:
            kwargs["q"] = query

        while True:
            if page_token:
                kwargs["pageToken"] = page_token
            resp = self._svc.events().list(**kwargs).execute()
            items.extend(resp.get("items", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        self._cache.set(cache_key, items, TTL_EVENTS)
        return items

    def quick_add(
        self, text: str, *, calendar_id: str = "primary"
    ) -> dict:
        """Create an event via Google's natural language parser."""
        calendar_id = self._resolve_calendar_id(calendar_id)
        event = (
            self._svc.events()
            .quickAdd(calendarId=calendar_id, text=text)
            .execute()
        )
        self._cache.invalidate("events:")
        return event

    def insert_event(
        self, body: dict, *, calendar_id: str = "primary"
    ) -> dict:
        """Insert a fully formed event."""
        calendar_id = self._resolve_calendar_id(calendar_id)
        event = (
            self._svc.events()
            .insert(calendarId=calendar_id, body=body)
            .execute()
        )
        self._cache.invalidate("events:")
        return event

    def delete_event(
        self, event_id: str, *, calendar_id: str = "primary"
    ) -> None:
        """Delete an event by ID."""
        calendar_id = self._resolve_calendar_id(calendar_id)
        self._svc.events().delete(
            calendarId=calendar_id, eventId=event_id
        ).execute()
        self._cache.invalidate("events:")

    def patch_event(
        self,
        event_id: str,
        body: dict,
        *,
        calendar_id: str = "primary",
    ) -> dict:
        """Patch (partial update) an event."""
        calendar_id = self._resolve_calendar_id(calendar_id)
        event = (
            self._svc.events()
            .patch(calendarId=calendar_id, eventId=event_id, body=body)
            .execute()
        )
        self._cache.invalidate("events:")
        return event

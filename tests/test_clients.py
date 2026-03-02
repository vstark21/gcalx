"""Tests for gcalx.calendar.client and gcalx.tasks.client."""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gcalx.shared.cache import Cache


# ── Helpers ────────────────────────────────────────────────────────

@pytest.fixture()
def cache(tmp_path: Path) -> Cache:
    return Cache(tmp_path / "test.db")


def _paginated_response(items: list[dict], next_token: str | None = None) -> dict:
    resp: dict = {"items": items}
    if next_token:
        resp["nextPageToken"] = next_token
    return resp


# ════════════════════════════════════════════════════════════════════
# CalendarClient
# ════════════════════════════════════════════════════════════════════

class TestCalendarClient:
    """Tests for CalendarClient using a mocked Google Calendar service."""

    @pytest.fixture()
    def svc(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture()
    def client(self, svc: MagicMock, cache: Cache):
        from gcalx.calendar.client import CalendarClient
        return CalendarClient(svc, cache)

    # ── list_calendars ─────────────────────────────────────────────

    def test_list_calendars_single_page(self, client, svc) -> None:
        cals = [{"id": "a@g", "summary": "Work"}]
        svc.calendarList().list().execute.return_value = _paginated_response(cals)
        result = client.list_calendars(refresh=True)
        assert result == cals

    def test_list_calendars_cached(self, client, svc, cache) -> None:
        cals = [{"id": "a@g", "summary": "Work"}]
        # Seed cache
        cache.set("cal:list", cals, ttl=300)
        result = client.list_calendars()
        assert result == cals
        # Service should NOT have been called for the second fetch
        svc.calendarList().list().execute.assert_not_called

    def test_list_calendars_pagination(self, client, svc) -> None:
        page1 = _paginated_response([{"id": "1"}], next_token="tok2")
        page2 = _paginated_response([{"id": "2"}])
        svc.calendarList().list().execute.side_effect = [page1, page2]
        result = client.list_calendars(refresh=True)
        assert len(result) == 2

    # ── _resolve_calendar_id ───────────────────────────────────────

    def test_resolve_email_passthrough(self, client) -> None:
        assert client._resolve_calendar_id("foo@bar.com") == "foo@bar.com"

    def test_resolve_primary_passthrough(self, client) -> None:
        assert client._resolve_calendar_id("primary") == "primary"

    def test_resolve_by_summary(self, client, svc) -> None:
        cals = [{"id": "x@g", "summary": "Personal"}]
        svc.calendarList().list().execute.return_value = _paginated_response(cals)
        assert client._resolve_calendar_id("personal") == "x@g"

    def test_resolve_unknown_returns_raw(self, client, svc) -> None:
        svc.calendarList().list().execute.return_value = _paginated_response([])
        assert client._resolve_calendar_id("nope") == "nope"

    # ── list_events ────────────────────────────────────────────────

    def test_list_events_basic(self, client, svc) -> None:
        events = [{"id": "e1", "summary": "Standup"}]
        svc.calendarList().list().execute.return_value = _paginated_response([])
        svc.events().list().execute.return_value = _paginated_response(events)

        from datetime import datetime, timezone
        result = client.list_events(
            time_min=datetime(2025, 1, 1, tzinfo=timezone.utc),
            time_max=datetime(2025, 1, 2, tzinfo=timezone.utc),
            refresh=True,
        )
        assert result == events

    # ── quick_add ──────────────────────────────────────────────────

    def test_quick_add_invalidates_cache(self, client, svc, cache) -> None:
        cache.set("events:primary:x:y:z", [{"id": "old"}], ttl=300)
        svc.events().quickAdd().execute.return_value = {"id": "new"}
        result = client.quick_add("Lunch tomorrow at noon")
        assert result["id"] == "new"
        assert cache.get("events:primary:x:y:z") is None

    # ── insert_event ───────────────────────────────────────────────

    def test_insert_event(self, client, svc) -> None:
        body = {"summary": "Party", "start": {}, "end": {}}
        svc.events().insert().execute.return_value = {"id": "ev1"}
        result = client.insert_event(body)
        assert result["id"] == "ev1"

    # ── delete_event ───────────────────────────────────────────────

    def test_delete_event(self, client, svc) -> None:
        svc.events().delete().execute.return_value = None
        client.delete_event("ev1")  # should not raise

    # ── patch_event ────────────────────────────────────────────────

    def test_patch_event(self, client, svc) -> None:
        svc.events().patch().execute.return_value = {"id": "ev1", "summary": "Updated"}
        result = client.patch_event("ev1", {"summary": "Updated"})
        assert result["summary"] == "Updated"


# ════════════════════════════════════════════════════════════════════
# TasksClient
# ════════════════════════════════════════════════════════════════════

class TestTasksClient:
    """Tests for TasksClient using a mocked Google Tasks service."""

    @pytest.fixture()
    def svc(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture()
    def client(self, svc: MagicMock, cache: Cache):
        from gcalx.tasks.client import TasksClient
        return TasksClient(svc, cache)

    # ── list_task_lists ────────────────────────────────────────────

    def test_list_task_lists(self, client, svc) -> None:
        lists = [{"id": "L1", "title": "My Tasks"}]
        svc.tasklists().list().execute.return_value = _paginated_response(lists)
        assert client.list_task_lists(refresh=True) == lists

    def test_list_task_lists_cached(self, client, svc, cache) -> None:
        lists = [{"id": "L1"}]
        cache.set("tasklists", lists, ttl=300)
        assert client.list_task_lists() == lists

    # ── resolve_list_id ────────────────────────────────────────────

    def test_resolve_default_passthrough(self, client) -> None:
        assert client.resolve_list_id("@default") == "@default"

    def test_resolve_by_title(self, client, svc) -> None:
        svc.tasklists().list().execute.return_value = _paginated_response(
            [{"id": "L1", "title": "Work"}]
        )
        assert client.resolve_list_id("work") == "L1"

    def test_resolve_fallback_warns(self, client, svc) -> None:
        svc.tasklists().list().execute.return_value = _paginated_response(
            [{"id": "L1", "title": "Inbox"}]
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = client.resolve_list_id("nonexistent")
        assert result == "L1"
        assert len(w) == 1
        assert "not found" in str(w[0].message)

    def test_resolve_no_lists(self, client, svc) -> None:
        svc.tasklists().list().execute.return_value = _paginated_response([])
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            assert client.resolve_list_id("any") == "@default"

    # ── list_tasks ─────────────────────────────────────────────────

    def test_list_tasks(self, client, svc) -> None:
        tasks = [{"id": "t1", "title": "Buy milk"}]
        svc.tasks().list().execute.return_value = _paginated_response(tasks)
        assert client.list_tasks("L1", refresh=True) == tasks

    # ── get_task ───────────────────────────────────────────────────

    def test_get_task(self, client, svc) -> None:
        svc.tasks().get().execute.return_value = {"id": "t1"}
        assert client.get_task("L1", "t1")["id"] == "t1"

    # ── insert_task ────────────────────────────────────────────────

    def test_insert_task(self, client, svc) -> None:
        svc.tasks().insert().execute.return_value = {"id": "t2", "title": "New"}
        result = client.insert_task("L1", {"title": "New"})
        assert result["id"] == "t2"

    def test_insert_task_with_parent(self, client, svc) -> None:
        svc.tasks().insert().execute.return_value = {"id": "t3"}
        result = client.insert_task("L1", {"title": "Sub"}, parent="t1")
        assert result["id"] == "t3"

    # ── patch / delete / complete / uncomplete ─────────────────────

    def test_complete_task(self, client, svc) -> None:
        svc.tasks().patch().execute.return_value = {"id": "t1", "status": "completed"}
        result = client.complete_task("L1", "t1")
        assert result["status"] == "completed"

    def test_uncomplete_task(self, client, svc) -> None:
        svc.tasks().patch().execute.return_value = {"id": "t1", "status": "needsAction"}
        result = client.uncomplete_task("L1", "t1")
        assert result["status"] == "needsAction"

    def test_delete_task(self, client, svc) -> None:
        svc.tasks().delete().execute.return_value = None
        client.delete_task("L1", "t1")  # should not raise

    # ── move_task ──────────────────────────────────────────────────

    def test_move_task(self, client, svc) -> None:
        svc.tasks().move().execute.return_value = {"id": "t1"}
        result = client.move_task("L1", "t1", previous="t0")
        assert result["id"] == "t1"

    # ── clear_completed ────────────────────────────────────────────

    def test_clear_completed(self, client, svc, cache) -> None:
        cache.set("tasks:L1:True", [{"id": "t1"}], ttl=60)
        svc.tasks().clear().execute.return_value = None
        client.clear_completed("L1")
        assert cache.get("tasks:L1:True") is None

    # ── resolve_task ───────────────────────────────────────────────

    def test_resolve_by_id(self, client, svc) -> None:
        tasks = [{"id": "abc123", "title": "Do stuff"}]
        svc.tasks().list().execute.return_value = _paginated_response(tasks)
        assert client.resolve_task("abc123", "L1") == tasks[0]

    def test_resolve_by_title_substring(self, client, svc) -> None:
        tasks = [{"id": "t1", "title": "Buy groceries"}]
        svc.tasks().list().execute.return_value = _paginated_response(tasks)
        assert client.resolve_task("grocer", "L1") == tasks[0]

    def test_resolve_by_position(self, client, svc, cache) -> None:
        tasks = [{"id": "t1", "title": "First"}, {"id": "t2", "title": "Second"}]
        svc.tasks().list().execute.return_value = _paginated_response(tasks)
        cache.save_task_positions("L1", [{"id": "t1", "title": "First"}, {"id": "t2", "title": "Second"}])
        result = client.resolve_task("2", "L1")
        assert result is not None
        assert result["id"] == "t2"

    def test_resolve_not_found(self, client, svc) -> None:
        svc.tasks().list().execute.return_value = _paginated_response([])
        assert client.resolve_task("nope", "L1") is None

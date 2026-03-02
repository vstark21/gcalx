"""Tests for gcalx.calendar.formatters and gcalx.tasks.formatters."""

from __future__ import annotations

from datetime import date, datetime, timezone
from io import StringIO

from rich.console import Console

from gcalx.shared.printer import build_theme


# ── Helpers ────────────────────────────────────────────────────────


def _console() -> Console:
    """Rich Console that writes to a StringIO buffer with Dusk theme."""
    return Console(file=StringIO(), theme=build_theme(), color_system=None, width=120)


def _output(console: Console) -> str:
    """Return everything printed to the console buffer."""
    assert isinstance(console.file, StringIO)
    return console.file.getvalue()


# ════════════════════════════════════════════════════════════════════
# Calendar formatters
# ════════════════════════════════════════════════════════════════════


class TestFormatCalendarList:
    def test_basic_table(self) -> None:
        from gcalx.calendar.formatters import format_calendar_list

        cals = [
            {"summary": "Work", "accessRole": "owner"},
            {"summary": "Personal", "accessRole": "reader"},
        ]
        con = _console()
        format_calendar_list(cals, con)
        out = _output(con)
        assert "Work" in out
        assert "Personal" in out
        assert "owner" in out
        assert "reader" in out

    def test_empty_list(self) -> None:
        from gcalx.calendar.formatters import format_calendar_list

        con = _console()
        format_calendar_list([], con)
        out = _output(con)
        # Table headers exist but no data rows — shouldn't crash
        assert "Calendar" in out or out.strip() != ""


class TestFormatAgenda:
    def _make_event(
        self,
        summary: str,
        start: str | dict,
        end: str | dict | None = None,
        **extra,
    ) -> dict:
        """Helper to construct a minimal event dict."""
        ev: dict = {"summary": summary}
        if isinstance(start, str):
            ev["start"] = {"dateTime": start}
        else:
            ev["start"] = start
        if end is not None:
            if isinstance(end, str):
                ev["end"] = {"dateTime": end}
            else:
                ev["end"] = end
        ev.update(extra)
        return ev

    def test_no_events(self) -> None:
        from gcalx.calendar.formatters import format_agenda

        con = _console()
        format_agenda([], con)
        assert "No events" in _output(con)

    def test_timed_event(self) -> None:
        from gcalx.calendar.formatters import format_agenda

        ev = self._make_event(
            "Standup",
            "2025-06-10T09:00:00+00:00",
            "2025-06-10T09:30:00+00:00",
        )
        con = _console()
        format_agenda([ev], con, military=True)
        out = _output(con)
        assert "Standup" in out
        assert "30m" in out

    def test_all_day_event(self) -> None:
        from gcalx.calendar.formatters import format_agenda

        ev = {
            "summary": "Holiday",
            "start": {"date": "2025-06-10"},
            "end": {"date": "2025-06-11"},
        }
        con = _console()
        format_agenda([ev], con)
        out = _output(con)
        assert "Holiday" in out
        assert "all day" in out

    def test_declined_event(self) -> None:
        from gcalx.calendar.formatters import format_agenda

        ev = self._make_event(
            "Boring meeting",
            "2025-06-10T14:00:00+00:00",
            "2025-06-10T15:00:00+00:00",
            attendees=[{"self": True, "responseStatus": "declined"}],
        )
        con = _console()
        format_agenda([ev], con)
        out = _output(con)
        assert "Boring meeting" in out

    def test_location_shown(self) -> None:
        from gcalx.calendar.formatters import format_agenda

        ev = self._make_event(
            "Lunch",
            "2025-06-10T12:00:00+00:00",
            "2025-06-10T13:00:00+00:00",
            location="Café Downtown",
        )
        con = _console()
        format_agenda([ev], con, show_location=True)
        out = _output(con)
        assert "Café Downtown" in out

    def test_description_hidden_by_default(self) -> None:
        from gcalx.calendar.formatters import format_agenda

        ev = self._make_event(
            "Report",
            "2025-06-10T10:00:00+00:00",
            "2025-06-10T11:00:00+00:00",
            description="Some long notes",
        )
        con = _console()
        format_agenda([ev], con, show_description=False)
        assert "Some long notes" not in _output(con)

    def test_description_shown(self) -> None:
        from gcalx.calendar.formatters import format_agenda

        ev = self._make_event(
            "Report",
            "2025-06-10T10:00:00+00:00",
            "2025-06-10T11:00:00+00:00",
            description="Quarterly numbers",
        )
        con = _console()
        format_agenda([ev], con, show_description=True)
        assert "Quarterly numbers" in _output(con)

    def test_date_grouping(self) -> None:
        from gcalx.calendar.formatters import format_agenda

        ev1 = self._make_event("A", "2025-06-10T09:00:00+00:00", "2025-06-10T10:00:00+00:00")
        ev2 = self._make_event("B", "2025-06-11T09:00:00+00:00", "2025-06-11T10:00:00+00:00")
        con = _console()
        format_agenda([ev1, ev2], con)
        out = _output(con)
        assert "A" in out and "B" in out


class TestFormatEventShort:
    def test_timed(self) -> None:
        from gcalx.calendar.formatters import format_event_short

        ev = {
            "summary": "Quick call",
            "start": {"dateTime": "2025-06-10T15:30:00+00:00"},
            "end": {"dateTime": "2025-06-10T16:00:00+00:00"},
        }
        result = format_event_short(ev, military=True)
        assert "Quick call" in result

    def test_all_day(self) -> None:
        from gcalx.calendar.formatters import format_event_short

        ev = {
            "summary": "Vacation",
            "start": {"date": "2025-06-10"},
            "end": {"date": "2025-06-12"},
        }
        result = format_event_short(ev)
        assert "all day" in result
        assert "Vacation" in result


# ════════════════════════════════════════════════════════════════════
# Tasks formatters
# ════════════════════════════════════════════════════════════════════


class TestFormatTaskLists:
    def test_basic_table(self) -> None:
        from gcalx.tasks.formatters import format_task_lists

        lists = [
            {"id": "L1", "title": "My Tasks", "updated": "2025-06-01T00:00:00Z"},
            {"id": "L2", "title": "Work"},
        ]
        con = _console()
        format_task_lists(lists, con)
        out = _output(con)
        assert "My Tasks" in out
        assert "Work" in out


class TestFormatTaskList:
    def _task(
        self,
        tid: str,
        title: str,
        status: str = "needsAction",
        **extra,
    ) -> dict:
        t: dict = {"id": tid, "title": title, "status": status}
        t.update(extra)
        return t

    def test_pending_tasks(self) -> None:
        from gcalx.tasks.formatters import format_task_list

        tasks = [self._task("t1", "Buy milk"), self._task("t2", "Clean room")]
        con = _console()
        format_task_list(tasks, "Inbox", con)
        out = _output(con)
        assert "Buy milk" in out
        assert "Clean room" in out
        assert "Inbox" in out
        assert "2 tasks" in out

    def test_completed_task(self) -> None:
        from gcalx.tasks.formatters import format_task_list

        t = self._task(
            "t1", "Done thing",
            status="completed",
            completed="2025-06-01T00:00:00Z",
        )
        con = _console()
        format_task_list([t], "List", con)
        out = _output(con)
        assert "Done thing" in out
        assert "✓" in out

    def test_overdue_task(self) -> None:
        from gcalx.tasks.formatters import format_task_list

        yesterday = date.today().isoformat()  # close enough for rendering
        t = self._task("t1", "Late task", due="2020-01-01T00:00:00Z")
        con = _console()
        format_task_list([t], "List", con)
        out = _output(con)
        assert "Late task" in out

    def test_subtasks(self) -> None:
        from gcalx.tasks.formatters import format_task_list

        parent = self._task("p1", "Parent")
        child = self._task("c1", "Child", parent="p1")
        con = _console()
        format_task_list([parent, child], "List", con)
        out = _output(con)
        assert "Parent" in out
        assert "Child" in out

    def test_show_notes(self) -> None:
        from gcalx.tasks.formatters import format_task_list

        t = self._task("t1", "Item", notes="Some extra info")
        con = _console()
        format_task_list([t], "List", con, show_notes=True)
        out = _output(con)
        assert "Some extra info" in out

    def test_show_id(self) -> None:
        from gcalx.tasks.formatters import format_task_list

        t = self._task("abc123", "Visible ID")
        con = _console()
        format_task_list([t], "List", con, show_id=True)
        out = _output(con)
        assert "abc123" in out

    def test_due_date_shown(self) -> None:
        from gcalx.tasks.formatters import format_task_list

        tomorrow = date.today().isoformat()
        t = self._task("t1", "With due", due="2030-01-01T00:00:00Z")
        con = _console()
        format_task_list([t], "List", con)
        out = _output(con)
        assert "due:" in out

"""Rich formatters for calendar output."""

from __future__ import annotations

from datetime import date, datetime

from rich.console import Console
from rich.table import Table
from rich.text import Text

from gcalx.shared.dates import (
    event_duration_minutes,
    format_date_header,
    format_duration,
    format_time,
    is_all_day,
    parse_event_time,
)
from gcalx.shared.utils import truncate


def format_calendar_list(calendars: list[dict], console: Console) -> None:
    """Print a table of calendars with access roles."""
    table = Table(show_header=True, header_style="header", box=None, pad_edge=False)
    table.add_column("Calendar", style="cal.title", min_width=30)
    table.add_column("Access", justify="right")

    role_styles = {
        "owner": "cal.owner",
        "writer": "cal.writer",
        "reader": "cal.reader",
        "freeBusyReader": "cal.freebusy",
    }

    for cal in calendars:
        summary = cal.get("summary", cal.get("id", "?"))
        role = cal.get("accessRole", "reader")
        style = role_styles.get(role, "muted")
        table.add_row(summary, Text(role, style=style))

    console.print(table)


def format_agenda(
    events: list[dict],
    console: Console,
    *,
    military: bool = True,
    show_location: bool = True,
    show_description: bool = False,
) -> None:
    """Print an agenda view grouped by date."""
    if not events:
        console.print("[muted]No events found.[/muted]")
        return

    current_date: date | None = None
    now = datetime.now().astimezone()

    for event in events:
        all_day = is_all_day(event)
        start = parse_event_time(event, "start")

        # Determine the date for grouping
        if isinstance(start, datetime):
            ev_date = start.date()
        else:
            ev_date = start

        # Date header
        if ev_date != current_date:
            if current_date is not None:
                console.print(" [cal.border]┃[/cal.border]")
            console.print(
                f" [cal.border]┃[/cal.border] [cal.date]{format_date_header(ev_date)}[/cal.date]"
            )
            current_date = ev_date

        # Now marker
        if isinstance(start, datetime) and current_date == now.date():
            if start > now and (not hasattr(format_agenda, "_now_shown") or format_agenda._now_shown != current_date):  # type: ignore[attr-defined]
                console.print(
                    " [cal.border]┃[/cal.border]   [cal.now]▸ NOW ─────────────────────────[/cal.now]"
                )
                format_agenda._now_shown = current_date  # type: ignore[attr-defined]

        title = event.get("summary", "(No title)")

        # Check if declined
        attendees = event.get("attendees", [])
        declined = any(
            a.get("self") and a.get("responseStatus") == "declined"
            for a in attendees
        )

        if all_day:
            line = f" [cal.border]┃[/cal.border]   [cal.allday]▓▓▓▓▓  {title}[/cal.allday]  [muted]all day[/muted]"
        elif declined:
            time_str = format_time(start, military=military) if isinstance(start, datetime) else ""
            line = f" [cal.border]┃[/cal.border]   [cal.declined]{time_str}  {title}[/cal.declined]"
        else:
            time_str = format_time(start, military=military) if isinstance(start, datetime) else ""
            # Duration
            dur_str = ""
            try:
                end = parse_event_time(event, "end")
                if isinstance(start, datetime) and isinstance(end, datetime):
                    mins = event_duration_minutes(start, end)
                    dur_str = format_duration(mins)
            except (ValueError, KeyError):
                pass

            line = (
                f" [cal.border]┃[/cal.border]   "
                f"[cal.time]{time_str}[/cal.time]  "
                f"[cal.title]{truncate(title, 40)}[/cal.title]"
            )
            if dur_str:
                line += f"  [muted]{dur_str}[/muted]"

        console.print(line)

        # Location
        if show_location and event.get("location"):
            loc = truncate(event["location"], 50)
            console.print(
                f" [cal.border]┃[/cal.border]          [cal.location]📍 {loc}[/cal.location]"
            )

        # Description
        if show_description and event.get("description"):
            desc = truncate(event["description"], 70)
            console.print(
                f" [cal.border]┃[/cal.border]          [cal.description]{desc}[/cal.description]"
            )

    console.print(" [cal.border]┃[/cal.border]")


def format_event_short(event: dict, *, military: bool = True) -> str:
    """One-line summary of an event for pickers and confirmations."""
    title = event.get("summary", "(No title)")
    if is_all_day(event):
        start = parse_event_time(event, "start")
        return f"{start}  {title} (all day)"
    start = parse_event_time(event, "start")
    if isinstance(start, datetime):
        return f"{format_time(start, military=military)}  {title}"
    return f"{start}  {title}"

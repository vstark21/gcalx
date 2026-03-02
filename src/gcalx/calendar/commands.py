"""Typer commands for `gcalx cal`."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import typer
from rich.prompt import Confirm

from gcalx.auth import build_calendar_service
from gcalx.calendar.client import CalendarClient
from gcalx.calendar.formatters import format_agenda, format_calendar_list, format_event_short
from gcalx.shared.dates import parse_date, parse_datetime, rfc3339, rfc3339_date
from gcalx.shared.deps import get_deps

app = typer.Typer(name="cal", help="Google Calendar commands.")


def _get_deps(refresh: bool = False):
    """Bootstrap config → creds → service → client."""
    return get_deps(
        build_service=build_calendar_service,
        build_client=CalendarClient,
        refresh=refresh,
    )


# ── cal list ───────────────────────────────────────────────────────


@app.command("list")
def cal_list(
    refresh: Annotated[bool, typer.Option("--refresh", help="Bypass cache.")] = False,
) -> None:
    """List available calendars."""
    _cfg, client, _cache, console = _get_deps(refresh)
    calendars = client.list_calendars(refresh=refresh)
    format_calendar_list(calendars, console)


# ── cal agenda ─────────────────────────────────────────────────────


@app.command()
def agenda(
    start: Annotated[
        Optional[str], typer.Argument(help="Start date (default: now).")
    ] = None,
    end: Annotated[
        Optional[str], typer.Argument(help="End date (default: start + 5 days).")
    ] = None,
    calendar: Annotated[
        Optional[str], typer.Option("-c", "--calendar", help="Calendar name or ID.")
    ] = None,
    military: Annotated[
        Optional[bool], typer.Option("--military/--ampm", help="24h vs 12h time.")
    ] = None,
    refresh: Annotated[
        bool, typer.Option("--refresh", help="Bypass cache.")
    ] = False,
) -> None:
    """Show agenda for a time period (default: next 5 days)."""
    cfg, client, _cache, console = _get_deps(refresh)

    now = datetime.now(timezone.utc)
    time_min = parse_datetime(start) if start else now
    time_max = parse_datetime(end) if end else time_min + timedelta(days=5)

    cal_id = calendar or cfg.calendar.default_calendar
    events = client.list_events(
        calendar_id=cal_id,
        time_min=time_min,
        time_max=time_max,
        refresh=refresh,
    )

    use_military = military if military is not None else cfg.calendar.military
    format_agenda(events, console, military=use_military)


# ── cal quick ──────────────────────────────────────────────────────


@app.command()
def quick(
    text: Annotated[str, typer.Argument(help="Natural language event description.")],
    calendar: Annotated[
        Optional[str], typer.Option("-c", "--calendar", help="Calendar name or ID.")
    ] = None,
) -> None:
    """Quick-add an event from natural language text."""
    cfg, client, _cache, console = _get_deps()
    cal_id = calendar or cfg.calendar.default_calendar
    event = client.quick_add(text, calendar_id=cal_id)
    console.print(f"[success]Created:[/success] {format_event_short(event)}")


# ── cal add ────────────────────────────────────────────────────────


@app.command()
def add(
    title: Annotated[Optional[str], typer.Option("--title", "-t", help="Event title.")] = None,
    when: Annotated[Optional[str], typer.Option("--when", "-w", help="Start time.")] = None,
    duration: Annotated[int, typer.Option("--duration", "-d", help="Duration in minutes.")] = 60,
    end: Annotated[
        Optional[str], typer.Option("--end", help="End time (alternative to --duration).")
    ] = None,
    where: Annotated[Optional[str], typer.Option("--where", help="Location.")] = None,
    description: Annotated[Optional[str], typer.Option("--desc", help="Description.")] = None,
    who: Annotated[Optional[list[str]], typer.Option("--who", help="Attendee email.")] = None,
    allday: Annotated[bool, typer.Option("--allday", help="All-day event.")] = False,
    calendar: Annotated[Optional[str], typer.Option("-c", "--calendar", help="Calendar.")] = None,
    noprompt: Annotated[bool, typer.Option("--noprompt", help="Don't prompt.")] = False,
) -> None:
    """Add an event with full details."""
    cfg, client, _cache, console = _get_deps()

    # Interactive prompts for required fields
    if not title:
        if noprompt:
            console.print("[error]--title is required with --noprompt[/error]")
            raise typer.Exit(1)
        title = typer.prompt("Title")
    if not when:
        if noprompt:
            console.print("[error]--when is required with --noprompt[/error]")
            raise typer.Exit(1)
        when = typer.prompt("When")

    cal_id = calendar or cfg.calendar.default_calendar

    body: dict = {"summary": title}

    if allday:
        start_date = parse_date(when)
        if end:
            end_date = parse_date(end)
        else:
            end_date = start_date + timedelta(days=1)
        body["start"] = {"date": rfc3339_date(start_date)}
        body["end"] = {"date": rfc3339_date(end_date)}
    else:
        start_dt = parse_datetime(when)
        if end:
            end_dt = parse_datetime(end)
        else:
            end_dt = start_dt + timedelta(minutes=duration)
        body["start"] = {"dateTime": rfc3339(start_dt)}
        body["end"] = {"dateTime": rfc3339(end_dt)}

    if where:
        body["location"] = where
    if description:
        body["description"] = description
    if who:
        body["attendees"] = [{"email": e} for e in who]

    event = client.insert_event(body, calendar_id=cal_id)
    console.print(f"[success]Created:[/success] {format_event_short(event)}")


# ── cal search ─────────────────────────────────────────────────────


@app.command()
def search(
    text: Annotated[str, typer.Argument(help="Search text.")],
    start: Annotated[Optional[str], typer.Argument(help="Start date.")] = None,
    end: Annotated[Optional[str], typer.Argument(help="End date.")] = None,
    calendar: Annotated[Optional[str], typer.Option("-c", "--calendar")] = None,
    military: Annotated[Optional[bool], typer.Option("--military/--ampm")] = None,
    refresh: Annotated[bool, typer.Option("--refresh")] = False,
) -> None:
    """Search events by text."""
    cfg, client, _cache, console = _get_deps(refresh)

    now = datetime.now(timezone.utc)
    time_min = parse_datetime(start) if start else now
    time_max = parse_datetime(end) if end else time_min + timedelta(days=365)

    cal_id = calendar or cfg.calendar.default_calendar
    events = client.list_events(
        calendar_id=cal_id,
        time_min=time_min,
        time_max=time_max,
        query=text,
        refresh=refresh,
    )

    use_military = military if military is not None else cfg.calendar.military
    format_agenda(events, console, military=use_military)


# ── cal delete ─────────────────────────────────────────────────────


@app.command()
def delete(
    text: Annotated[str, typer.Argument(help="Search text to find events.")],
    start: Annotated[Optional[str], typer.Argument(help="Start date.")] = None,
    end: Annotated[Optional[str], typer.Argument(help="End date.")] = None,
    calendar: Annotated[Optional[str], typer.Option("-c", "--calendar")] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Find and delete events matching search text."""
    cfg, client, _cache, console = _get_deps()

    now = datetime.now(timezone.utc)
    time_min = parse_datetime(start) if start else now
    time_max = parse_datetime(end) if end else time_min + timedelta(days=30)

    cal_id = calendar or cfg.calendar.default_calendar
    events = client.list_events(
        calendar_id=cal_id,
        time_min=time_min,
        time_max=time_max,
        query=text,
        refresh=True,
    )

    if not events:
        console.print("[muted]No events found.[/muted]")
        return

    console.print(f"[header]Found {len(events)} event(s):[/header]")
    for i, ev in enumerate(events, 1):
        console.print(f"  {i}. {format_event_short(ev)}")

    if len(events) == 1:
        target = events[0]
    else:
        idx = typer.prompt("Delete which? (number)", type=int) - 1
        if idx < 0 or idx >= len(events):
            console.print("[error]Invalid selection.[/error]")
            raise typer.Exit(1)
        target = events[idx]

    if not yes:
        if not Confirm.ask(
            f"Delete '{target.get('summary', '?')}'?", default=False
        ):
            console.print("[muted]Cancelled.[/muted]")
            return

    client.delete_event(target["id"], calendar_id=cal_id)
    console.print(f"[success]Deleted:[/success] {target.get('summary', '?')}")

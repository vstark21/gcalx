"""gcalx CLI entry point."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Optional

import typer

from gcalx import __version__
from gcalx.calendar.commands import app as cal_app
from gcalx.tasks.commands import app as task_app

app = typer.Typer(
    name="gcalx",
    help="Google Calendar Extended — unified CLI for Google Calendar and Tasks.",
    no_args_is_help=True,
)

# ── Sub-command groups ─────────────────────────────────────────────

app.add_typer(cal_app, name="cal", help="Calendar commands.")
app.add_typer(task_app, name="task", help="Tasks commands.")


# ── Version callback ──────────────────────────────────────────────

def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"gcalx {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-V", help="Show version.", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    """Google Calendar Extended — Calendar + Tasks from the terminal."""


# ── init ───────────────────────────────────────────────────────────

@app.command()
def init() -> None:
    """Authenticate with Google and save credentials."""
    from gcalx.auth import authenticate
    from gcalx.config import load_config, save_config
    from gcalx.shared.printer import get_console

    cfg = load_config()
    console = get_console(color=cfg.display.color)

    console.print("[header]gcalx — first-time setup[/header]\n")

    # Use built-in client credentials
    from gcalx.auth import load_credentials

    existing = load_credentials(cfg.config_dir)
    if existing:
        console.print("[success]Already authenticated![/success]")
        console.print("[muted]To re-authenticate, delete the token file and run init again.[/muted]")
        console.print(f"[muted]  rm {cfg.token_path}[/muted]")
        return

    # Hard-coded OAuth client (open-source app credentials)
    client_id = cfg.auth.client_id or "REDACTED_CLIENT_ID"
    client_secret = cfg.auth.client_secret or "REDACTED_CLIENT_SECRET"

    console.print("Opening browser for Google OAuth...\n")
    authenticate(client_id, client_secret, cfg.config_dir)

    # Save config with defaults if it doesn't exist
    if not cfg.config_file.exists():
        save_config(cfg)
        console.print(f"\n[muted]Config saved to {cfg.config_file}[/muted]")

    console.print("\n[success]Setup complete![/success] Try:")
    console.print("  [link]gcalx cal agenda[/link]")
    console.print("  [link]gcalx task ls[/link]")
    console.print("  [link]gcalx today[/link]")


# ── today ──────────────────────────────────────────────────────────

@app.command()
def today(
    military: Annotated[Optional[bool], typer.Option("--military/--ampm")] = None,
    refresh: Annotated[bool, typer.Option("--refresh")] = False,
) -> None:
    """Combined view of today's events and due tasks."""
    from gcalx.auth import build_calendar_service, build_tasks_service, load_credentials
    from gcalx.calendar.client import CalendarClient
    from gcalx.calendar.formatters import format_agenda
    from gcalx.config import load_config
    from gcalx.shared.cache import Cache
    from gcalx.shared.dates import format_full_date
    from gcalx.shared.printer import get_console
    from gcalx.shared.utils import ensure_auth
    from gcalx.tasks.client import TasksClient
    from gcalx.tasks.formatters import format_task_list

    cfg = load_config()
    ensure_auth(cfg.config_dir)
    creds = load_credentials(cfg.config_dir)
    if creds is None:
        typer.echo("Failed to load credentials. Run `gcalx init`.", err=True)
        raise typer.Exit(1)

    console = get_console(
        color=cfg.display.color,
        overrides=cfg.theme.overrides or None,
    )
    cache = Cache(cfg.cache_path)
    use_military = military if military is not None else cfg.calendar.military

    d = date.today()
    console.print(f"\n [header]━━━ {format_full_date(d)} ━━━[/header]\n")

    # ── Calendar ──
    cal_svc = build_calendar_service(creds)
    cal_client = CalendarClient(cal_svc, cache)

    now = datetime.now(timezone.utc)
    day_start = datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    events = cal_client.list_events(
        calendar_id=cfg.calendar.default_calendar,
        time_min=day_start,
        time_max=day_end,
        refresh=refresh,
    )

    console.print(" [header]📅 Calendar[/header]")
    if events:
        format_agenda(events, console, military=use_military)
    else:
        console.print("   [muted]No events today.[/muted]")

    # ── Tasks ──
    task_svc = build_tasks_service(creds)
    task_client = TasksClient(task_svc, cache)
    list_id = task_client.resolve_list_id(cfg.tasks.default_list)
    tasks = task_client.list_tasks(list_id, show_completed=False, refresh=refresh)

    due_today = [
        t for t in tasks
        if t.get("due") and date.fromisoformat(t["due"][:10]) <= d
    ]
    overdue = [
        t for t in due_today
        if date.fromisoformat(t["due"][:10]) < d
    ]
    today_only = [
        t for t in due_today
        if date.fromisoformat(t["due"][:10]) == d
    ]

    if today_only:
        console.print("\n [header]☑️  Tasks Due Today[/header]")
        format_task_list(today_only, "", console)

    if overdue:
        console.print("\n [warning]⚠️  Overdue[/warning]")
        format_task_list(overdue, "", console)

    if not due_today:
        console.print("\n [header]☑️  Tasks[/header]")
        console.print("   [muted]No tasks due today.[/muted]")

    console.print()

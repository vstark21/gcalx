"""Typer commands for `gcalx task`."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

import typer
from rich.prompt import Confirm

from gcalx.auth import build_tasks_service
from gcalx.shared.dates import parse_date, rfc3339_date
from gcalx.shared.deps import get_deps
from gcalx.tasks.client import TasksClient
from gcalx.tasks.formatters import format_task_list, format_task_lists

app = typer.Typer(name="task", help="Google Tasks commands.")


def _get_deps(refresh: bool = False):
    """Bootstrap config → creds → service → client."""
    return get_deps(
        build_service=build_tasks_service,
        build_client=TasksClient,
        refresh=refresh,
    )


def _resolve_list(cfg, client: TasksClient, list_name: str | None) -> str:
    """Resolve a list name to its Google Tasks ID."""
    name = list_name or cfg.tasks.default_list
    return client.resolve_list_id(name)


# ── task lists ─────────────────────────────────────────────────────


@app.command("lists")
def task_lists(
    refresh: Annotated[bool, typer.Option("--refresh", help="Bypass cache.")] = False,
) -> None:
    """List all task lists."""
    _cfg, client, _cache, console = _get_deps(refresh)
    lists = client.list_task_lists(refresh=refresh)
    format_task_lists(lists, console)


# ── task ls ────────────────────────────────────────────────────────


@app.command("ls")
def task_ls(
    list_name: Annotated[
        Optional[str], typer.Option("-l", "--list", help="Task list name.")
    ] = None,
    all_tasks: Annotated[bool, typer.Option("-a", "--all", help="Include completed.")] = False,
    due: Annotated[Optional[str], typer.Option("--due", help="Filter by due date.")] = None,
    show_notes: Annotated[bool, typer.Option("--show-notes", help="Show task notes.")] = False,
    show_id: Annotated[bool, typer.Option("--show-id", help="Show task IDs.")] = False,
    refresh: Annotated[bool, typer.Option("--refresh", help="Bypass cache.")] = False,
) -> None:
    """List tasks in a task list."""
    cfg, client, cache, console = _get_deps(refresh)
    list_id = _resolve_list(cfg, client, list_name)
    tasks = client.list_tasks(list_id, show_completed=all_tasks, refresh=refresh)

    # Filter by due date
    if due:
        due_date = parse_date(due)
        tasks = [
            t for t in tasks
            if t.get("due") and date.fromisoformat(t["due"][:10]) <= due_date
        ]

    # Save positions for positional references
    cache.save_task_positions(
        list_id, [{"id": t["id"], "title": t.get("title", "")} for t in tasks]
    )

    list_title = list_name or cfg.tasks.default_list
    format_task_list(
        tasks, list_title, console,
        show_notes=show_notes, show_id=show_id,
    )


# ── task add ───────────────────────────────────────────────────────


@app.command()
def add(
    title: Annotated[str, typer.Argument(help="Task title.")],
    list_name: Annotated[Optional[str], typer.Option("-l", "--list", help="Task list.")] = None,
    due_date: Annotated[Optional[str], typer.Option("-d", "--due", help="Due date.")] = None,
    notes: Annotated[Optional[str], typer.Option("-n", "--notes", help="Task notes.")] = None,
    parent: Annotated[
        Optional[str], typer.Option("-p", "--parent", help="Parent task (subtask).")
    ] = None,
) -> None:
    """Add a new task."""
    cfg, client, _cache, console = _get_deps()
    list_id = _resolve_list(cfg, client, list_name)

    body: dict = {"title": title}
    if due_date:
        d = parse_date(due_date)
        body["due"] = f"{rfc3339_date(d)}T00:00:00.000Z"
    if notes:
        body["notes"] = notes

    # Resolve parent task
    parent_id: str | None = None
    if parent:
        p = client.resolve_task(parent, list_id)
        if p is None:
            console.print(f"[error]Parent task '{parent}' not found.[/error]")
            raise typer.Exit(1)
        parent_id = p["id"]

    task = client.insert_task(list_id, body, parent=parent_id)
    console.print(f"[success]Added:[/success] {task.get('title', title)}")


# ── task done ──────────────────────────────────────────────────────


@app.command()
def done(
    identifier: Annotated[str, typer.Argument(help="Task ID, title, or position number.")],
    list_name: Annotated[Optional[str], typer.Option("-l", "--list")] = None,
) -> None:
    """Mark a task as completed."""
    cfg, client, _cache, console = _get_deps()
    list_id = _resolve_list(cfg, client, list_name)

    task = client.resolve_task(identifier, list_id)
    if task is None:
        console.print(f"[error]Task '{identifier}' not found.[/error]")
        raise typer.Exit(1)

    client.complete_task(list_id, task["id"])
    console.print(f"[success]Done:[/success] {task.get('title', '?')}")


# ── task undone ────────────────────────────────────────────────────


@app.command()
def undone(
    identifier: Annotated[str, typer.Argument(help="Task ID, title, or position number.")],
    list_name: Annotated[Optional[str], typer.Option("-l", "--list")] = None,
) -> None:
    """Mark a completed task as needs action."""
    cfg, client, _cache, console = _get_deps()
    list_id = _resolve_list(cfg, client, list_name)

    task = client.resolve_task(identifier, list_id)
    if task is None:
        console.print(f"[error]Task '{identifier}' not found.[/error]")
        raise typer.Exit(1)

    client.uncomplete_task(list_id, task["id"])
    console.print(f"[success]Reopened:[/success] {task.get('title', '?')}")


# ── task edit ──────────────────────────────────────────────────────


@app.command()
def edit(
    identifier: Annotated[str, typer.Argument(help="Task ID, title, or position.")],
    title: Annotated[Optional[str], typer.Option("--title", "-t")] = None,
    due_date: Annotated[Optional[str], typer.Option("--due", "-d")] = None,
    notes_text: Annotated[Optional[str], typer.Option("--notes", "-n")] = None,
    list_name: Annotated[Optional[str], typer.Option("-l", "--list")] = None,
) -> None:
    """Edit a task's title, due date, or notes."""
    cfg, client, _cache, console = _get_deps()
    list_id = _resolve_list(cfg, client, list_name)

    task = client.resolve_task(identifier, list_id)
    if task is None:
        console.print(f"[error]Task '{identifier}' not found.[/error]")
        raise typer.Exit(1)

    body: dict = {}
    if title is not None:
        body["title"] = title
    if due_date is not None:
        d = parse_date(due_date)
        body["due"] = f"{rfc3339_date(d)}T00:00:00.000Z"
    if notes_text is not None:
        body["notes"] = notes_text

    if not body:
        # Interactive prompt
        body["title"] = typer.prompt("Title", default=task.get("title", ""))
        due_input = typer.prompt("Due date (empty to skip)", default="")
        if due_input:
            d = parse_date(due_input)
            body["due"] = f"{rfc3339_date(d)}T00:00:00.000Z"
        notes_input = typer.prompt("Notes (empty to skip)", default="")
        if notes_input:
            body["notes"] = notes_input

    updated = client.patch_task(list_id, task["id"], body)
    console.print(f"[success]Updated:[/success] {updated.get('title', '?')}")


# ── task delete ────────────────────────────────────────────────────


@app.command()
def delete(
    identifier: Annotated[str, typer.Argument(help="Task ID, title, or position.")],
    list_name: Annotated[Optional[str], typer.Option("-l", "--list")] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Delete a task."""
    cfg, client, _cache, console = _get_deps()
    list_id = _resolve_list(cfg, client, list_name)

    task = client.resolve_task(identifier, list_id)
    if task is None:
        console.print(f"[error]Task '{identifier}' not found.[/error]")
        raise typer.Exit(1)

    title = task.get("title", "?")
    if not yes:
        if not Confirm.ask(f"Delete '{title}'?", default=False):
            console.print("[muted]Cancelled.[/muted]")
            return

    client.delete_task(list_id, task["id"])
    console.print(f"[success]Deleted:[/success] {title}")


# ── task clear ─────────────────────────────────────────────────────


@app.command("clear")
def clear(
    list_name: Annotated[Optional[str], typer.Option("-l", "--list")] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Clear all completed tasks from a list."""
    cfg, client, _cache, console = _get_deps()
    list_id = _resolve_list(cfg, client, list_name)

    if not yes:
        name = list_name or cfg.tasks.default_list
        if not Confirm.ask(f"Clear completed tasks in '{name}'?", default=False):
            console.print("[muted]Cancelled.[/muted]")
            return

    client.clear_completed(list_id)
    console.print("[success]Cleared completed tasks.[/success]")


# ── task search ────────────────────────────────────────────────────


@app.command()
def search(
    text: Annotated[str, typer.Argument(help="Search text.")],
    list_name: Annotated[Optional[str], typer.Option("-l", "--list")] = None,
    show_notes: Annotated[bool, typer.Option("--show-notes")] = False,
) -> None:
    """Search tasks by title or notes (client-side filter)."""
    cfg, client, _cache, console = _get_deps()
    list_id = _resolve_list(cfg, client, list_name)
    tasks = client.list_tasks(list_id, show_completed=True, refresh=True)

    lowered = text.lower()
    matched = [
        t for t in tasks
        if lowered in t.get("title", "").lower()
        or lowered in t.get("notes", "").lower()
    ]

    if not matched:
        console.print("[muted]No matching tasks found.[/muted]")
        return

    list_title = f"Search: '{text}'"
    format_task_list(matched, list_title, console, show_notes=show_notes)

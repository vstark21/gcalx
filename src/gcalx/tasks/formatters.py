"""Rich formatters for tasks output."""

from __future__ import annotations

from datetime import date, datetime

from rich.console import Console
from rich.table import Table

from gcalx.shared.dates import format_relative_date
from gcalx.shared.utils import pluralize, truncate


def format_task_lists(task_lists: list[dict], console: Console) -> None:
    """Print a table of task lists."""
    table = Table(show_header=True, header_style="header", box=None, pad_edge=False)
    table.add_column("Task List", style="cal.title", min_width=25)
    table.add_column("Updated", justify="right", style="muted")

    for tl in task_lists:
        title = tl.get("title", tl.get("id", "?"))
        updated = tl.get("updated", "")
        if updated:
            try:
                dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                updated = format_relative_date(dt.date())
            except (ValueError, TypeError):
                pass
        table.add_row(title, updated)

    console.print(table)


def format_task_list(
    tasks: list[dict],
    list_title: str,
    console: Console,
    *,
    show_notes: bool = False,
    show_id: bool = False,
) -> None:
    """Print tasks with status indicators and optional hierarchy."""
    # Separate top-level tasks vs subtasks
    top_level: list[dict] = []
    children: dict[str, list[dict]] = {}

    for t in tasks:
        parent = t.get("parent")
        if parent:
            children.setdefault(parent, []).append(t)
        else:
            top_level.append(t)

    count = len(tasks)
    console.print(f"\n [header]{list_title}[/header] [muted]({pluralize(count, 'task')})[/muted]")
    console.print(" " + "━" * 50)

    for i, task in enumerate(top_level, 1):
        _print_task(console, task, i, show_notes=show_notes, show_id=show_id)

        # Subtasks
        subs = children.get(task["id"], [])
        for j, sub in enumerate(subs):
            is_last = j == len(subs) - 1
            prefix = "└─" if is_last else "├─"
            letter = chr(ord("a") + j)
            _print_task(
                console, sub, f"{i}{letter}",
                prefix=f"    [task.subtask]{prefix}[/task.subtask] ",
                show_notes=show_notes,
                show_id=show_id,
            )


def _print_task(
    console: Console,
    task: dict,
    number: int | str,
    *,
    prefix: str = " ",
    show_notes: bool = False,
    show_id: bool = False,
) -> None:
    """Print a single task line."""
    title = task.get("title", "(No title)")
    status = task.get("status", "needsAction")
    due_str = task.get("due", "")

    if status == "completed":
        icon = "✓"
        style = "task.done"
    else:
        icon = "☐"
        # Check if overdue
        if due_str:
            try:
                due_date = date.fromisoformat(due_str[:10])
                if due_date < date.today():
                    style = "task.overdue"
                else:
                    style = "task.pending"
            except ValueError:
                style = "task.pending"
        else:
            style = "task.pending"

    line = f"{prefix}[{style}]{icon}  {number}. {truncate(title, 40)}[/{style}]"

    # Due / completed date
    if status == "completed" and task.get("completed"):
        try:
            comp = datetime.fromisoformat(
                task["completed"].replace("Z", "+00:00")
            )
            rel = format_relative_date(comp.date())
            line += f"  [task.done]done: {rel}[/task.done]"
        except (ValueError, TypeError):
            pass
    elif due_str:
        try:
            due_date = date.fromisoformat(due_str[:10])
            rel = format_relative_date(due_date)
            if due_date < date.today():
                line += f"  [task.overdue]due: {rel}[/task.overdue]"
            else:
                line += f"  [task.due]due: {rel}[/task.due]"
        except ValueError:
            pass

    if show_id:
        line += f"  [muted]({task.get('id', '?')})[/muted]"

    console.print(line)

    if show_notes and task.get("notes"):
        for notes_line in task["notes"].splitlines():
            console.print(f"{prefix}     [task.notes]{notes_line}[/task.notes]")

"""Rich console and Dusk theme for gcalx output."""

from __future__ import annotations

from rich.console import Console
from rich.theme import Theme

# ── Dusk palette ───────────────────────────────────────────────────
# Calm twilight tones — high contrast where it matters.

_DUSK_STYLES: dict[str, str] = {
    # Calendar
    "cal.date":        "bold #7AA2F7",       # soft blue — date headers
    "cal.time":        "#9ECE6A",            # green — event times
    "cal.title":       "bold #C0CAF5",       # light lavender — event titles
    "cal.location":    "italic #BB9AF7",     # purple — locations
    "cal.description": "#565F89",            # muted gray — descriptions
    "cal.now":         "bold #FF9E64",       # warm orange — now marker
    "cal.allday":      "bold #E0AF68",       # amber — all-day events
    "cal.declined":    "dim strike",          # dimmed — declined events
    "cal.border":      "#3B4261",            # dark blue-gray — borders

    # Calendar access roles
    "cal.owner":       "bold #7AA2F7",
    "cal.writer":      "#9ECE6A",
    "cal.reader":      "#BB9AF7",
    "cal.freebusy":    "#565F89",

    # Tasks
    "task.pending":    "#7DCFFF",            # cyan — pending tasks
    "task.done":       "dim #9ECE6A",        # dim green — completed
    "task.overdue":    "bold #F7768E",       # red — overdue
    "task.due":        "#E0AF68",            # amber — due date
    "task.notes":      "italic #565F89",     # gray — notes
    "task.subtask":    "#7AA2F7",            # blue — subtask tree lines

    # Shared
    "header":          "bold #C0CAF5",       # section headers
    "success":         "bold #9ECE6A",
    "warning":         "bold #E0AF68",
    "error":           "bold #F7768E",
    "muted":           "#565F89",
    "link":            "underline #7DCFFF",
}


def build_theme(overrides: dict[str, str] | None = None) -> Theme:
    """Build the Dusk theme, optionally merging user overrides."""
    styles = dict(_DUSK_STYLES)
    if overrides:
        styles.update(overrides)
    return Theme(styles)


def get_console(
    *,
    color: bool = True,
    overrides: dict[str, str] | None = None,
) -> Console:
    """Return a Console wired to the Dusk theme."""
    return Console(
        theme=build_theme(overrides),
        highlight=False,
        force_terminal=color,
        no_color=not color,
    )

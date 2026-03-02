---
name: gcalx
description: "Manage Google Calendar events and Google Tasks from the terminal via the gcalx CLI. Use when: user asks about calendar events, scheduling, tasks, todos, or reminders."
metadata:
    "openclaw":
        "emoji": "📅"
---

# gcalx

Unified CLI for Google Calendar + Google Tasks. One auth flow, one config.

## When to Use

✅ **USE this skill when:**

- "What's on my calendar today?"
- "Add a meeting tomorrow at 3pm"
- "What tasks are due this week?"
- "Mark the groceries task as done"
- "Show my overdue tasks"
- "Quick-add: Lunch with Sarah Friday noon"
- "Search for standup events"
- "What are my task lists?"

❌ **DON'T use this skill when:**

- Managing calendar settings or permissions → use Google admin
- Shared calendar administration → use Google Workspace admin
- Non-Google calendar services (Apple, Outlook)

## Prerequisites

gcalx must be authenticated before use. If commands fail with auth errors, run:

```bash
gcalx init
```

Config: `~/.config/gcalx/config.toml` (OAuth credentials + display prefs).

## Commands

### Combined View

```bash
# Today's agenda + due/overdue tasks in one view
gcalx today
```

### Calendar (`gcalx cal`)

```bash
# List all calendars
gcalx cal list

# Show agenda (default: next 5 days)
gcalx cal agenda

# Custom date range (natural language supported)
gcalx cal agenda "tomorrow" "next friday"

# Quick-add event from natural language
gcalx cal quick "Lunch tomorrow at noon"

# Add event with full details
gcalx cal add --title "Meeting" --when "friday 3pm" --duration 60

# Search events
gcalx cal search "standup"

# Delete an event
gcalx cal delete "dentist"
```

### Tasks (`gcalx task`)

```bash
# List all task lists
gcalx task lists

# List tasks (shows hierarchy, due dates, status)
gcalx task ls

# List tasks due today
gcalx task ls --due today

# Add a task
gcalx task add "Buy groceries" --due "saturday"

# Add a subtask under a parent
gcalx task add "Subtask" --parent "Main task"

# Mark task done (by position number or title)
gcalx task done 3
gcalx task done "Buy groceries"

# Reopen a completed task
gcalx task undone 3

# Edit a task
gcalx task edit 2 --due "next monday"

# Search tasks
gcalx task search "report"

# Delete a task
gcalx task delete 1

# Clear all completed tasks
gcalx task clear
```

## Natural Language Dates

gcalx supports natural language in date arguments:

- Relative: `"today"`, `"tomorrow"`, `"yesterday"`
- Named days: `"monday"`, `"next friday"`
- Shorthand: `"3d"` (3 days), `"2w"` (2 weeks)
- Combined: `"friday 3pm"`, `"tomorrow at noon"`

## Task Positions

Tasks can be referenced by position number (as shown in `gcalx task ls` output) or by title substring. Position numbers are stable within a single listing and reset on refresh.

## Output Format

- Output is styled for terminal display (Rich formatting).
- Use `2>&1` if you need to capture both stdout and stderr.
- Calendar events show time, title, and duration.
- Tasks show status icon (☐/☑), position, title, due date.
- `gcalx today` groups into: calendar, due today, and overdue.

## Multiple Task Lists

```bash
# See available lists
gcalx task lists

# Work with a specific list
gcalx task ls --list "Work"
gcalx task add "Deploy app" --list "Work"
```

Default list is configured in `~/.config/gcalx/config.toml` under `[tasks] default_list`.

# gcalx

**Google Calendar Extended** — a unified CLI for Google Calendar and Google Tasks.

Manage your calendar events and tasks from the terminal with a single tool, one auth flow, and one config.

```
pip install git+https://github.com/vstark21/gcalx.git
```

## Features

- **Calendar + Tasks in one CLI** — no switching between tools
- **Natural language dates** — `"tomorrow"`, `"next friday"`, `"3d"`, `"2w"`
- **Quick-add events** — `gcalx cal quick "Lunch tomorrow at noon"`
- **Task management** — add, complete, edit, delete, search
- **Combined today view** — agenda + due tasks at a glance
- **Positional task references** — `gcalx task done 3` (by list position)
- **SQLite caching** — fast repeated queries
- **Rich terminal output** — colored, themed, readable
- **TOML config** — customizable defaults and theme overrides

## Setup

### 1. Create Google OAuth Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project (or select an existing one)
3. Enable the **Google Calendar API** and **Google Tasks API**
4. Go to **Credentials** → **Create Credentials** → **OAuth client ID**
5. Select **Desktop app** as the application type
6. Download or copy the **Client ID** and **Client Secret**

### 2. Configure gcalx

Add your credentials to `~/.config/gcalx/config.toml`:

```toml
[auth]
client_id = "your-client-id.apps.googleusercontent.com"
client_secret = "your-client-secret"
```

Or use environment variables:

```bash
export GCALX_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GCALX_CLIENT_SECRET="your-client-secret"
```

### 3. Authenticate

```bash
gcalx init
```

This opens a browser for Google OAuth consent. On headless machines, it prints the URL and waits — use SSH port forwarding:

```bash
ssh -L <port>:localhost:<port> user@host
```

## Usage

### Calendar

```bash
gcalx cal agenda                              # next 5 days
gcalx cal agenda "tomorrow" "next friday"     # custom range
gcalx cal quick "Lunch with Sarah tomorrow at noon"
gcalx cal add --title "Meeting" --when "friday 3pm" --duration 60
gcalx cal search "standup"
gcalx cal list                                # list all calendars
gcalx cal delete "dentist"                    # find and delete
```

### Tasks

```bash
gcalx task ls                                 # list tasks
gcalx task ls --due today                     # due today
gcalx task add "Buy groceries" --due "saturday"
gcalx task add "Subtask" --parent "Main task"
gcalx task done 3                             # complete by position
gcalx task done "Buy groceries"               # or by title
gcalx task edit 2 --due "next monday"
gcalx task search "report"
gcalx task clear                              # clear completed
```

### Combined

```bash
gcalx today                                  # today's agenda + due tasks
```

## Commands

### Calendar (`gcalx cal`)

| Command | Description |
|---------|-------------|
| `cal list` | List available calendars with access roles |
| `cal agenda [START] [END]` | Show agenda for a time period (default: 5 days) |
| `cal add` | Add an event with full details |
| `cal quick TEXT` | Quick-add event from natural language |
| `cal search TEXT [START] [END]` | Search events by text |
| `cal delete TEXT [START] [END]` | Find and delete events |

### Tasks (`gcalx task`)

| Command | Description |
|---------|-------------|
| `task lists` | List all task lists |
| `task ls` | List tasks (with hierarchy, due dates, status) |
| `task add TITLE` | Add a new task |
| `task done ID_OR_POS` | Mark a task as completed |
| `task undone ID_OR_POS` | Reopen a completed task |
| `task edit ID_OR_POS` | Edit title, due date, or notes |
| `task delete ID_OR_POS` | Delete a task |
| `task clear` | Clear all completed tasks |
| `task search TEXT` | Search tasks by title or notes |

### Global

| Command | Description |
|---------|-------------|
| `init` | Run OAuth2 authentication |
| `today` | Today's events + due/overdue tasks |
| `--version` | Show version |

## Configuration

Config file: `~/.config/gcalx/config.toml`

```toml
[auth]
client_id = "your-client-id.apps.googleusercontent.com"
client_secret = "your-client-secret"

[calendar]
default_calendar = "primary"
military = true          # 24h time (false for 12h)
week_start = "monday"
width = 80

[tasks]
default_list = "My Tasks"

[display]
color = true
lineart = "unicode"

# Override any theme color
[theme]
"cal.date" = "bold cyan"
"task.overdue" = "bold red on white"
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GCALX_CLIENT_ID` | Google OAuth client ID (overrides config) |
| `GCALX_CLIENT_SECRET` | Google OAuth client secret (overrides config) |

## OpenClaw Skill

This project was built as part of an [OpenClaw](https://github.com/openclaw/openclaw) setup so an AI agent can manage your calendar and tasks via chat. An OpenClaw skill definition is included at [`.github/skills/gcalx/SKILL.md`](.github/skills/gcalx/SKILL.md) — copy it into your OpenClaw skills directory to enable it:

```bash
cp -r .github/skills/gcalx ~/.openclaw/workspace/skills/gcalx
```

## Development

```bash
git clone https://github.com/vstark21/gcalx.git
cd gcalx
pip install -e ".[dev]"
```

## License

[MIT](LICENSE)

## Support

If you find gcalx useful, consider buying me a coffee:

<a href="https://buymeacoffee.com/vstark21" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40"></a>

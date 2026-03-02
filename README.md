# gcalx

**Google Calendar Extended** — a unified CLI for Google Calendar and Google Tasks.

```
pip install gcalx
```

## Why?

- `gcalcli` doesn't support Google Tasks — and that's what many people actually use
- No mature Tasks CLI exists anywhere
- One tool, one auth flow, one config for both calendar events and tasks

## Quick Start

```bash
# Authenticate (one time)
gcalx init --client-id YOUR_ID --client-secret YOUR_SECRET

# Calendar
gcalx cal agenda                          # next 5 days
gcalx cal quick "Lunch tomorrow at noon"  # quick-add event
gcalx cal add --title "Meeting" --when "friday 3pm" --duration 60

# Tasks
gcalx task ls                             # list tasks
gcalx task add "Buy groceries" --due "saturday"
gcalx task done "Buy groceries"

# Combined
gcalx today                              # today's agenda + due tasks
```

## Commands

### Calendar (`gcalx cal`)

| Command | Description |
|---------|-------------|
| `cal list` | List available calendars |
| `cal agenda [START] [END]` | Show agenda for time period |
| `cal add` | Add event with full details |
| `cal quick TEXT` | Quick-add event from natural language |
| `cal search TEXT` | Search events |
| `cal delete TEXT` | Find and delete events |

### Tasks (`gcalx task`)

| Command | Description |
|---------|-------------|
| `task lists` | List all task lists |
| `task ls` | List tasks |
| `task add TITLE` | Add a new task |
| `task done ID_OR_TITLE` | Complete a task |
| `task delete ID_OR_TITLE` | Delete a task |

### Global

| Command | Description |
|---------|-------------|
| `init` | Run OAuth2 authentication |
| `today` | Today's agenda + due tasks |

## Configuration

Config lives at `~/.config/gcalx/config.toml`:

```toml
[auth]
client_id = "your-client-id"
client_secret = "your-client-secret"

[calendar]
default_calendar = "primary"
military = true

[tasks]
default_list = "My Tasks"
```

## License

MIT

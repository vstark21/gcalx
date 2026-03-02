"""gcalx CLI entry point."""

import typer

app = typer.Typer(
    name="gcalx",
    help="Google Calendar Extended — unified CLI for Google Calendar and Tasks.",
    no_args_is_help=True,
)

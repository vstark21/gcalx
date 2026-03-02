"""Small utility helpers used across gcalx."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console


def ensure_auth(config_dir: Path) -> None:
    """Exit with a helpful message if no token is found."""
    token = config_dir / "token.json"
    if not token.exists():
        console = Console(stderr=True)
        console.print(
            "[error]Not authenticated. Run [bold]gcalx init[/bold] first.[/error]"
        )
        sys.exit(1)


def truncate(text: str, length: int = 50) -> str:
    """Truncate *text* to *length* chars, adding '…' if shortened."""
    if len(text) <= length:
        return text
    return text[: length - 1] + "…"


def pluralize(n: int, singular: str, plural: str | None = None) -> str:
    """Return ``'1 event'`` or ``'3 events'``."""
    if plural is None:
        plural = singular + "s"
    return f"{n} {singular}" if n == 1 else f"{n} {plural}"

"""Shared dependency bootstrapping for CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import typer

from gcalx.auth import load_credentials
from gcalx.config import Config, load_config
from gcalx.shared.cache import Cache
from gcalx.shared.printer import get_console
from gcalx.shared.utils import ensure_auth

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials
    from rich.console import Console


def get_deps(
    *,
    build_service: Any,
    build_client: Any,
    refresh: bool = False,
) -> tuple[Config, Any, Cache, "Console"]:
    """Bootstrap config → creds → service → client → console.

    Args:
        build_service: Callable to build the Google API service
            (e.g. ``build_calendar_service`` or ``build_tasks_service``).
        build_client: Client class to instantiate
            (e.g. ``CalendarClient`` or ``TasksClient``).
        refresh: Whether to bypass the cache.

    Returns:
        A tuple of ``(config, client, cache, console)``.
    """
    cfg = load_config()
    creds = _load_creds(cfg)
    svc = build_service(creds)
    cache = Cache(cfg.cache_path)
    client = build_client(svc, cache)
    console = get_console(
        color=cfg.display.color,
        overrides=cfg.theme.overrides or None,
    )
    return cfg, client, cache, console


def _load_creds(cfg: Config) -> "Credentials":
    """Load credentials or exit with a helpful message."""
    ensure_auth(cfg.config_dir)
    creds = load_credentials(cfg.config_dir)
    if creds is None:
        typer.echo(
            "Failed to load credentials. Run `gcalx init`.", err=True
        )
        raise typer.Exit(1)
    return creds

"""Configuration loading and defaults for gcalx."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "gcalx"


@dataclass
class AuthConfig:
    client_id: str = ""
    client_secret: str = ""


@dataclass
class CalendarConfig:
    default_calendar: str = "primary"
    military: bool = True
    week_start: str = "monday"
    width: int = 80


@dataclass
class TasksConfig:
    default_list: str = "My Tasks"


@dataclass
class DisplayConfig:
    color: bool = True
    lineart: str = "unicode"


@dataclass
class ThemeOverrides:
    overrides: dict[str, str] = field(default_factory=dict)


@dataclass
class Config:
    auth: AuthConfig = field(default_factory=AuthConfig)
    calendar: CalendarConfig = field(default_factory=CalendarConfig)
    tasks: TasksConfig = field(default_factory=TasksConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    theme: ThemeOverrides = field(default_factory=ThemeOverrides)
    config_dir: Path = DEFAULT_CONFIG_DIR

    @property
    def token_path(self) -> Path:
        return self.config_dir / "token.json"

    @property
    def cache_path(self) -> Path:
        return self.config_dir / "cache.db"

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.toml"


def _merge_dict(target: dict, source: dict) -> dict:
    """Shallow merge source into target."""
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_dict(target[key], value)
        else:
            target[key] = value
    return target


def _dict_to_config(data: dict[str, Any]) -> Config:
    """Convert a parsed TOML dict to a Config dataclass."""
    cfg = Config()

    if "auth" in data:
        cfg.auth = AuthConfig(**{
            k: v for k, v in data["auth"].items()
            if k in AuthConfig.__dataclass_fields__
        })

    if "calendar" in data:
        cfg.calendar = CalendarConfig(**{
            k: v for k, v in data["calendar"].items()
            if k in CalendarConfig.__dataclass_fields__
        })

    if "tasks" in data:
        cfg.tasks = TasksConfig(**{
            k: v for k, v in data["tasks"].items()
            if k in TasksConfig.__dataclass_fields__
        })

    if "display" in data:
        cfg.display = DisplayConfig(**{
            k: v for k, v in data["display"].items()
            if k in DisplayConfig.__dataclass_fields__
        })

    if "theme" in data:
        cfg.theme = ThemeOverrides(overrides=dict(data["theme"]))

    return cfg


def load_config(config_dir: Path | None = None) -> Config:
    """Load config from TOML file, falling back to defaults.

    Args:
        config_dir: Override config directory. Defaults to ~/.config/gcalx/
    """
    if config_dir is None:
        config_dir = DEFAULT_CONFIG_DIR

    config_file = config_dir / "config.toml"
    cfg = Config(config_dir=config_dir)

    # Environment variables always take priority
    env_id = os.environ.get("GCALX_CLIENT_ID", "")
    env_secret = os.environ.get("GCALX_CLIENT_SECRET", "")

    if not config_file.exists():
        cfg.auth.client_id = env_id
        cfg.auth.client_secret = env_secret
        return cfg

    if tomllib is None:
        # Can't parse TOML without tomllib/tomli — return defaults
        return cfg

    with open(config_file, "rb") as f:
        data = tomllib.load(f)

    parsed = _dict_to_config(data)
    parsed.config_dir = config_dir

    # Environment variables override config file
    parsed.auth.client_id = env_id or parsed.auth.client_id
    parsed.auth.client_secret = env_secret or parsed.auth.client_secret

    return parsed


def save_config(cfg: Config) -> None:
    """Write config to TOML file (minimal writer — no dependency needed)."""
    cfg.config_dir.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    if cfg.auth.client_id or cfg.auth.client_secret:
        lines.append("[auth]")
        if cfg.auth.client_id:
            lines.append(f'client_id = "{cfg.auth.client_id}"')
        if cfg.auth.client_secret:
            lines.append(f'client_secret = "{cfg.auth.client_secret}"')
        lines.append("")

    lines.append("[calendar]")
    lines.append(f'default_calendar = "{cfg.calendar.default_calendar}"')
    lines.append(f"military = {'true' if cfg.calendar.military else 'false'}")
    lines.append(f'week_start = "{cfg.calendar.week_start}"')
    lines.append(f"width = {cfg.calendar.width}")
    lines.append("")

    lines.append("[tasks]")
    lines.append(f'default_list = "{cfg.tasks.default_list}"')
    lines.append("")

    lines.append("[display]")
    lines.append(f"color = {'true' if cfg.display.color else 'false'}")
    lines.append(f'lineart = "{cfg.display.lineart}"')
    lines.append("")

    if cfg.theme.overrides:
        lines.append("[theme]")
        for key, value in cfg.theme.overrides.items():
            lines.append(f'"{key}" = "{value}"')
        lines.append("")

    cfg.config_file.write_text("\n".join(lines) + "\n")

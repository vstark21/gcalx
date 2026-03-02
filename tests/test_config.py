"""Tests for gcalx.config — configuration loading and saving."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from gcalx.config import (
    Config,
    _dict_to_config,
    _toml_escape,
    load_config,
    save_config,
)


# ── _toml_escape ───────────────────────────────────────────────────


class TestTomlEscape:
    def test_plain_string(self) -> None:
        assert _toml_escape("hello") == "hello"

    def test_escapes_quotes(self) -> None:
        assert _toml_escape('say "hi"') == 'say \\"hi\\"'

    def test_escapes_backslash(self) -> None:
        assert _toml_escape("a\\b") == "a\\\\b"

    def test_combined(self) -> None:
        assert _toml_escape('a\\b"c') == 'a\\\\b\\"c'


# ── _dict_to_config ────────────────────────────────────────────────


class TestDictToConfig:
    def test_empty_dict(self) -> None:
        cfg = _dict_to_config({})
        assert cfg.auth.client_id == ""
        assert cfg.calendar.default_calendar == "primary"
        assert cfg.tasks.default_list == "My Tasks"

    def test_auth_section(self) -> None:
        data = {"auth": {"client_id": "my-id", "client_secret": "my-secret"}}
        cfg = _dict_to_config(data)
        assert cfg.auth.client_id == "my-id"
        assert cfg.auth.client_secret == "my-secret"

    def test_calendar_section(self) -> None:
        data = {"calendar": {"military": False, "width": 120}}
        cfg = _dict_to_config(data)
        assert cfg.calendar.military is False
        assert cfg.calendar.width == 120
        assert cfg.calendar.default_calendar == "primary"  # default preserved

    def test_tasks_section(self) -> None:
        data = {"tasks": {"default_list": "Work"}}
        cfg = _dict_to_config(data)
        assert cfg.tasks.default_list == "Work"

    def test_display_section(self) -> None:
        data = {"display": {"color": False, "lineart": "ascii"}}
        cfg = _dict_to_config(data)
        assert cfg.display.color is False
        assert cfg.display.lineart == "ascii"

    def test_theme_section(self) -> None:
        data = {"theme": {"cal.date": "bold red", "task.done": "green"}}
        cfg = _dict_to_config(data)
        assert cfg.theme.overrides == {"cal.date": "bold red", "task.done": "green"}

    def test_ignores_unknown_fields(self) -> None:
        data = {"auth": {"client_id": "id", "unknown_field": "ignored"}}
        cfg = _dict_to_config(data)
        assert cfg.auth.client_id == "id"
        assert not hasattr(cfg.auth, "unknown_field")


# ── load_config ────────────────────────────────────────────────────


class TestLoadConfig:
    def test_defaults_when_no_file(self, tmp_path: Path) -> None:
        cfg = load_config(tmp_path)
        assert cfg.config_dir == tmp_path
        assert cfg.calendar.military is True
        assert cfg.auth.client_id == ""

    def test_loads_toml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[auth]\nclient_id = "test-id"\nclient_secret = "test-secret"\n'
            "[calendar]\nmilitary = false\n"
        )
        cfg = load_config(tmp_path)
        assert cfg.auth.client_id == "test-id"
        assert cfg.calendar.military is False

    def test_env_vars_override_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[auth]\nclient_id = "file-id"\nclient_secret = "file-secret"\n'
        )
        monkeypatch.setenv("GCALX_CLIENT_ID", "env-id")
        monkeypatch.setenv("GCALX_CLIENT_SECRET", "env-secret")

        cfg = load_config(tmp_path)
        assert cfg.auth.client_id == "env-id"
        assert cfg.auth.client_secret == "env-secret"

    def test_env_vars_without_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GCALX_CLIENT_ID", "env-id")
        monkeypatch.setenv("GCALX_CLIENT_SECRET", "env-secret")

        cfg = load_config(tmp_path)
        assert cfg.auth.client_id == "env-id"
        assert cfg.auth.client_secret == "env-secret"

    def test_env_empty_falls_back_to_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[auth]\nclient_id = "file-id"\nclient_secret = "file-secret"\n'
        )
        monkeypatch.delenv("GCALX_CLIENT_ID", raising=False)
        monkeypatch.delenv("GCALX_CLIENT_SECRET", raising=False)

        cfg = load_config(tmp_path)
        assert cfg.auth.client_id == "file-id"

    def test_config_paths(self, tmp_path: Path) -> None:
        cfg = load_config(tmp_path)
        assert cfg.token_path == tmp_path / "token.json"
        assert cfg.cache_path == tmp_path / "cache.db"
        assert cfg.config_file == tmp_path / "config.toml"


# ── save_config ────────────────────────────────────────────────────


class TestSaveConfig:
    def test_roundtrip(self, tmp_path: Path) -> None:
        cfg = Config(config_dir=tmp_path)
        cfg.auth.client_id = "my-id"
        cfg.auth.client_secret = "my-secret"
        cfg.calendar.military = False
        cfg.tasks.default_list = "Work"

        save_config(cfg)
        loaded = load_config(tmp_path)

        assert loaded.auth.client_id == "my-id"
        assert loaded.calendar.military is False
        assert loaded.tasks.default_list == "Work"

    def test_file_permissions(self, tmp_path: Path) -> None:
        cfg = Config(config_dir=tmp_path)
        save_config(cfg)

        mode = cfg.config_file.stat().st_mode
        assert stat.S_IMODE(mode) == 0o600

    def test_creates_directory(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b"
        cfg = Config(config_dir=deep)
        save_config(cfg)
        assert cfg.config_file.exists()

    def test_escapes_quotes_in_values(self, tmp_path: Path) -> None:
        cfg = Config(config_dir=tmp_path)
        cfg.auth.client_id = 'id-with-"quotes"'
        save_config(cfg)

        content = cfg.config_file.read_text()
        assert '\\"quotes\\"' in content

        # Verify it loads back correctly
        loaded = load_config(tmp_path)
        assert loaded.auth.client_id == 'id-with-"quotes"'

    def test_theme_overrides(self, tmp_path: Path) -> None:
        cfg = Config(config_dir=tmp_path)
        cfg.theme.overrides = {"cal.date": "bold cyan"}
        save_config(cfg)

        loaded = load_config(tmp_path)
        assert loaded.theme.overrides == {"cal.date": "bold cyan"}

    def test_no_auth_section_when_empty(self, tmp_path: Path) -> None:
        cfg = Config(config_dir=tmp_path)
        save_config(cfg)

        content = cfg.config_file.read_text()
        assert "[auth]" not in content

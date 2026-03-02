"""Tests for gcalx.shared.utils — utility helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from gcalx.shared.utils import ensure_auth, pluralize, truncate


# ── truncate ───────────────────────────────────────────────────────


class TestTruncate:
    def test_short_string_unchanged(self) -> None:
        assert truncate("hello", 10) == "hello"

    def test_exact_length_unchanged(self) -> None:
        assert truncate("hello", 5) == "hello"

    def test_long_string_truncated(self) -> None:
        result = truncate("hello world", 8)
        assert result == "hello w…"
        assert len(result) == 8

    def test_default_length(self) -> None:
        long = "a" * 100
        result = truncate(long)
        assert len(result) == 50
        assert result.endswith("…")

    def test_empty_string(self) -> None:
        assert truncate("", 10) == ""


# ── pluralize ──────────────────────────────────────────────────────


class TestPluralize:
    def test_singular(self) -> None:
        assert pluralize(1, "event") == "1 event"

    def test_plural(self) -> None:
        assert pluralize(5, "event") == "5 events"

    def test_zero(self) -> None:
        assert pluralize(0, "task") == "0 tasks"

    def test_custom_plural(self) -> None:
        assert pluralize(2, "octopus", "octopi") == "2 octopi"

    def test_custom_plural_singular(self) -> None:
        assert pluralize(1, "octopus", "octopi") == "1 octopus"


# ── ensure_auth ────────────────────────────────────────────────────


class TestEnsureAuth:
    def test_exists_does_not_raise(self, tmp_path: Path) -> None:
        token = tmp_path / "token.json"
        token.write_text("{}")
        # Should not raise
        ensure_auth(tmp_path)

    def test_missing_raises_exit(self, tmp_path: Path) -> None:
        from click.exceptions import Exit

        with pytest.raises(Exit):
            ensure_auth(tmp_path)

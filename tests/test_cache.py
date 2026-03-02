"""Tests for gcalx.shared.cache — SQLite cache layer."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from gcalx.shared.cache import Cache


@pytest.fixture()
def cache(tmp_path: Path) -> Cache:
    """Create a fresh cache in a temp directory."""
    c = Cache(tmp_path / "test_cache.db")
    yield c
    c.close()


# ── get / set ──────────────────────────────────────────────────────


class TestGetSet:
    def test_set_and_get(self, cache: Cache) -> None:
        cache.set("key1", {"data": [1, 2, 3]}, ttl=60)
        result = cache.get("key1")
        assert result == {"data": [1, 2, 3]}

    def test_get_missing_key(self, cache: Cache) -> None:
        assert cache.get("nonexistent") is None

    def test_get_expired(self, cache: Cache) -> None:
        cache.set("key1", "value", ttl=0)
        # TTL=0 means it expires immediately
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_overwrite(self, cache: Cache) -> None:
        cache.set("key1", "old", ttl=60)
        cache.set("key1", "new", ttl=60)
        assert cache.get("key1") == "new"

    def test_stores_various_types(self, cache: Cache) -> None:
        cache.set("str", "hello", ttl=60)
        cache.set("int", 42, ttl=60)
        cache.set("list", [1, 2, 3], ttl=60)
        cache.set("dict", {"a": 1}, ttl=60)
        cache.set("null", None, ttl=60)
        cache.set("bool", True, ttl=60)

        assert cache.get("str") == "hello"
        assert cache.get("int") == 42
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"a": 1}
        assert cache.get("null") is None  # can't distinguish from miss
        assert cache.get("bool") is True


# ── invalidation ───────────────────────────────────────────────────


class TestInvalidation:
    def test_invalidate_prefix(self, cache: Cache) -> None:
        cache.set("events:cal1:a", "v1", ttl=60)
        cache.set("events:cal1:b", "v2", ttl=60)
        cache.set("tasks:list1", "v3", ttl=60)

        cache.invalidate("events:")

        assert cache.get("events:cal1:a") is None
        assert cache.get("events:cal1:b") is None
        assert cache.get("tasks:list1") == "v3"

    def test_delete_single(self, cache: Cache) -> None:
        cache.set("key1", "v1", ttl=60)
        cache.set("key2", "v2", ttl=60)

        cache.delete("key1")

        assert cache.get("key1") is None
        assert cache.get("key2") == "v2"

    def test_clear_all(self, cache: Cache) -> None:
        cache.set("a", 1, ttl=60)
        cache.set("b", 2, ttl=60)
        cache.save_task_positions("list1", [{"id": "t1", "title": "Task"}])

        cache.clear()

        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.resolve_task_position("list1", 1) is None


# ── task positions ─────────────────────────────────────────────────


class TestTaskPositions:
    def test_save_and_resolve(self, cache: Cache) -> None:
        tasks = [
            {"id": "task_a", "title": "First"},
            {"id": "task_b", "title": "Second"},
            {"id": "task_c", "title": "Third"},
        ]
        cache.save_task_positions("list1", tasks)

        assert cache.resolve_task_position("list1", 1) == "task_a"
        assert cache.resolve_task_position("list1", 2) == "task_b"
        assert cache.resolve_task_position("list1", 3) == "task_c"

    def test_resolve_invalid_position(self, cache: Cache) -> None:
        cache.save_task_positions("list1", [{"id": "t1", "title": "A"}])
        assert cache.resolve_task_position("list1", 99) is None

    def test_resolve_wrong_list(self, cache: Cache) -> None:
        cache.save_task_positions("list1", [{"id": "t1", "title": "A"}])
        assert cache.resolve_task_position("other_list", 1) is None

    def test_overwrite_positions(self, cache: Cache) -> None:
        cache.save_task_positions("list1", [{"id": "old", "title": "Old"}])
        cache.save_task_positions("list1", [{"id": "new", "title": "New"}])

        assert cache.resolve_task_position("list1", 1) == "new"

    def test_positions_isolated_per_list(self, cache: Cache) -> None:
        cache.save_task_positions("list1", [{"id": "t1", "title": "A"}])
        cache.save_task_positions("list2", [{"id": "t2", "title": "B"}])

        assert cache.resolve_task_position("list1", 1) == "t1"
        assert cache.resolve_task_position("list2", 1) == "t2"


# ── context manager ───────────────────────────────────────────────


class TestContextManager:
    def test_with_statement(self, tmp_path: Path) -> None:
        with Cache(tmp_path / "cm_cache.db") as c:
            c.set("key", "value", ttl=60)
            assert c.get("key") == "value"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c" / "cache.db"
        with Cache(deep) as c:
            c.set("k", "v", ttl=60)
            assert c.get("k") == "v"

"""Thin wrapper around the Google Tasks API v1."""

from __future__ import annotations

from typing import Any

from gcalx.shared.cache import Cache, TTL_TASK_LISTS, TTL_TASKS


class TasksClient:
    """Google Tasks API helper with cache integration."""

    def __init__(self, service: Any, cache: Cache) -> None:
        self._svc = service
        self._cache = cache

    # ── Task lists ─────────────────────────────────────────────────

    def list_task_lists(self, *, refresh: bool = False) -> list[dict]:
        """Return all task lists. Cached 24 h."""
        key = "tasklists"
        if not refresh:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

        items: list[dict] = []
        page_token: str | None = None
        while True:
            resp = (
                self._svc.tasklists()
                .list(pageToken=page_token)
                .execute()
            )
            items.extend(resp.get("items", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        self._cache.set(key, items, TTL_TASK_LISTS)
        return items

    def resolve_list_id(self, name: str) -> str:
        """Resolve a list name to its ID.

        Falls back to the first list whose title matches case-insensitively.
        Special value ``@default`` is returned as-is.
        """
        if name == "@default":
            return name
        lists = self.list_task_lists()
        for tl in lists:
            if tl.get("title", "").lower() == name.lower():
                return tl["id"]
        # Maybe it's already an ID
        return name

    # ── Tasks ──────────────────────────────────────────────────────

    def list_tasks(
        self,
        list_id: str = "@default",
        *,
        show_completed: bool = False,
        refresh: bool = False,
    ) -> list[dict]:
        """Fetch tasks in a list. Cached 2 min."""
        cache_key = f"tasks:{list_id}:{show_completed}"
        if not refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        items: list[dict] = []
        page_token: str | None = None
        while True:
            kwargs: dict[str, Any] = {
                "tasklist": list_id,
                "showCompleted": show_completed,
                "showHidden": False,
            }
            if page_token:
                kwargs["pageToken"] = page_token
            resp = self._svc.tasks().list(**kwargs).execute()
            items.extend(resp.get("items", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        self._cache.set(cache_key, items, TTL_TASKS)
        return items

    def get_task(self, list_id: str, task_id: str) -> dict:
        """Fetch a single task."""
        return (
            self._svc.tasks()
            .get(tasklist=list_id, task=task_id)
            .execute()
        )

    def insert_task(
        self,
        list_id: str,
        body: dict,
        *,
        parent: str | None = None,
    ) -> dict:
        """Insert a new task."""
        kwargs: dict[str, Any] = {"tasklist": list_id, "body": body}
        if parent:
            kwargs["parent"] = parent
        task = self._svc.tasks().insert(**kwargs).execute()
        self._cache.invalidate(f"tasks:{list_id}")
        return task

    def patch_task(self, list_id: str, task_id: str, body: dict) -> dict:
        """Partial update a task."""
        task = (
            self._svc.tasks()
            .patch(tasklist=list_id, task=task_id, body=body)
            .execute()
        )
        self._cache.invalidate(f"tasks:{list_id}")
        return task

    def delete_task(self, list_id: str, task_id: str) -> None:
        """Delete a task."""
        self._svc.tasks().delete(
            tasklist=list_id, task=task_id
        ).execute()
        self._cache.invalidate(f"tasks:{list_id}")

    def complete_task(self, list_id: str, task_id: str) -> dict:
        """Mark a task as completed."""
        return self.patch_task(list_id, task_id, {"status": "completed"})

    def uncomplete_task(self, list_id: str, task_id: str) -> dict:
        """Mark a completed task as needs action."""
        return self.patch_task(
            list_id, task_id, {"status": "needsAction", "completed": None}
        )

    def move_task(
        self,
        list_id: str,
        task_id: str,
        *,
        parent: str | None = None,
        previous: str | None = None,
    ) -> dict:
        """Move/reorder a task within its list."""
        kwargs: dict[str, Any] = {"tasklist": list_id, "task": task_id}
        if parent is not None:
            kwargs["parent"] = parent
        if previous is not None:
            kwargs["previous"] = previous
        task = self._svc.tasks().move(**kwargs).execute()
        self._cache.invalidate(f"tasks:{list_id}")
        return task

    def clear_completed(self, list_id: str) -> None:
        """Clear all completed tasks from a list."""
        self._svc.tasks().clear(tasklist=list_id).execute()
        self._cache.invalidate(f"tasks:{list_id}")

    def resolve_task(
        self, identifier: str, list_id: str
    ) -> dict | None:
        """Resolve a user-supplied identifier to a task dict.

        Resolution order:
        1. Pure integer → positional reference from last ``task ls``
        2. Exact task ID match
        3. Case-insensitive title substring match (first hit)
        """
        tasks = self.list_tasks(list_id, show_completed=True, refresh=True)

        # 1) Positional
        if identifier.isdigit():
            pos = int(identifier)
            task_id = self._cache.resolve_task_position(list_id, pos)
            if task_id:
                for t in tasks:
                    if t["id"] == task_id:
                        return t

        # 2) Exact ID
        for t in tasks:
            if t["id"] == identifier:
                return t

        # 3) Title match
        lowered = identifier.lower()
        for t in tasks:
            if lowered in t.get("title", "").lower():
                return t

        return None

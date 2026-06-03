"""Background-task retention helper.

`asyncio.create_task(coro)` returns a Task whose only owner inside the
event loop is a weak reference. If the caller drops the returned reference,
GC may collect the task mid-flight, silently cancelling it.

`spawn_bg(coro, bag)` adds the task to a caller-supplied `set` (strong
reference, no leak) and arranges for the task to remove itself when done.

Usage in a service class:

    class MyService:
        def __init__(self):
            self._bg_tasks: set[asyncio.Task] = set()

        def fire_and_forget(self, coro):
            spawn_bg(coro, self._bg_tasks)
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any


def spawn_bg(coro: Coroutine[Any, Any, Any], bag: set[asyncio.Task]) -> asyncio.Task:
    """Spawn a background task with a strong reference held in `bag`."""
    task = asyncio.create_task(coro)
    bag.add(task)
    task.add_done_callback(bag.discard)
    return task

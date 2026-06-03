"""TDD test for the background-task retention helper.

Bug it guards against: `asyncio.create_task(coro)` without storing the
returned Task lets the event loop's only strong reference live on the
loop's internal weak-task set, so the GC may collect the task before
the coroutine finishes, silently cancelling it.

(ruff RUF006: "Store a reference to the return value of asyncio.create_task")

The fix module under test: `app.domain.services._bg.spawn_bg`
Contract:
  1. Returned Task is added to the caller-supplied `bag: set[Task]`
     (a strong reference, so GC cannot reap mid-flight).
  2. When the Task finishes (or is cancelled), it is removed from the bag
     via add_done_callback — no permanent leak.
"""

import asyncio
import gc

import pytest

from app.domain.services._bg import spawn_bg


@pytest.mark.asyncio
async def test_spawn_bg_holds_strong_reference_during_run():
    """While the coroutine is running, the task must live in the bag."""
    bag: set[asyncio.Task] = set()
    started = asyncio.Event()
    release = asyncio.Event()

    async def work():
        started.set()
        await release.wait()

    task = spawn_bg(work(), bag)

    # Task is running; bag must hold the strong reference.
    await started.wait()
    assert task in bag, 'spawn_bg must put the task in the bag'
    assert len(bag) == 1

    # Even after forcing GC, the task must survive — because the bag holds it.
    del task
    gc.collect()
    assert len(bag) == 1
    bag_task = next(iter(bag))
    assert not bag_task.done()

    # Cleanup
    release.set()
    await bag_task


@pytest.mark.asyncio
async def test_spawn_bg_releases_reference_when_done():
    """After the coroutine finishes, the task must be removed from the bag."""
    bag: set[asyncio.Task] = set()

    async def quick_work():
        await asyncio.sleep(0)  # one event-loop tick, then return

    task = spawn_bg(quick_work(), bag)
    assert task in bag

    await task
    # add_done_callback runs in a subsequent event-loop iteration on some
    # implementations — yield once to let it fire.
    await asyncio.sleep(0)
    assert task not in bag, 'done_callback must discard the task from the bag'
    assert len(bag) == 0


@pytest.mark.asyncio
async def test_spawn_bg_releases_reference_on_cancellation():
    """If the task is cancelled, the bag must still be cleaned up."""
    bag: set[asyncio.Task] = set()

    async def long_work():
        await asyncio.sleep(60)

    task = spawn_bg(long_work(), bag)
    assert task in bag

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0)
    assert task not in bag


@pytest.mark.asyncio
async def test_spawn_bg_releases_reference_on_exception():
    """If the coroutine raises, the bag must still be cleaned up."""
    bag: set[asyncio.Task] = set()

    async def failing_work():
        raise RuntimeError('boom')

    task = spawn_bg(failing_work(), bag)
    assert task in bag

    with pytest.raises(RuntimeError, match='boom'):
        await task
    await asyncio.sleep(0)
    assert task not in bag

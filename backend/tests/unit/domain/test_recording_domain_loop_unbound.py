"""Regression test for `loop` possibly-unbound bug in on_recording_failed.

pyright reports `reportPossiblyUnboundVariable` for `loop` at
recording_domain.py:218 and :244 because `loop = asyncio.get_running_loop()`
is only assigned inside `if task.output_path.exists():` at line 178.

Bug trigger path:
  1. line 178: task.output_path.exists() returns False → `loop` is NOT defined
  2. on_recording_failed proceeds without `loop`
  3. Recording row does NOT exist (recording_id is None and no segment match)
     → else branch at line 239
  4. line 242: task.output_path.exists() returns True (file appeared while
     we were awaiting other work — e.g., the recorder finalised flush after
     line 178 but before line 242)
  5. line 244: `await loop.run_in_executor(...)` → NameError

This test forces that exists() sequence with a Path wrapper and asserts the
function completes without raising NameError.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.services.recording_domain import RecordingDomainService
from app.models.recording import Recording
from app.services.nas_syncer import NasSyncer


class _FlakyExistsPath:
    """Path-like wrapper whose exists() returns from a scripted sequence.

    All other Path methods delegate to the real path. We only need str(),
    exists(), and stat() — what on_recording_failed touches on task.output_path.
    """

    def __init__(self, real_path: Path, exists_sequence: list[bool]):
        self._real = real_path
        self._exists_returns = list(exists_sequence)
        self._call_idx = 0

    def exists(self) -> bool:
        if self._call_idx < len(self._exists_returns):
            ret = self._exists_returns[self._call_idx]
            self._call_idx += 1
            return ret
        # After the scripted sequence, defer to the real path
        return self._real.exists()

    def stat(self):
        return self._real.stat()

    def __str__(self) -> str:
        return str(self._real)

    def __fspath__(self) -> str:
        return str(self._real)


class _FakeTask:
    def __init__(self, output_path, camera_mac: str, recording_id, segment_index: int = 0):
        self.output_path = output_path
        self.camera_mac = camera_mac
        self.started_at = datetime(2026, 6, 1, 10, 0, 0)
        self.recording_id = recording_id
        self.segment_index = segment_index
        self.session_recording_id = None


@pytest.mark.asyncio
async def test_on_recording_failed_does_not_crash_when_file_appears_late(tmp_path):
    """Regression: `loop` must be defined even if first exists() check is False.

    Without the fix, this raises `NameError: name 'loop' is not defined`
    at recording_domain.py:244.
    """
    real_file = tmp_path / 'late_segment.mp4'
    real_file.write_bytes(b'fake-video-data')

    # First exists() (line 178) → False; subsequent (line 242 etc.) → True.
    flaky_path = _FlakyExistsPath(real_file, exists_sequence=[False])

    # recording_id=None and no pre-existing segment row → on_recording_failed
    # goes into the `else` branch (rec is None) at line 239.
    task = _FakeTask(
        output_path=flaky_path,
        camera_mac='DE:AD:BE:EF:00:01',
        recording_id=None,
    )

    svc = RecordingDomainService(MagicMock(spec=NasSyncer))
    # First exists() is False, so _probe_duration is never called by the
    # production code path — but configure it anyway for safety.
    svc._probe_duration = AsyncMock(return_value=None)

    import app.domain.services.recording_domain as rd_module

    original_ws = rd_module.ws_manager
    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()
    rd_module.ws_manager = mock_ws

    fake_syncer = MagicMock(spec=NasSyncer)
    fake_syncer.sync_file = MagicMock(return_value=real_file)
    svc._nas_syncer = fake_syncer

    try:
        # Must not raise NameError — this is the regression assertion.
        await svc.on_recording_failed(task, retcode=2, stderr='SIGKILL', keep_recording=False)

        # The bug currently lives behind a `except Exception` that silently
        # swallows the NameError, so the function returns successfully but
        # sync_file is NEVER actually called. The strong assertion is that
        # sync_file ran (which it can only do if `loop` is defined).
        assert fake_syncer.sync_file.called, (
            'NAS sync_file was never called — `loop` was unbound and the '
            'NameError got swallowed by the blind `except Exception` in '
            'recording_domain.on_recording_failed.'
        )

        # Sanity: a Recording row was inserted in the else branch, and its
        # file_path reflects the synced destination (not the fallback to
        # the raw task.output_path that the except branch falls back to).
        from sqlalchemy import select

        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            rec = (
                await session.execute(
                    select(Recording).where(Recording.camera_mac == 'DE:AD:BE:EF:00:01')
                )
            ).scalar_one_or_none()
            assert rec is not None, 'else-branch must insert a new Recording row'
            assert rec.segment_index == 0
            assert rec.file_path == str(real_file), (
                f'file_path should equal the sync destination (real_file), '
                f'not the fallback dest_str. Got: {rec.file_path}'
            )
    finally:
        rd_module.ws_manager = original_ws

"""Verify NasSyncer retries on transient file-lock errors (Windows).

The legacy ``app/services/nas_syncer.py`` ships a ``_copy_with_retry`` helper
that catches ``OSError`` (the typical Windows "file in use" error class) and
retries with exponential backoff. After the canonical-location flip the
implementation lives under ``app/domain/services/nas_syncer.py``; this test
imports via the canonical path to guarantee the retry behavior survives the
move.
"""

from __future__ import annotations

import errno
from pathlib import Path
from unittest.mock import patch


def _make_syncer(tmp_path: Path) -> tuple:
    """Build a NasSyncer pointing its local_storage at tmp_path."""
    from app.domain.services.nas_syncer import NasSyncer

    return NasSyncer(
        mode='local',
        local_storage_path=str(tmp_path / 'storage'),
    )


def test_sync_to_local_retries_then_succeeds(tmp_path: Path) -> None:
    """First two copy attempts raise PermissionError (Win32 sharing violation),
    third attempt succeeds. The sync must complete and the file must exist."""
    syncer = _make_syncer(tmp_path)

    src = tmp_path / 'recording.mp4'
    src.write_bytes(b'fake video bytes')

    perm_error = OSError(errno.EACCES, 'The process cannot access the file')

    call_counter = {'count': 0}

    def flaky_copy(src_str: str, dst_str: str) -> None:
        call_counter['count'] += 1
        if call_counter['count'] < 3:
            raise perm_error
        # 3rd call: real copy so the file is written.
        # Bypass the mock by reading bytes + writing directly.
        Path(dst_str).write_bytes(Path(src_str).read_bytes())

    with patch('app.domain.services.nas_syncer.shutil.copy2', side_effect=flaky_copy):
        dest = syncer._sync_to_local(src, 'mac1/2026-01-01/recording.mp4')

    # File was actually copied on the successful (3rd) attempt.
    assert dest.exists()
    assert dest.read_bytes() == b'fake video bytes'
    # And the retry helper was invoked at least 3 times.
    assert call_counter['count'] == 3


def test_sync_to_local_raises_after_exhausting_retries(tmp_path: Path) -> None:
    """If every retry attempt fails the helper must surface the last OSError."""
    syncer = _make_syncer(tmp_path)

    src = tmp_path / 'recording.mp4'
    src.write_bytes(b'fake video bytes')

    perm_error = OSError(errno.EACCES, 'permanently locked')

    # 5 attempts (max_retries default) all fail.
    with (
        patch(
            'app.domain.services.nas_syncer.shutil.copy2',
            side_effect=perm_error,
        ) as mock_copy,
        patch('app.domain.services.nas_syncer.time.sleep'),
    ):
        try:
            syncer._sync_to_local(src, 'mac1/2026-01-01/recording.mp4')
        except OSError as e:
            raised = e
        else:
            raise AssertionError('Expected OSError after exhausting retries')

    assert raised is perm_error
    assert mock_copy.call_count == 5


def test_sync_to_local_uses_exponential_backoff_delays(tmp_path: Path) -> None:
    """Delays must follow 0.5 * 2**attempt: 0.5, 1.0, 2.0, 4.0 between attempts."""
    syncer = _make_syncer(tmp_path)

    src = tmp_path / 'recording.mp4'
    src.write_bytes(b'fake video bytes')

    perm_error = OSError(errno.EACCES, 'locked')

    sleep_delays: list[float] = []

    def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    def always_fail(_src: str, _dst: str) -> None:
        raise perm_error

    with (
        patch(
            'app.domain.services.nas_syncer.shutil.copy2',
            side_effect=always_fail,
        ),
        patch('app.domain.services.nas_syncer.time.sleep', side_effect=fake_sleep),
    ):
        try:
            syncer._sync_to_local(src, 'mac1/2026-01-01/recording.mp4')
        except OSError:
            pass

    # 5 attempts → 4 sleeps in between.
    assert sleep_delays == [0.5, 1.0, 2.0, 4.0]

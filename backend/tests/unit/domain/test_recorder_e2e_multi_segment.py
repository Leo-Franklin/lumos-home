"""端到端测试：验证 5min10s + 60s 段时长 → 6 个独立 DB 记录和 6 个独立文件

通过 mock ffmpeg Popen 让每次"段"在一次 _monitor_loop 迭代中完成，
模拟生产环境的多段录制完整流程。
"""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.services.recorder import Recorder, RecordingParams


class _FakeProcess:
    """模拟 ffmpeg 进程对象。"""

    def __init__(self):
        self._retcode = None
        self._stderr = b''
        self.stdin = MagicMock()
        self.poll = MagicMock(side_effect=self._poll)
        self.wait = MagicMock(return_value=0)
        self.terminate = MagicMock()
        self.kill = MagicMock()
        self.stderr = MagicMock(read=MagicMock(side_effect=lambda n=-1: self._stderr))

    def _poll(self):
        return self._retcode

    def set_finished(self):
        self._retcode = 0

    def set_failed(self, code=1, stderr=b'ffmpeg error'):
        self._retcode = code
        self._stderr = stderr


def _make_writeable_file(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'x' * 20 * 1024)


async def _run_monitor_one_tick(recorder: Recorder) -> bool:
    """执行 _monitor_loop 中"一次检查+处理"的逻辑片段（避开 while True 阻塞）。"""
    await asyncio.sleep(0)  # yield to event loop
    finished: list = []
    for mac, task in list(recorder.active.items()):
        retcode = task.process.poll()
        if retcode is not None:
            finished.append((mac, retcode, task))
            continue
    for mac, retcode, task in finished:
        recorder.active.pop(mac, None)
        if retcode == 0:
            try:
                should_continue = (
                    await recorder._should_continue_cb(mac)
                    if recorder._should_continue_cb
                    else False
                )
            except Exception:
                should_continue = False
            if should_continue:
                completed = recorder._completed_indices.setdefault(mac, set())
                completed.add(task.segment_index)
                original_seg_index = task.segment_index
                if recorder._on_complete_cb:
                    await recorder._on_complete_cb(task, keep_recording=True)
                completed_tasks = recorder._completed_tasks.setdefault(mac, {})
                completed_tasks[original_seg_index] = task
                session_rec_id = task.session_recording_id or task.recording_id
                task.segment_index = task.segment_index + 1
                next_index = task.segment_index
                new_recording_id = await recorder._allocate_next_recording_id(mac)
                new_task = await recorder._restart_segment(
                    task, next_index, new_recording_id, session_recording_id=session_rec_id
                )
                recorder.active[mac] = new_task
                return True
            else:
                completed = recorder._completed_indices.setdefault(mac, set())
                completed.add(task.segment_index)
                completed_tasks = recorder._completed_tasks.setdefault(mac, {})
                completed_tasks[task.segment_index] = task
                if recorder._on_complete_cb:
                    await recorder._on_complete_cb(task)
                return False
        else:
            if recorder._on_failed_cb:
                stderr = task.process.stderr.read().decode(errors='replace')[-500:]
                await recorder._on_failed_cb(task, retcode, stderr)
    return False


@pytest.mark.asyncio
async def test_multi_segment_recording_creates_six_db_records(tmp_path, monkeypatch, db):
    """5min10s / 60s = 6 段：应产生 6 个 Recording 行和 6 个独立文件。"""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.domain.models.recording import Recording
    from app.domain.services.recording_domain import RecordingDomainService
    from app.models.camera import Camera
    from app.models.device import Device
    from app.services.nas_syncer import NasSyncer

    mac = 'AA:BB:CC:DD:EE:FF'
    db.add(Device(mac=mac, device_type='camera', is_online=True))
    camera = Camera(
        device_mac=mac, onvif_host='192.168.1.10', rtsp_url='rtsp://x', is_recording=True
    )
    db.add(camera)
    parent_rec = Recording(
        camera_mac=mac,
        file_path='(pending)',
        started_at=datetime.now(),
        status='recording',
    )
    db.add(parent_rec)
    await db.commit()
    await db.refresh(parent_rec)

    mock_nas_syncer = MagicMock(spec=NasSyncer)
    mock_nas_syncer.sync_file = MagicMock(side_effect=lambda p, m: p)
    rec_domain = RecordingDomainService(nas_syncer=mock_nas_syncer)
    rec_domain._ws_manager = MagicMock()
    rec_domain._ws_manager.broadcast = AsyncMock()
    rec_domain._probe_duration = AsyncMock(return_value=60)

    recorder = Recorder(temp_dir=str(tmp_path))
    recorder.set_callbacks(
        on_complete=rec_domain.on_recording_complete,
        on_failed=rec_domain.on_recording_failed,
        should_continue=rec_domain.should_continue_recording,
        create_next_recording=rec_domain.create_continued_recording,
    )

    ffmpeg_procs: list[_FakeProcess] = []

    def popen_factory(*args, **kwargs):
        proc = _FakeProcess()
        ffmpeg_procs.append(proc)
        return proc

    monkeypatch.setattr('app.domain.services.recorder.subprocess.Popen', popen_factory)

    await recorder.start_recording(mac, 'rtsp://x', RecordingParams(segment_seconds=60))
    assert len(ffmpeg_procs) == 1
    recorder.active[mac].recording_id = parent_rec.id
    recorder.active[mac].session_recording_id = parent_rec.id

    expected_segments = 6
    for i in range(expected_segments):
        if i >= len(ffmpeg_procs):
            break
        current_task = recorder.active.get(mac)
        if current_task is None:
            break
        _make_writeable_file(current_task.output_path)
        ffmpeg_procs[i].set_finished()
        await _run_monitor_one_tick(recorder)

    output_path = await recorder.stop_recording(mac)

    # 使用全新 session 验证（避免 db fixture 的 identity map 缓存）
    async with AsyncSessionLocal() as verify_session:
        result = await verify_session.execute(
            select(Recording).where(Recording.camera_mac == mac).order_by(Recording.id)
        )
        all_recs = result.scalars().all()
        print(f'\n[TEST] All recordings ({len(all_recs)}):')
        for r in all_recs:
            print(
                f'  id={r.id} rec_id={r.recording_id} seg_idx={r.segment_index} status={r.status}'
            )

        segment_recs = [r for r in all_recs if r.segment_index is not None]
        assert len(segment_recs) == 6, (
            f'Expected 6 per-segment Recording rows, got {len(segment_recs)}. '
            f'segment_indices: {[r.segment_index for r in segment_recs]}. '
            'Multi-segment recording is broken: ffmpeg produces N segments, '
            'but DB only stores M < N rows.'
        )

        indices = sorted([r.segment_index for r in segment_recs])
        assert indices == [0, 1, 2, 3, 4, 5], f'Expected [0,1,2,3,4,5], got {indices}'

        file_paths = [r.file_path for r in segment_recs]
        assert len(set(file_paths)) == 6, (
            f'Expected 6 distinct file_paths, got {len(set(file_paths))} unique. '
            f'Paths: {file_paths}'
        )

        statuses = [r.status for r in segment_recs]
        assert all(s == 'completed' for s in statuses), f'Some segments not completed: {statuses}'

        for fp in file_paths:
            assert Path(fp).exists(), f'File does not exist: {fp}'

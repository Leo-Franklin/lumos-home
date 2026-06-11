"""A.1 + C.7: camera_health 二次确认 + 联动停录.

- A.1: 连续 N 次失败才广播 camera_offline；连续 N 次成功才广播 camera_online。
  把 1-15s 的网络抖动误报压下去。
- C.7: 真的进入 offline 时，如果该摄像头 is_recording=True，调用注入的
  recorder.stop_recording(mac) 并把 is_recording 翻回 False，避免前端
  出现"已掉线 + 录制中"的不一致。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@pytest_asyncio.fixture
async def mem_db():
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    from app.database import Base
    from app.domain.models import (  # noqa: F401
        camera,
        device,
        device_online_log,
        dlna_device,
        member,
        recording,
        schedule,
        user_settings,
    )
    from app.models import user  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    yield Session
    await engine.dispose()


async def _seed_online_camera(session_maker, mac: str = 'AA:BB:CC:DD:EE:01'):
    from app.domain.models.camera import Camera
    from app.models.device import Device

    async with session_maker() as db:
        db.add(Device(mac=mac, device_type='camera', is_online=True))
        await db.commit()
        db.add(
            Camera(
                device_mac=mac,
                onvif_host='192.168.1.10',
                rtsp_url='rtsp://192.168.1.10:554/stream',
                is_online=True,
            )
        )
        await db.commit()


def _make_checker(session_maker, recorder=None, fail_threshold=2, success_threshold=2):
    """Build a CameraHealthChecker pointed at the in-memory DB."""
    from app.domain.services.camera_health import CameraHealthChecker

    checker = CameraHealthChecker(
        interval=60,
        fail_threshold=fail_threshold,
        success_threshold=success_threshold,
        session_factory=session_maker,
        recorder=recorder,
    )
    return checker


# ---------------------------------------------------------------------------
# A.1: consecutive confirmation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_failure_does_not_broadcast_offline(mem_db):
    await _seed_online_camera(mem_db)
    recorder = AsyncMock()
    checker = _make_checker(mem_db, recorder=recorder, fail_threshold=2)

    with (
        patch.object(checker, '_probe_rtsp', new=AsyncMock(return_value=False)),
        patch('app.domain.services.camera_health.ws_manager') as wsm,
    ):
        wsm.broadcast = AsyncMock()
        await checker._check_camera(
            'AA:BB:CC:DD:EE:01',
            'rtsp://x/y',
            None,
            None,
            was_online=True,
        )

    wsm.broadcast.assert_not_called()
    recorder.stop_recording.assert_not_called()
    # is_online 也不应该翻成 False
    async with mem_db() as db:
        from sqlalchemy import select

        from app.domain.models.camera import Camera

        cam = (
            await db.execute(select(Camera).where(Camera.device_mac == 'AA:BB:CC:DD:EE:01'))
        ).scalar_one()
        assert cam.is_online is True


@pytest.mark.asyncio
async def test_two_consecutive_failures_broadcast_offline(mem_db):
    await _seed_online_camera(mem_db)
    recorder = AsyncMock()
    checker = _make_checker(mem_db, recorder=recorder, fail_threshold=2)

    with (
        patch.object(checker, '_probe_rtsp', new=AsyncMock(return_value=False)),
        patch('app.domain.services.camera_health.ws_manager') as wsm,
    ):
        wsm.broadcast = AsyncMock()
        # 第 1 次失败 — 计数
        await checker._check_camera(
            'AA:BB:CC:DD:EE:01',
            'rtsp://x/y',
            None,
            None,
            was_online=True,
        )
        assert wsm.broadcast.await_count == 0
        # 第 2 次失败 — 阈值到，广播
        await checker._check_camera(
            'AA:BB:CC:DD:EE:01',
            'rtsp://x/y',
            None,
            None,
            was_online=True,
        )

    wsm.broadcast.assert_awaited_once()
    args, _ = wsm.broadcast.await_args
    assert args[0] == 'camera_offline'
    assert args[1] == {'mac': 'AA:BB:CC:DD:EE:01'}


@pytest.mark.asyncio
async def test_interleaved_failure_success_resets_streak(mem_db):
    await _seed_online_camera(mem_db)
    recorder = AsyncMock()
    checker = _make_checker(mem_db, recorder=recorder, fail_threshold=2)

    probe = AsyncMock(side_effect=[False, True, False, False])
    with (
        patch.object(checker, '_probe_rtsp', new=probe),
        patch('app.domain.services.camera_health.ws_manager') as wsm,
    ):
        wsm.broadcast = AsyncMock()
        # F → streak=1, not enough
        await checker._check_camera('AA:BB:CC:DD:EE:01', 'rtsp://x/y', None, None, was_online=True)
        # S → streak reset
        await checker._check_camera('AA:BB:CC:DD:EE:01', 'rtsp://x/y', None, None, was_online=True)
        # F → streak=1, not enough
        await checker._check_camera('AA:BB:CC:DD:EE:01', 'rtsp://x/y', None, None, was_online=True)
        # F → streak=2, threshold met
        await checker._check_camera('AA:BB:CC:DD:EE:01', 'rtsp://x/y', None, None, was_online=True)

    # 4 次 probe 中只应触发 1 次 broadcast（最后一次 F 累计到 2）
    assert wsm.broadcast.await_count == 1


@pytest.mark.asyncio
async def test_recovery_requires_consecutive_successes(mem_db):
    await _seed_online_camera(mem_db)
    recorder = AsyncMock()
    checker = _make_checker(mem_db, recorder=recorder, fail_threshold=2, success_threshold=2)

    with (
        patch.object(checker, '_probe_rtsp', new=AsyncMock(return_value=False)),
        patch('app.domain.services.camera_health.ws_manager') as wsm,
    ):
        wsm.broadcast = AsyncMock()
        # 进入 offline（2 次失败）
        await checker._check_camera('AA:BB:CC:DD:EE:01', 'rtsp://x/y', None, None, was_online=True)
        await checker._check_camera('AA:BB:CC:DD:EE:01', 'rtsp://x/y', None, None, was_online=True)
        assert wsm.broadcast.await_count == 1

        # 切到成功探针
        with patch.object(checker, '_probe_rtsp', new=AsyncMock(return_value=True)):
            # 第 1 次成功 — 计数，不广播
            await checker._check_camera(
                'AA:BB:CC:DD:EE:01', 'rtsp://x/y', None, None, was_online=False
            )
            assert wsm.broadcast.await_count == 1
            # 第 2 次成功 — 广播恢复
            await checker._check_camera(
                'AA:BB:CC:DD:EE:01', 'rtsp://x/y', None, None, was_online=False
            )

    assert wsm.broadcast.await_count == 2
    last_args, _ = wsm.broadcast.await_args
    assert last_args[0] == 'camera_online'


# ---------------------------------------------------------------------------
# C.7: 联动停录
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_offline_triggers_stop_recording_when_is_recording_true(mem_db):
    await _seed_online_camera(mem_db)
    recorder = AsyncMock()
    checker = _make_checker(mem_db, recorder=recorder, fail_threshold=1, success_threshold=1)

    # 把 is_recording 改成 True
    from sqlalchemy import update

    from app.domain.models.camera import Camera

    async with mem_db() as db:
        await db.execute(
            update(Camera).where(Camera.device_mac == 'AA:BB:CC:DD:EE:01').values(is_recording=True)
        )
        await db.commit()

    with (
        patch.object(checker, '_probe_rtsp', new=AsyncMock(return_value=False)),
        patch('app.domain.services.camera_health.ws_manager') as wsm,
    ):
        wsm.broadcast = AsyncMock()
        # threshold=1, 一次失败就触发
        await checker._check_camera('AA:BB:CC:DD:EE:01', 'rtsp://x/y', None, None, was_online=True)

    recorder.stop_recording.assert_awaited_once_with('AA:BB:CC:DD:EE:01')

    async with mem_db() as db:
        from sqlalchemy import select

        cam = (
            await db.execute(select(Camera).where(Camera.device_mac == 'AA:BB:CC:DD:EE:01'))
        ).scalar_one()
        assert cam.is_recording is False
        assert cam.is_online is False


@pytest.mark.asyncio
async def test_offline_does_not_call_recorder_when_not_recording(mem_db):
    await _seed_online_camera(mem_db)
    recorder = AsyncMock()
    checker = _make_checker(mem_db, recorder=recorder, fail_threshold=1, success_threshold=1)

    with (
        patch.object(checker, '_probe_rtsp', new=AsyncMock(return_value=False)),
        patch('app.domain.services.camera_health.ws_manager') as wsm,
    ):
        wsm.broadcast = AsyncMock()
        await checker._check_camera('AA:BB:CC:DD:EE:01', 'rtsp://x/y', None, None, was_online=True)

    recorder.stop_recording.assert_not_called()


@pytest.mark.asyncio
async def test_offline_without_injected_recorder_still_clears_state(mem_db):
    """recorder is None 时（单测早期实例化 / 老的装配路径）也要保证 is_recording 翻 False。"""
    await _seed_online_camera(mem_db)
    checker = _make_checker(mem_db, recorder=None, fail_threshold=1, success_threshold=1)

    from sqlalchemy import update

    from app.domain.models.camera import Camera

    async with mem_db() as db:
        await db.execute(
            update(Camera).where(Camera.device_mac == 'AA:BB:CC:DD:EE:01').values(is_recording=True)
        )
        await db.commit()

    with (
        patch.object(checker, '_probe_rtsp', new=AsyncMock(return_value=False)),
        patch('app.domain.services.camera_health.ws_manager') as wsm,
    ):
        wsm.broadcast = AsyncMock()
        await checker._check_camera('AA:BB:CC:DD:EE:01', 'rtsp://x/y', None, None, was_online=True)

    async with mem_db() as db:
        from sqlalchemy import select

        cam = (
            await db.execute(select(Camera).where(Camera.device_mac == 'AA:BB:CC:DD:EE:01'))
        ).scalar_one()
        assert cam.is_recording is False
        assert cam.is_online is False

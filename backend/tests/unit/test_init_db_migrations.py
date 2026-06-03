"""TDD 回归测试：旧版本 schema 的 DB 通过 init_db() 必须能补齐新增的 recordings 列

RED: 现状是 init_db() 缺少 recordings.recording_id / recordings.segment_index 的 ALTER TABLE，
     导致升级用户的旧 DB 直接崩溃（lifespan 启动时 OperationalError: no such column）。

GREEN: 补齐迁移后，init_db() 必须能在旧 schema 上成功创建这两个列。
"""

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest_asyncio.fixture
async def legacy_db(tmp_path):
    """创建一个 v0.0.x 时代的 smart_home.db：recordings 表只有基本列，没有 recording_id/segment_index。"""
    legacy_sqlite_path = tmp_path / 'legacy.db'
    sync_url = f'sqlite:///{legacy_sqlite_path}'
    engine = create_engine(sync_url, connect_args={'check_same_thread': False})

    with engine.begin() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_mac VARCHAR(17) NOT NULL UNIQUE,
                onvif_host VARCHAR(64) NOT NULL,
                onvif_port INTEGER DEFAULT 2020,
                onvif_user VARCHAR(64),
                onvif_password VARCHAR(256),
                rtsp_port INTEGER DEFAULT 554,
                rtsp_url TEXT,
                stream_profile VARCHAR(32) DEFAULT 'mainStream',
                is_recording BOOLEAN DEFAULT 0,
                is_online BOOLEAN NOT NULL DEFAULT 1,
                last_probe_at DATETIME,
                auto_cast_dlna VARCHAR(256),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                recording_presets JSON DEFAULT '[]',
                default_preset_id VARCHAR(36),
                FOREIGN KEY (device_mac) REFERENCES devices(mac)
            )
        """
            )
        )
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_mac VARCHAR(17) NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                duration INTEGER,
                started_at DATETIME NOT NULL,
                ended_at DATETIME,
                status VARCHAR(32) DEFAULT 'recording',
                error_msg TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (camera_mac) REFERENCES cameras(device_mac)
            )
        """
            )
        )
        conn.execute(
            text('CREATE INDEX IF NOT EXISTS ix_recordings_camera_mac ON recordings(camera_mac)')
        )
        conn.execute(
            text('CREATE INDEX IF NOT EXISTS ix_recordings_started_at ON recordings(started_at)')
        )
    engine.dispose()

    yield legacy_sqlite_path


@pytest.fixture(autouse=True)
def reset_db_engine_cache():
    """每次测试前重置 _engine / _AsyncSessionLocal 全局缓存，避免测试间污染。"""
    import app.database as db_module

    db_module._engine = None
    db_module._AsyncSessionLocal = None
    yield
    db_module._engine = None
    db_module._AsyncSessionLocal = None


@pytest.mark.asyncio
async def test_init_db_adds_recording_id_and_segment_index_columns(legacy_db, monkeypatch):
    """旧 DB 缺 recording_id / segment_index，调用 init_db() 后必须补齐。"""
    async_url = f'sqlite+aiosqlite:///{legacy_db}'

    from app.config import get_settings

    get_settings.cache_clear()
    real_settings = get_settings()
    custom_settings = real_settings.model_copy(update={'database_url': async_url})

    monkeypatch.setattr('app.config.get_settings', lambda: custom_settings)

    from app.database import init_db

    await init_db()

    aio_engine = create_async_engine(async_url)
    async with aio_engine.connect() as conn:
        result = await conn.execute(text('PRAGMA table_info(recordings)'))
        columns = {row[1] for row in result.fetchall()}

    assert 'recording_id' in columns, (
        f'recordings.recording_id 列未在 init_db() 中通过迁移创建。\n'
        f'当前列: {sorted(columns)}\n'
        '需要在 init_db() 的 migrations 列表中追加 '
        "'ALTER TABLE recordings ADD COLUMN recording_id INTEGER'。"
    )
    assert 'segment_index' in columns, (
        f'recordings.segment_index 列未在 init_db() 中通过迁移创建。\n'
        f'当前列: {sorted(columns)}\n'
        '需要在 init_db() 的 migrations 列表中追加 '
        "'ALTER TABLE recordings ADD COLUMN segment_index INTEGER'。"
    )

    async with aio_engine.connect() as conn:
        idx_result = await conn.execute(text('PRAGMA index_list(recordings)'))
        indexes = {row[1] for row in idx_result.fetchall()}
    assert 'ix_recordings_recording_id' in indexes, 'recording_id 索引未创建'
    assert 'ix_recordings_segment_index' in indexes, 'segment_index 索引未创建'

    await aio_engine.dispose()

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_init_db_is_idempotent_when_columns_already_exist(tmp_path, monkeypatch):
    """新 DB 已经在 create_all 中有这些列，再次调用 init_db() 不能抛错。"""
    new_path = tmp_path / 'fresh.db'
    async_url = f'sqlite+aiosqlite:///{new_path}'

    from app.config import get_settings

    get_settings.cache_clear()
    real_settings = get_settings()
    custom_settings = real_settings.model_copy(update={'database_url': async_url})

    monkeypatch.setattr('app.config.get_settings', lambda: custom_settings)

    from app.database import init_db

    # 第一次：创建表 + 跑迁移（应该全部幂等）
    await init_db()
    # 第二次：迁移都应被 try/except 吞掉，不应抛错
    await init_db()

    get_settings.cache_clear()

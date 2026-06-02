import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger


def _copy_with_retry(src: str, dest: str, max_retries: int = 5) -> None:
    """Copy file with retry for transient file locks (Windows)."""
    last_err = None
    for attempt in range(max_retries):
        try:
            shutil.copy2(src, dest)
            return
        except OSError as e:
            last_err = e
            if attempt < max_retries - 1:
                wait = 0.5 * (2**attempt)
                logger.warning(
                    f'文件被占用，{wait:.1f}s后重试 ({attempt + 1}/{max_retries}): {src}'
                )
                time.sleep(wait)
    raise last_err  # type: ignore[misc]


class NasSyncer:
    def __init__(
        self,
        mode: str,
        mount_path: str = '',
        local_storage_path: str = '',
        smb_host: str = '',
        smb_share: str = '',
        smb_user: str = '',
        smb_password: str = '',
    ):
        self.mode = mode
        self.mount_path = Path(mount_path) if mount_path else None
        self.local_storage_path = (
            Path(local_storage_path).resolve()
            if local_storage_path
            else Path('./data/recordings').resolve()
        )
        self.smb_config = {
            'host': smb_host,
            'share': smb_share,
            'user': smb_user,
            'password': smb_password,
        }

    def sync_file(self, src: Path, camera_mac: str) -> Path:
        date_dir = datetime.now(UTC).strftime('%Y-%m-%d')
        safe_mac = camera_mac.replace(':', '')
        relative = f'{safe_mac}/{date_dir}/{src.name}'
        if self.mode == 'local':
            return self._sync_to_local(src, relative)
        elif self.mode == 'mount':
            return self._sync_via_mount(src, relative)
        elif self.mode == 'smb':
            return self._sync_via_smb(src, relative)
        else:
            raise ValueError(f'未知 NAS_MODE: {self.mode}')

    def _sync_to_local(self, src: Path, relative: str) -> Path:
        dest = self.local_storage_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f'本地存储: {src} → {dest}')
        _copy_with_retry(str(src), str(dest))
        try:
            src.unlink()
        except OSError as e:
            logger.warning(f'临时文件稍后清理（文件仍被占用）: {src} — {e.strerror}')
        return dest

    def _sync_via_mount(self, src: Path, relative: str) -> Path:
        assert self.mount_path is not None, 'mount_path must be set for mount mode'
        dest = self.mount_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f'NAS同步(mount): {src} → {dest}')
        _copy_with_retry(str(src), str(dest))
        try:
            src.unlink()
        except OSError as e:
            logger.warning(f'临时文件稍后清理（文件仍被占用）: {src} — {e.strerror}')
        return dest

    def _sync_via_smb(self, src: Path, remote_path: str) -> Path:
        from smbclient import open_file, register_session

        register_session(
            self.smb_config['host'],
            username=self.smb_config['user'],
            password=self.smb_config['password'],
        )
        share = self.smb_config['share']
        full_remote = f'\\\\{self.smb_config["host"]}\\{share}\\{remote_path}'
        logger.info(f'NAS同步(SMB): {src} → {full_remote}')
        with open(src, 'rb') as local_f:
            with open_file(full_remote, mode='wb') as remote_f:
                shutil.copyfileobj(local_f, remote_f, length=1024 * 1024)
        src.unlink()
        return Path(full_remote)

    def check_writable(self) -> bool:
        try:
            if self.mode == 'local':
                self.local_storage_path.mkdir(parents=True, exist_ok=True)
                test_file = self.local_storage_path / '.health_check'
                test_file.write_text('ok')
                test_file.unlink()
                return True
            elif self.mode == 'mount' and self.mount_path:
                test_file = self.mount_path / '.health_check'
                test_file.write_text('ok')
                test_file.unlink()
                return True
            elif self.mode == 'smb':
                from smbclient import register_session

                register_session(
                    self.smb_config['host'],
                    username=self.smb_config['user'],
                    password=self.smb_config['password'],
                )
                return True
            return False
        except Exception as e:  # noqa: BLE001 — smbprotocol/socket/auth 边界,任意异常都视为不可达
            logger.error(f'NAS 健康检查失败: {e}')
            return False

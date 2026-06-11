"""Go2RtcRunner — start/stop embedded go2rtc binary."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from loguru import logger

from app.config import is_packaged


def _exe_dir() -> Path:
    return Path(sys.executable).parent


def resolve_go2rtc_binary(*, explicit: str = '') -> Path | None:
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None
    if is_packaged():
        candidate = _exe_dir() / 'go2rtc' / 'go2rtc.exe'
        return candidate if candidate.is_file() else None
    return None


def should_start_embedded_runner(*, go2rtc_enabled: bool, binary: Path | None) -> bool:
    """True only when Lumos should spawn a local go2rtc subprocess (Windows installer)."""
    return go2rtc_enabled and binary is not None


def read_webrtc_candidates(path: Path) -> list[str]:
    if not path.is_file():
        return []
    candidates: list[str] = []
    in_candidates = False
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if line == 'candidates:':
            in_candidates = True
            continue
        if in_candidates:
            if line.startswith('- '):
                candidates.append(line[2:].strip())
            elif line and not line.startswith('#'):
                in_candidates = False
    return candidates


def write_go2rtc_config(
    path: Path,
    *,
    api_port: int = 1984,
    rtsp_port: int = 8554,
    webrtc_port: int = 8555,
    webrtc_candidates: list[str] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        'api:',
        f'  listen: "127.0.0.1:{api_port}"',
        'rtsp:',
        f'  listen: ":{rtsp_port}"',
        'webrtc:',
        f'  listen: ":{webrtc_port}"',
    ]
    if webrtc_candidates:
        lines.append('  candidates:')
        lines.extend(f'    - {item}' for item in webrtc_candidates)
    lines.append('streams: {}')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


class Go2RtcRunner:
    def __init__(self):
        self._process: subprocess.Popen | None = None

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self, *, binary: Path, config_path: Path) -> None:
        if self.is_running():
            return
        cmd = [str(binary), '-config', str(config_path)]
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f'go2rtc 已启动 pid={self._process.pid}')

    def stop(self) -> None:
        proc = self._process
        self._process = None
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            try:
                proc.kill()
                proc.wait(timeout=3)
            except (subprocess.TimeoutExpired, OSError):
                pass
        logger.info('go2rtc 已停止')

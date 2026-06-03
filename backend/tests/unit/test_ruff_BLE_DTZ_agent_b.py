"""Contract test: app/api/ must have ZERO BLE001 + DTZ005 violations.

Scans the api directory (excluding test runners) via ruff and asserts
the count is exactly 0. M+N agent B's scope is restricted to
``app/api/`` — if any handler file grows a blind ``except Exception``
or a naive ``datetime.now()``, this test fails.

Why a contract test (and not just a ruff CI run)?
- The CI ruff command is a single sweep that may be skipped locally
  with ``--no-verify``; this pytest test runs in the same invocation
  as the rest of the suite and gates the build.
- A regression here is loud (visible red bar) instead of silent
  (lint config drift).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_DIR = _REPO_ROOT / 'app' / 'api'


def _run_ruff() -> str:
    """Return ruff's ``--output-format=concise`` output for app/api/.

    Empty string = clean.
    """
    if shutil.which('ruff') is None:
        pytest.skip('ruff binary not on PATH')
    result = subprocess.run(
        [
            'uv',
            'run',
            'ruff',
            'check',
            str(_API_DIR),
            '--select=BLE001,DTZ005',
            '--output-format=concise',
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # ruff prints errors to stdout when --output-format=concise; if all
    # clean it prints "All checks passed!" — treat that as no violations.
    out = result.stdout.strip()
    if out.startswith('All checks passed'):
        return ''
    return out


def test_app_api_has_no_BLE001_or_DTZ005():
    """app/api/* must satisfy BLE001 (narrow except) and DTZ005 (tz-aware now)."""
    assert _API_DIR.is_dir(), f'{_API_DIR} missing — repo layout changed?'

    output = _run_ruff()
    assert not output, (
        'app/api/ has ruff BLE001/DTZ005 violations — fix per '
        '`M+N B: app/api/* files` rules:\n'
        '- BLE001: narrow except (OSError/TimeoutError/SQLAlchemyError) OR keep '
        '`except Exception` with `# noqa: BLE001` + log + explicit HTTPException\n'
        '- DTZ005: use `datetime.now(timezone.utc)`, OR keep naive + `# noqa: '
        'DTZ005` only when comparing against a SQLAlchemy DateTime column '
        'without tzinfo=True\n'
        f'\n{output}'
    )

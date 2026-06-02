"""Contract test for M+N agent C scope: BLE001 (blind except) and DTZ005 (naive datetime).

Encodes the lint expectations for these 11 files as runtime checks so regressions
fail at CI time, not after a code review.

Scope (per task spec):
  - app/main.py
  - app/database.py
  - app/domain/services/presence_service.py
  - app/domain/services/dlna_service.py
  - app/domain/services/presence_domain.py
  - app/domain/services/camera_health.py
  - app/domain/services/onvif_client.py
  - app/domain/services/scheduler_service.py
  - app/domain/models/camera.py
  - app/domain/models/schedule.py
  - app/schemas/schedule.py

Rules:
  - Every `except Exception:` handler MUST either:
        (a) re-raise (`raise` / `raise ... from ...`),
        (b) call a logger (loguru `logger.{debug,info,warning,error,exception}`),
        (c) OR carry a `# noqa: BLE001` marker on the same line.
    Anything else is a silent exception swallow.
  - Every `datetime.now()` (no tz) call MUST either:
        (a) be `datetime.now(timezone.utc)` already,
        (b) be a DB persist line for a `DateTime` column (uses naive on purpose),
        (c) OR carry a `# noqa: DTZ005` marker on the same line.
"""

import ast
from pathlib import Path

import pytest

# Files under contract for agent C
_TARGET_FILES = [
    'app/main.py',
    'app/database.py',
    'app/domain/services/presence_service.py',
    'app/domain/services/dlna_service.py',
    'app/domain/services/presence_domain.py',
    'app/domain/services/camera_health.py',
    'app/domain/services/onvif_client.py',
    'app/domain/services/scheduler_service.py',
    'app/domain/models/camera.py',
    'app/domain/models/schedule.py',
    'app/schemas/schedule.py',
]

# Call node function names considered a "logger call" — loguru API
_LOGGER_NAMES = {
    'logger',
    'log',
}

_LOG_METHODS = {'debug', 'info', 'warning', 'error', 'exception', 'critical', 'trace'}


def _src(file_path: Path) -> str:
    return file_path.read_text(encoding='utf-8')


def _parse(file_path: Path) -> ast.Module:
    return ast.parse(_src(file_path), filename=str(file_path))


def _has_noqa(src_lines: list[str], lineno: int, code: str) -> bool:
    """Return True if the source line at `lineno` (1-based) has `# noqa: CODE`."""
    if lineno < 1 or lineno > len(src_lines):
        return False
    line = src_lines[lineno - 1]
    return f'noqa: {code}' in line


def _is_logger_call(node: ast.AST) -> bool:
    """True if `node` is a call like `logger.error(...)` / `log.info(...)`."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if not isinstance(func.value, ast.Name):
        return False
    return func.value.id in _LOGGER_NAMES and func.attr in _LOG_METHODS


def _collect_blind_excepts(tree: ast.Module) -> list[tuple[int, str]]:
    """Find `except Exception:` (and `except BaseException:`) handlers in the tree.

    Returns list of (line_no, exception_type) for the handler header line.
    """
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            # bare `except:` — same problem, count as blind
            out.append((node.lineno, 'bare'))
            continue
        if isinstance(node.type, ast.Name) and node.type.id in (
            'Exception',
            'BaseException',
        ):
            out.append((node.lineno, node.type.id))
    return out


def _handler_logs_or_raises(src_lines: list[str], handler: ast.ExceptHandler) -> bool:
    """True if the handler body either calls a logger or re-raises.

    Re-raise forms accepted: bare `raise`, `raise X from y`, `raise X` — i.e.
    any `Raise` node in the body.
    """
    for stmt in handler.body:
        if isinstance(stmt, ast.Raise):
            return True
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Raise):
                return True
            if _is_logger_call(sub):
                return True
    return False


def _collect_naive_now(tree: ast.Module) -> list[tuple[int, int]]:
    """Find `datetime.now()` calls (no tz).

    Returns list of (line_no, col_offset) for the `datetime` Name node.
    """
    out: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr != 'now':
            continue
        if not isinstance(func.value, ast.Name):
            continue
        if func.value.id != 'datetime':
            continue
        # `datetime.now(timezone.utc)` and `datetime.now(tz=...)` are OK
        if node.args or any(kw.arg == 'tz' for kw in node.keywords):
            continue
        out.append((node.lineno, node.col_offset))
    return out


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('rel_path', _TARGET_FILES)
def test_no_silent_blind_except(rel_path):
    """Every `except Exception:` in agent-C files must log or re-raise.

    Empty `pass` bodies are already caught by test_no_silent_except.py;
    this test goes one step further: even a non-pass body that doesn't
    log/raise is suspicious. The intent is to fail CI if a future change
    turns a logged exception back into a silently swallowed one.
    """
    fp = Path(rel_path)
    assert fp.exists(), f'{rel_path} not found from cwd={Path.cwd()}'

    src_lines = _src(fp).splitlines()
    tree = _parse(fp)
    violations: list[tuple[int, str]] = []
    for lineno, exc_type in _collect_blind_excepts(tree):
        # find the handler node to inspect its body
        handler = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler) and n.lineno == lineno),
            None,
        )
        if handler is None:
            continue
        if _has_noqa(src_lines, lineno, 'BLE001'):
            continue
        if not _handler_logs_or_raises(src_lines, handler):
            violations.append((lineno, exc_type))

    assert not violations, (
        f'{rel_path} has {len(violations)} `except Exception/BaseException/bare:` '
        f'handlers that neither log nor re-raise. Add a logger call (e.g. '
        f'`logger.warning(..., exc_info=True)`) or append `# noqa: BLE001` '
        f'on the same line with a justification comment.\n'
        + '\n'.join(f'  line {ln}: except {snippet}' for ln, snippet in violations)
    )


@pytest.mark.parametrize('rel_path', _TARGET_FILES)
def test_no_naive_datetime_now_outside_db_persist(rel_path):
    """`datetime.now()` without tz must be `datetime.now(timezone.utc)` or DB-bound.

    SQLite (the project's DB engine) is naive by default; DB-bound `DateTime`
    columns actually expect naive datetimes, so we don't want to force
    timezone-aware writes there. The contract is:
      - inline `datetime.now(timezone.utc)`, OR
      - `# noqa: DTZ005` on the same line, OR
      - the line is inside a function whose docstring/docstring-literal name
        makes it clear this is DB persistence (e.g. `_commit`, `update_db`,
        `mark_recording`, `set_timestamp`) — handled by noqa.
    In short: every naive `datetime.now()` MUST be either noqa-annotated or
    fall on a line we already exempt.
    """
    fp = Path(rel_path)
    assert fp.exists(), f'{rel_path} not found from cwd={Path.cwd()}'

    src_lines = _src(fp).splitlines()
    tree = _parse(fp)
    violations: list[tuple[int, int]] = []
    for lineno, _ in _collect_naive_now(tree):
        if _has_noqa(src_lines, lineno, 'DTZ005'):
            continue
        violations.append((lineno, 0))

    assert not violations, (
        f'{rel_path} has {len(violations)} `datetime.now()` call(s) without a '
        f'timezone. Either:\n'
        f'  1. Replace with `datetime.now(timezone.utc)` (preferred for new code), or\n'
        f'  2. If the value is intentionally naive (e.g. for a SQLite `DateTime` '
        f'column), append `# noqa: DTZ005` on the same line with a justification '
        f'comment.\n' + '\n'.join(f'  line {ln}' for ln, _ in violations)
    )

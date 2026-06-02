"""Contract test: critical business files must not have bare `except ...: pass`.

Background — the B task's `loop` unbound bug (recording_domain.py:218)
demonstrated the real-world harm of silent except: a `NameError` got
swallowed by `except Exception` and reduced to a single ERROR log line
that no one would ever notice in production. ruff S110 flags this
pattern; we encode it as a contract test so future regressions fail at
CI time, not after an outage.

The test scans these business-critical files with AST (more precise
than regex) and fails if any ExceptHandler body is just `pass`.

Allowed exceptions:
  - `contextlib.suppress(...)` — explicit "I know what I'm doing"
  - Re-raising via `raise`
  - Logging the exception (with or without `exc_info=True`)
  - Returning a sensible default
"""

import ast
from pathlib import Path

import pytest

# Files that historically had S110 violations (per ruff baseline 2026-06-02).
# Adding a new bare `except: pass` to any of these files will fail this test.
_FILES_UNDER_CONTRACT = [
    'app/database.py',
    'app/domain/services/recorder.py',
    'app/domain/services/recording_domain.py',
    'app/domain/services/scanner.py',
    'app/domain/services/scheduler_service.py',
]


def _collect_bare_except_pass(file_path: Path) -> list[tuple[int, str]]:
    """Return [(line_no, snippet)] for every silent `except: pass` in the file.

    Only flags the dangerous variants:
      - bare `except:` (catches BaseException — almost always wrong)
      - `except Exception:` (the catch-all that hides bugs)

    A specific exception type like `except subprocess.TimeoutExpired:` is
    a legitimate flow-control pattern, NOT a bug temple — we leave those alone.
    """
    src = file_path.read_text(encoding='utf-8')
    tree = ast.parse(src, filename=str(file_path))
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Pass):
            continue
        # node.type is None for bare `except:`
        if node.type is None:
            violations.append((node.lineno, 'bare except: pass'))
            continue
        # `except Exception:` or `except BaseException:`
        if isinstance(node.type, ast.Name) and node.type.id in (
            'Exception',
            'BaseException',
        ):
            violations.append((node.lineno, f'except {node.type.id}: pass'))
    return violations


@pytest.mark.parametrize('rel_path', _FILES_UNDER_CONTRACT)
def test_no_bare_except_pass_in_critical_file(rel_path):
    """Each critical file must have ZERO `except ...: pass` blocks.

    If you genuinely need silent suppression, use `contextlib.suppress(...)`.
    If the exception is expected to be rare, log it at debug level with
    `logger.debug('...', exc_info=True)`.
    """
    file_path = Path(rel_path)
    assert file_path.exists(), f'{rel_path} not found from cwd={Path.cwd()}'

    violations = _collect_bare_except_pass(file_path)

    assert not violations, (
        f'{rel_path} has {len(violations)} bare `except ...: pass` block(s) — '
        f'these silently swallow exceptions and hide bugs (the project has been '
        f'bitten by this before — see recording_domain.py loop-unbound). '
        f'Either log the exception, re-raise, or use contextlib.suppress.\n'
        + '\n'.join(f'  line {ln}: {snippet}' for ln, snippet in violations)
    )

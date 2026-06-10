"""Contract test: BLE001 + DTZ005 must be clean in agent A's target files.

The scanner domain was split into ``app/domain/services/scanner/``; all
package modules are included here alongside recorder and recording_domain.
The test invokes ruff directly and asserts zero violations for each rule.
"""

import subprocess
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_SCANNER_FILES = [
    'app/domain/services/scanner/__init__.py',
    'app/domain/services/scanner/constants.py',
    'app/domain/services/scanner/enrichment.py',
    'app/domain/services/scanner/metadata.py',
    'app/domain/services/scanner/network.py',
    'app/domain/services/scanner/pipeline.py',
    'app/domain/services/scanner/probe.py',
]

FILES = [
    *_SCANNER_FILES,
    'app/domain/services/recorder.py',
    'app/domain/services/recording_domain.py',
]


def _run_ruff(rule: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['uv', 'run', 'ruff', 'check', *FILES, f'--select={rule}', '--output-format=concise'],
        capture_output=True,
        text=True,
        cwd=_BACKEND_ROOT,
    )


@pytest.mark.parametrize('rule', ['BLE001', 'DTZ005'])
def test_ruff_rule_clean(rule):
    """Agent A target files must contain zero violations of the given rule."""
    result = _run_ruff(rule)
    if result.returncode == 0:
        return
    lines = [line for line in result.stdout.splitlines() if rule in line]
    assert not lines, f'{rule} violations in agent A target files:\n' + '\n'.join(lines)

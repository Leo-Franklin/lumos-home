"""Contract test: BLE001 + DTZ005 must be clean in agent A's 3 target files.

These 3 files are: scanner.py, recorder.py, recording_domain.py.
The test invokes ruff directly and asserts zero violations for each rule.
"""

import subprocess

import pytest

FILES = [
    'app/domain/services/scanner.py',
    'app/domain/services/recorder.py',
    'app/domain/services/recording_domain.py',
]


def _run_ruff(rule: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['uv', 'run', 'ruff', 'check', *FILES, f'--select={rule}', '--output-format=concise'],
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize('rule', ['BLE001', 'DTZ005'])
def test_ruff_rule_clean(rule):
    """The 3 target files must contain zero violations of the given rule."""
    result = _run_ruff(rule)
    # ruff returns 0 when clean, 1 when violations exist
    if result.returncode == 0:
        return  # clean
    # Extract only the lines that report this rule
    lines = [line for line in result.stdout.splitlines() if rule in line]
    assert not lines, f'{rule} violations in agent A target files:\n' + '\n'.join(lines)

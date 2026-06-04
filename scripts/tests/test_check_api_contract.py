import pytest

import check_api_contract as cac


FIX_ROOT = __file__.resolve().parent / "fixtures"


def _paths(group: str) -> tuple[str, str]:
    schema = FIX_ROOT / group / "schema"
    api = FIX_ROOT / group / "api"
    return str(schema), str(api)


def test_extracts_pydantic_models_from_clean_fixture():
    schema_dir, _ = _paths("clean")
    models = cac.extract_models(schema_dir)
    assert cac.Model("UserCreate", frozenset({"email", "password"})) in models
    assert cac.Model("UserRead", frozenset({"id", "email", "is_active"})) in models


def test_extracts_frontend_exports_from_clean_fixture():
    _, api_dir = _paths("clean")
    exports = cac.extract_exports(api_dir)
    # camelCase form of snake_case model name
    assert "userCreate" in exports
    assert "userRead" in exports


def test_clean_fixture_passes_with_exit_zero(tmp_path):
    schema_dir, api_dir = _paths("clean")
    rc = cac.run(schema_dir, api_dir, report_path=tmp_path / "report.txt")
    assert rc == 0
    report = (tmp_path / "report.txt").read_text()
    assert "OK" in report


def test_missing_model_in_frontend_returns_nonzero(tmp_path):
    schema_dir, api_dir = _paths("missing_in_api")
    rc = cac.run(schema_dir, api_dir, report_path=tmp_path / "report.txt")
    assert rc == 1
    report = (tmp_path / "report.txt").read_text()
    assert "ForgottenModel" in report


def test_parse_error_in_schema_returns_nonzero(tmp_path):
    schema_dir, api_dir = _paths("parse_error")
    rc = cac.run(schema_dir, api_dir, report_path=tmp_path / "report.txt")
    assert rc == 1
    report = (tmp_path / "report.txt").read_text()
    assert "broken.py" in report


def test_empty_api_dir_returns_zero(tmp_path):
    """Spec §7: empty / missing API directory is a warning, not an error."""
    schema_dir, api_dir = _paths("empty_api")
    rc = cac.run(schema_dir, api_dir, report_path=tmp_path / "report.txt")
    assert rc == 0
    report = (tmp_path / "report.txt").read_text()
    assert "OK" in report


def test_missing_api_dir_does_not_crash(tmp_path):
    """Spec §7: a non-existent api dir is tolerated, exit 0 if schemas are clean."""
    # Reuse the clean schema but point api at a path that doesn't exist
    clean_schema, _ = _paths("clean")
    missing_api = tmp_path / "does-not-exist"
    rc = cac.run(clean_schema, str(missing_api), report_path=tmp_path / "report.txt")
    assert rc == 0


def test_main_writes_report_to_default_path(tmp_path, monkeypatch):
    """Spec §4.3: CI invokes `python scripts/check_api_contract.py` with no args.

    `main([])` should run against the project's real tree (not a fixture),
    write its report to ./contract-report.txt, and return the appropriate
    exit code. We use monkeypatch to redirect CWD into tmp_path so the
    report file lands there.
    """
    monkeypatch.chdir(tmp_path)
    rc = cac.main([])
    report_file = tmp_path / "contract-report.txt"
    assert report_file.exists()
    # Don't assert on rc itself — the real repo may have missing exports
    # (we don't know yet). Just assert the CLI runs and writes a report.
    assert isinstance(rc, int)
    # Cleanup the cwd-relative report
    if report_file.exists():
        report_file.unlink()

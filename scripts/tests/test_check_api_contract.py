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

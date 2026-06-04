"""API contract check.

Enforces the project invariant (see .claude/CLAUDE.md §2.1): every Pydantic
model in backend/app/schemas/ must have a corresponding exported identifier
in frontend/src/api/. Compares model names case-insensitively, normalising
between snake_case (Python) and camelCase (JS).

Returns exit code 0 on success, 1 on any failure (missing match or parse
error). Writes a human-readable report to the path given by --report.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Model:
    name: str


def _to_camel(name: str) -> str:
    """Convert snake_case (or PascalCase) identifier to camelCase."""
    if not name:
        return name
    # PascalCase -> snake_case
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def _normalise(name: str) -> str:
    """Lowercase, strip underscores — used to compare across casing styles."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def extract_models(schema_dir: str) -> set[Model]:
    """Walk schema_dir, return set of Model found in Pydantic BaseModel subclasses."""
    out: set[Model] = set()
    for py in Path(schema_dir).rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError as e:
            raise SyntaxError(f"parse error in {py}: {e}") from e
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            # Heuristic: a class with at least one AnnAssign is a pydantic-like
            # model. We do NOT try to verify it actually inherits BaseModel (that
            # would require resolving imports) — false positives are tolerable;
            # false negatives are not.
            has_typed_field = any(
                isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
                for stmt in node.body
            )
            if has_typed_field:
                out.add(Model(name=node.name))
    return out


_JS_IDENT = re.compile(r"export\s+(?:async\s+)?function\s+([A-Za-z_$][\w$]*)")
_JS_CONST = re.compile(r"export\s+const\s+([A-Za-z_$][\w$]*)")
_JS_LET = re.compile(r"export\s+let\s+([A-Za-z_$][\w$]*)")
_JS_VAR = re.compile(r"export\s+var\s+([A-Za-z_$][\w$]*)")
_JS_RENAMED = re.compile(
    r"export\s*\{\s*[A-Za-z_$][\w$]*\s+as\s+([A-Za-z_$][\w$]*)\s*\}"
)


def extract_exports(api_dir: str) -> set[str]:
    """Walk api_dir, return set of exported camelCase identifiers."""
    out: set[str] = set()
    if not Path(api_dir).exists():
        return out
    for js in Path(api_dir).rglob("*.js"):
        text = js.read_text(encoding="utf-8")
        for pat in (_JS_IDENT, _JS_CONST, _JS_LET, _JS_VAR, _JS_RENAMED):
            for m in pat.finditer(text):
                out.add(_to_camel(m.group(1)))
    return out


def run(schema_dir: str, api_dir: str, report_path: Path) -> int:
    """Compare models and exports, write a report, return exit code."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        models = extract_models(schema_dir)
    except SyntaxError as e:
        report_path.write_text(f"ERROR: {e}\n", encoding="utf-8")
        return 1
    # Spec §7: a missing api directory is a WARNING, not an error. But a
    # directory that exists with .js files in it (even if they have no
    # exports) is a real project state — the models are genuinely missing
    # from the frontend and the run should fail.
    api_path = Path(api_dir)
    if not api_path.exists() or not any(api_path.rglob("*.js")):
        report_path.write_text(
            f"OK: {len(models)} model(s) in schema; api directory is empty or "
            f"missing, skipping contract check (warning only).\n",
            encoding="utf-8",
        )
        return 0
    exports = extract_exports(api_dir)
    # Normalise both sides for comparison; spec says case-insensitive, ignoring
    # underscores so snake_case and camelCase line up.
    norm_exports = {_normalise(e) for e in exports}

    missing: list[str] = []
    for m in models:
        if _normalise(m.name) not in norm_exports:
            missing.append(m.name)

    lines: list[str] = []
    if missing:
        lines.append("FAIL: backend models without a matching frontend export:")
        for name in sorted(missing):
            lines.append(f"   - {name}")
        lines.append("")
        lines.append("Add or update a file under frontend/src/api/ that exports an")
        lines.append("identifier with the same base name (camelCase form is fine).")
    else:
        lines.append(f"OK: {len(models)} model(s) matched against frontend exports")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if not missing else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--schema-dir",
        default="backend/app/schemas",
        help="Directory containing backend Pydantic models (default: %(default)s)",
    )
    p.add_argument(
        "--api-dir",
        default="frontend/src/api",
        help="Directory containing frontend API client modules (default: %(default)s)",
    )
    p.add_argument(
        "--report",
        default="contract-report.txt",
        help="Where to write the human-readable report (default: %(default)s)",
    )
    args = p.parse_args(argv)
    return run(args.schema_dir, args.api_dir, Path(args.report))


if __name__ == "__main__":
    sys.exit(main())

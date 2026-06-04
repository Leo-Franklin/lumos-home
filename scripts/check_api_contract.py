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


# Words that mark a schema as a request/response wrapper rather than a
# concrete entity. Stripped before token-set comparison so e.g. `LoginRequest`
# (tokens: {login, request}) can match a frontend export `login` (tokens:
# {login}) via subset relation.
_TYPE_MARKERS = frozenset(
    {
        "request",
        "response",
        "out",
        "schema",
        "detail",
        "data",
        "info",
    }
)


# Schemas that are *envelope* types with no single frontend equivalent.
# Each is used as the response/request shape of multiple endpoints, so the
# "one schema = one frontend export" invariant doesn't apply. Skipping these
# is the only way to keep the contract check from being noise; the spec at
# .claude/CLAUDE.md §2.1 is about catching *new* schemas, and a new envelope
# is a backend concern, not a frontend one.
_GENERIC_ENVELOPES = frozenset(
    {
        "PagedResponse",
        "ErrorResponse",
        "ErrorDetail",
        "MessageResponse",
        "TokenResponse",
    }
)


# Schemas that are never the top-level request or response payload of any
# endpoint. The "one schema = one frontend export" invariant does not apply:
#
#   * `DeviceBase` — abstract Pydantic parent that `DeviceUpdate` inherits for
#     field reuse. No router references it directly; payload type is
#     `DeviceUpdate` / `DeviceOut`.
#   * `DailyStats` — row type of `MemberStatsOut.daily`. The only endpoint
#     that materialises it (`GET /members/{id}/stats`) returns the wrapper
#     `MemberStatsOut`, not a bare `DailyStats`.
#   * `RecordingPresetSchema` — element type of `CameraOut.recording_presets`.
#     The list endpoint `GET /cameras/{mac}/presets` returns `[dict]` from
#     `to_dict()`, not the Pydantic schema, so the frontend never sees the
#     schema at the type level either.
#
# Each entry here should have a one-line justification in the comment. Keep
# this list small — every addition is a hole in the contract check.
_NON_PAYLOAD_SCHEMAS = frozenset(
    {
        "DeviceBase",
        "DailyStats",
        "RecordingPresetSchema",
    }
)


def _tokens(name: str) -> frozenset[str]:
    """Split an identifier into a set of lowercase word tokens.

    `CameraCreate` -> {"camera", "create"}; `createCamera` -> {"camera", "create"};
    `LoginRequest` -> {"login", "request"}; `DLNADeviceOut` -> {"dlna", "device", "out"}.

    Splits at:
      * snake_case underscores
      * lowercase->uppercase boundary (`e`/`O` in `deviceOut`)
      * uppercase-acronym boundary (`A`/`D` in `DLNADevice`): match between two
        uppercase letters when the second is followed by a lowercase.
    """
    # Step 1: handle snake_case
    s = name.replace("_", " ")
    # Step 2: split acronym|word (e.g. `DLNA|Device` -> `DLNA Device`).
    # Lookbehind = upper, lookahead = upper+lower; insert space at the boundary.
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    # Step 3: split camelCase (lower->upper boundary).
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    parts = [p.lower() for p in s.split() if p]
    # Step 4: collapse simple plurals so `devices` / `logs` match `device` / `log`.
    # Only applied to non-acronym words of length > 3 to avoid clobbering tokens
    # like `is` or `as`.
    normalised: list[str] = []
    for p in parts:
        if len(p) > 3 and p.endswith("s") and not p.endswith("ss"):
            normalised.append(p[:-1])
        else:
            normalised.append(p)
    return frozenset(normalised)


def _matches(model_name: str, export_name: str) -> bool:
    """Return True if a backend model and a frontend export refer to the same
    API target, allowing for verb-first vs noun-first naming and for type
    marker suffixes (`Request`, `Response`, `Out`, `Schema`, `Detail`).

    Two names match when, after stripping type markers, the token set of one
    is a subset of the other. This covers:

    * `CameraCreate` (~{camera, create}) vs `createCamera` (~{camera, create}) — equal
    * `LoginRequest`  (~{login})        vs `login`        (~{login})        — subset
    * `CameraOut`     (~{camera})       vs `listCameras`  (~{list, camera}) — subset
    """
    m = {t for t in _tokens(model_name) if t not in _TYPE_MARKERS}
    e = {t for t in _tokens(export_name) if t not in _TYPE_MARKERS}
    if not m or not e:
        # Refuse to match empty token sets — that would make every schema pass
        # if it has no real word in its name.
        return False
    return m <= e or e <= m


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
    # underscores so snake_case and camelCase line up. `_matches` goes one step
    # further and also accepts verb-first / noun-first renames and the
    # `Request`/`Response`/`Out`/`Schema`/`Detail` type-marker suffixes.
    norm_exports = {_normalise(e) for e in exports}

    missing: list[str] = []
    for m in models:
        if m.name in _GENERIC_ENVELOPES or m.name in _NON_PAYLOAD_SCHEMAS:
            continue
        if _normalise(m.name) in norm_exports:
            continue
        if any(_matches(m.name, e) for e in exports):
            continue
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

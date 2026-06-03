#!/usr/bin/env bash
# Dev-only helper: create a relative symlink at backend/frontend pointing
# to frontend/dist so the FastAPI dev server can serve the built SPA.
# Run from the repo root. Idempotent.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINK_PATH="$REPO_ROOT/backend/frontend"
TARGET="$REPO_ROOT/frontend/dist"

if [ ! -d "$TARGET" ]; then
    echo "frontend/dist/ not found. Run 'pnpm --dir frontend build' first." >&2
    exit 1
fi

rm -rf "$LINK_PATH"
ln -s "../../frontend/dist" "$LINK_PATH"
echo "Created symlink: $LINK_PATH -> ../../frontend/dist"
echo "Done. Restart the backend dev server to pick up the static mount."

#!/usr/bin/env bash
# Test BuildAppWorkflow end-to-end without running Temporal server.
# Exercises the same code paths as BuildDOQLActivity:
#   bundle → bundle-to-doql.py → app.doql.css → doql build
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE="${1:-bundles/generated/llm-multi-platform-app.json}"
BUNDLE_PATH="$ROOT/$BUNDLE"

echo "=== BuildAppWorkflow Test ==="
echo "Bundle: $BUNDLE_PATH"

if [ ! -f "$BUNDLE_PATH" ]; then
    echo "Error: bundle not found: $BUNDLE_PATH"
    exit 1
fi

# Step 1: Generate DOQL CSS (mirrors BuildDOQLActivity step 3)
echo ""
echo "[1/3] Generating DOQL app.doql.css..."
mkdir -p "$ROOT/generated"
python3 "$ROOT/scripts/bundle-to-doql.py" "$BUNDLE_PATH" > "$ROOT/generated/app.doql.css"
echo "✓ Generated: $ROOT/generated/app.doql.css"

# Step 2: DOQL validate + plan
echo ""
echo "[2/3] DOQL validate + plan..."
cd "$ROOT"
/home/tom/github/oqlos/venv/bin/python -m doql.cli -f generated/app.doql.css validate
/home/tom/github/oqlos/venv/bin/python -m doql.cli -f generated/app.doql.css plan

# Step 3: DOQL build
echo ""
echo "[3/3] DOQL build..."
/home/tom/github/oqlos/venv/bin/python -m doql.cli -f generated/app.doql.css build
echo "✓ Build artifacts in $ROOT/generated/build/"

echo ""
echo "=== BuildAppWorkflow Test PASSED ==="
echo "Artifacts:"
find "$ROOT/generated/build" -type f | head -20

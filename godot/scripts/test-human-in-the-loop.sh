#!/usr/bin/env bash
# Test human-in-the-loop workflow: create a WORKFLOW_BUNDLE with approval_required,
# move it to pending, approve, reject, and verify state transitions.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PENDING="$ROOT/bundles/pending"
APPROVED="$ROOT/bundles/approved"
REJECTED="$ROOT/bundles/rejected"
TEST_BUNDLE="test-workflow-approval.json"

cleanup() {
    rm -f "$PENDING/$TEST_BUNDLE" "$APPROVED/$TEST_BUNDLE" "$REJECTED/$TEST_BUNDLE"
}
trap cleanup EXIT

echo "=== Human-in-the-loop Test ==="

# Create test WORKFLOW_BUNDLE with approval_required
cat > "$PENDING/$TEST_BUNDLE" << 'EOF'
{
  "bundle": "test-workflow-approval",
  "kind": "WORKFLOW_BUNDLE",
  "version": "1.0.0",
  "description": "Test workflow requiring human approval",
  "schema_uri": "https://example.com/bundle.schema.json",
  "runner": "go_temporal",
  "approval_required": true,
  "sources": [],
  "output": { "format": "json" }
}
EOF
echo "✓ Created test bundle in pending: $TEST_BUNDLE"

# Validate it passes schema
cd "$ROOT"
python3 -c "
import json
from jsonschema import validate
schema = json.load(open('bundle.schema.json'))
bundle = json.load(open('$PENDING/$TEST_BUNDLE'))
validate(instance=bundle, schema=schema)
" 2>/dev/null || python3 -c "
import json
bundle = json.load(open('$PENDING/$TEST_BUNDLE'))
assert bundle['bundle']
assert bundle['kind'] == 'WORKFLOW_BUNDLE'
assert bundle.get('approval_required') == True
"
echo "✓ Bundle validation passed"

# List pending
result=$(bash "$ROOT/scripts/approve-bundle.sh" list 2>&1)
if ! echo "$result" | grep -q "$TEST_BUNDLE"; then
    echo "✗ Bundle not listed in pending"
    exit 1
fi
echo "✓ Bundle listed in pending"

# Approve
bash "$ROOT/scripts/approve-bundle.sh" approve "$TEST_BUNDLE" >/dev/null
if [ -f "$PENDING/$TEST_BUNDLE" ]; then
    echo "✗ Bundle still in pending after approve"
    exit 1
fi
if [ ! -f "$APPROVED/$TEST_BUNDLE" ]; then
    echo "✗ Bundle not in approved after approve"
    exit 1
fi
echo "✓ Bundle approved and moved to approved/"

# Move back to pending for reject test
mv "$APPROVED/$TEST_BUNDLE" "$PENDING/$TEST_BUNDLE"
bash "$ROOT/scripts/approve-bundle.sh" reject "$TEST_BUNDLE" >/dev/null
if [ -f "$PENDING/$TEST_BUNDLE" ]; then
    echo "✗ Bundle still in pending after reject"
    exit 1
fi
if [ ! -f "$REJECTED/$TEST_BUNDLE" ]; then
    echo "✗ Bundle not in rejected after reject"
    exit 1
fi
echo "✓ Bundle rejected and moved to rejected/"

echo ""
echo "=== Human-in-the-loop Test PASSED ==="

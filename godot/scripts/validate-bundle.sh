#!/usr/bin/env bash
set -e

BUNDLE_FILE="${1:-bundles/protocol-dashboard.json}"
if [ ! -f "$BUNDLE_FILE" ]; then
    echo "Error: Bundle file not found: $BUNDLE_FILE"
    exit 1
fi

echo "=== Validating bundle: $BUNDLE_FILE ==="

# JSON syntax validation
echo "Checking JSON syntax..."
python3 -c "import json; json.load(open('$BUNDLE_FILE')); print('✓ JSON syntax valid')"

# Required fields validation
echo "Checking required fields..."
python3 -c "
import json, sys
with open('$BUNDLE_FILE') as f:
    b = json.load(f)
    required = ['bundle', 'kind', 'schema_uri', 'runner']
    for field in required:
        if field not in b:
            print(f'✗ Missing required field: {field}')
            sys.exit(1)
    print(f'✓ All required fields present')
"

# Kind validation
echo "Checking bundle kind..."
python3 -c "
import json, sys
with open('$BUNDLE_FILE') as f:
    b = json.load(f)
    valid_kinds = ['SERVICE_BUNDLE', 'VIEW_BUNDLE', 'WORKFLOW_BUNDLE', 'APPLICATION_BUNDLE']
    if b['kind'] not in valid_kinds:
        print(f'✗ Invalid kind: {b[\"kind\"]}')
        sys.exit(1)
    print(f'✓ Kind valid: {b[\"kind\"]}')
"

echo "Checking bundle sources/output shape..."
python3 -c "
import json, sys
with open('$BUNDLE_FILE') as f:
    b = json.load(f)
    sources = b.get('sources', [])
    for idx, source in enumerate(sources):
        if 'refresh_sec' in source and not isinstance(source['refresh_sec'], int):
            print(f'✗ sources[{idx}].refresh_sec must be an integer')
            sys.exit(1)
    runtime = b.get('output', {}).get('runtime')
    if runtime is not None and not isinstance(runtime, dict):
        print('✗ output.runtime must be an object when present')
        sys.exit(1)
    if b['kind'] == 'APPLICATION_BUNDLE':
        targets = b.get('targets', [])
        if not targets:
            print('✗ application bundles must declare at least one target')
            sys.exit(1)
    print('✓ Bundle shape valid')
"

echo "=== Bundle validation passed ==="

#!/usr/bin/env bash
# Example 2: Convert CSV/text/XML to JSON
set -euo pipefail

set -a
source ../.env
set +a

API="${API:-${API_BASE_URL:-http://localhost:18080}}"
say() { printf "\n\033[1;36m[example]\033[0m %s\n" "$*"; }
ok()  { printf "  \033[32m✓\033[0m %s\n" "$*"; }

say "Example 2: Convert to JSON"
say "==========================="
say "Get admin token"
TOKEN=$(curl -fsS -X POST "$API/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")

say "1. Convert CSV to JSON"
curl -fsS -X PUT "$API/commands/converttojson" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/products.csv","meta":{"mode":"csv"}}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); payload=json.loads(base64.b64decode(r['payload_b64'])); print('Rows:', len(payload['rows'])); print('First row:', payload['rows'][0])"
ok "CSV converted to JSON"

say "2. Convert CSV to JSON with field names"
curl -fsS -X PUT "$API/commands/converttojson" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/products.csv","meta":{"mode":"csv","fields":["name","price","currency","category"]}}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); payload=json.loads(base64.b64decode(r['payload_b64'])); print('Fields:', payload['fields']); print('First row:', payload['rows'][0])"
ok "CSV converted with custom fields"

say "3. Convert with schema validation"
curl -fsS -X PUT "$API/commands/converttojson" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/products.csv","schema_uri":"file:///schemas/public-products.json","meta":{"mode":"csv"}}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); print('Validation passed:', r['meta'].get('validation', 'ok'))"
ok "Schema validation successful"

say "4. Convert text to JSON (line-by-line)"
curl -fsS -X PUT "$API/commands/converttojson" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/doc.txt","meta":{"mode":"lines"}}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); payload=json.loads(base64.b64decode(r['payload_b64'])); print('Lines:', len(payload['lines']))"
ok "Text converted to JSON"

printf "\n\033[32m✓ Example 2 completed\033[0m\n"

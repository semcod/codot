#!/usr/bin/env bash
# Example 1: Fetch raw content from various protocols
set -euo pipefail

set -a
source ../.env
set +a

API="${API:-${API_BASE_URL:-http://localhost:18080}}"
say() { printf "\n\033[1;36m[example]\033[0m %s\n" "$*"; }
ok()  { printf "  \033[32m✓\033[0m %s\n" "$*"; }

say "Example 1: Fetch raw content"
say "==========================="
say "Get admin token"
TOKEN=$(curl -fsS -X POST "$API/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")

say "1. Fetch text file from file:// protocol"
curl -fsS -X PUT "$API/commands/fetch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/doc.txt"}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); print('MIME:', r['mime']); print('Content:', base64.b64decode(r['payload_b64']).decode('utf-8'))"
ok "Fetched text file"

say "2. Fetch JSON from file:// protocol"
curl -fsS -X PUT "$API/commands/fetch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/posts.json"}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); print('MIME:', r['mime']); print('Content:', base64.b64decode(r['payload_b64']).decode('utf-8'))"
ok "Fetched JSON file"

say "3. Fetch CSV from file:// protocol"
curl -fsS -X PUT "$API/commands/fetch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/products.csv"}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); print('MIME:', r['mime']); print('Content:', base64.b64decode(r['payload_b64']).decode('utf-8'))"
ok "Fetched CSV file"

say "4. Fetch from data: URI (inline base64)"
curl -fsS -X PUT "$API/commands/fetch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"data:text/plain;base64,SGVsbG8gZnJvbSBpbmxpbmUgZGF0YSE="}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); print('MIME:', r['mime']); print('Content:', base64.b64decode(r['payload_b64']).decode('utf-8'))"
ok "Fetched from inline data URI"

printf "\n\033[32m✓ Example 1 completed\033[0m\n"

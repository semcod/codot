#!/usr/bin/env bash
# Example 3: Render JSON data to HTML using Jinja2 templates
set -euo pipefail

set -a
source ../.env
set +a

API="${API:-${API_BASE_URL:-http://localhost:18080}}"
say() { printf "\n\033[1;36m[example]\033[0m %s\n" "$*"; }
ok()  { printf "  \033[32m✓\033[0m %s\n" "$*"; }

say "Example 3: Render HTML"
say "======================"
say "Get admin token"
TOKEN=$(curl -fsS -X POST "$API/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")

say "1. Render JSON data with default template"
curl -fsS -X PUT "$API/commands/render" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/posts.json","meta":{"title":"Blog Posts"}}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); html=base64.b64decode(r['payload_b64']).decode('utf-8'); print('MIME:', r['mime']); print('HTML length:', len(html)); print('Contains table:', '<table' in html)"
ok "Rendered JSON to HTML"

say "2. Render CSV data (convert first, then render)"
curl -fsS -X PUT "$API/commands/render" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/posts.json","meta":{"title":"Posts from File"}}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); html=base64.b64decode(r['payload_b64']).decode('utf-8'); print('MIME:', r['mime']); print('HTML length:', len(html)); print('Contains table:', '<table' in html)"
ok "Rendered file data to HTML"

say "3. Render with custom inline template"
curl -fsS -X PUT "$API/commands/render" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"meta":{"title":"Custom Template","template":"<h1>{{ title }}</h1><p>Items: {{ data | length }}</p>","data":["item1","item2","item3"]}}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); html=base64.b64decode(r['payload_b64']).decode('utf-8'); print('MIME:', r['mime']); print('HTML:', html.strip())"
ok "Rendered with custom template"

printf "\n\033[32m✓ Example 3 completed\033[0m\n"

#!/usr/bin/env bash
# Example 6: Role-Based Access Control (RBAC)
set -euo pipefail

API="${API:-http://localhost:18080}"
say() { printf "\n\033[1;36m[example]\033[0m %s\n" "$*"; }
ok()  { printf "  \033[32m✓\033[0m %s\n" "$*"; }
warn() { printf "  \033[33m⚠\033[0m %s\n" "$*"; }

say "Example 6: Role-Based Access Control"
say "===================================="

say "1. Admin can access everything"
ADMIN_TOKEN=$(curl -fsS -X POST "$API/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")
curl -fsS -X PUT "$API/commands/fetch" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/products.csv"}' >/dev/null
ok "Admin can fetch internal CSV"

say "2. User (bob) is denied access to internal data"
USER_TOKEN=$(curl -fsS -X POST "$API/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"bob","password":"bob"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$API/commands/fetch" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/products.csv"}')
if [ "$STATUS" = "403" ]; then
  ok "User correctly denied (403)"
else
  warn "Expected 403, got $STATUS"
fi

say "3. User (bob) CAN access public data"
curl -fsS -X PUT "$API/commands/fetch" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/public/posts.json"}' >/dev/null
ok "User can fetch public JSON"

say "4. Analyst (alice) has broader access"
ANALYST_TOKEN=$(curl -fsS -X POST "$API/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"alice"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")
curl -fsS -X PUT "$API/commands/fetch" \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/products.csv"}' >/dev/null
ok "Analyst can fetch internal CSV"

say "5. Check current user info"
curl -fsS -X GET "$API/auth/me" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('Username:', r['username']); print('Role:', r['role'])"
ok "User info retrieved"

say "6. List commands available to user"
curl -fsS -X GET "$API/commands" \
  -H "Authorization: Bearer $USER_TOKEN" \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('Available commands:', len(r['commands'])); [print(f\"  - {c['name']}: {c['description']}\") for c in r['commands']]"
ok "Commands listed for user role"

printf "\n\033[32m✓ Example 6 completed\033[0m\n"

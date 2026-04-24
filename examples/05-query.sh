#!/usr/bin/env bash
# Example 5: Queries - fetch multiple resources
set -euo pipefail

set -a
source ../.env
set +a

API="${API:-${API_BASE_URL:-http://localhost:18080}}"
say() { printf "\n\033[1;36m[example]\033[0m %s\n" "$*"; }
ok()  { printf "  \033[32m✓\033[0m %s\n" "$*"; }

say "Example 5: Queries"
say "=================="
say "Get admin token"
TOKEN=$(curl -fsS -X POST "$API/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")

say "1. Query single resource via POST"
curl -fsS -X POST "$API/queries/from-url" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source_uris":["file:///data/doc.txt"]}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('Count:', r['meta']['count']); print('First result:', r['data'][0]['uri'], r['data'][0]['mime'])"
ok "Query single resource"

say "2. Query multiple resources"
curl -fsS -X POST "$API/queries/from-url" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source_uris":["file:///data/doc.txt","file:///data/posts.json","file:///data/products.csv"]}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('Count:', r['meta']['count']); print('Results:'); [print(f\"  - {item['uri']}: {item['mime']} ({item['size']} bytes)\") for item in r['data']]"
ok "Query multiple resources"

say "3. Query via GET (convenience method)"
curl -fsS -G "$API/queries/from-url" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "source_uris=file:///data/doc.txt" \
  --data-urlencode "source_uris=file:///data/posts.json" \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('Count:', r['meta']['count'])"
ok "Query via GET"

say "4. Introspect available commands and queries"
curl -fsS -X GET "$API/queries/introspect" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('Available commands:', len(r['data']['commands'])); print('Available queries:', len(r['data']['queries'])); print('Supported protocols:', r['data']['protocols'])"
ok "Introspection successful"

say "5. Public catalog (no auth required)"
curl -fsS "$API/catalog" \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('Commands:', len(r['commands'])); print('Queries:', len(r['queries'])); print('Protocols:', len(r['protocols']))"
ok "Public catalog accessible"

printf "\n\033[32m✓ Example 5 completed\033[0m\n"

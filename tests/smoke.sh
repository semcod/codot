#!/usr/bin/env bash
# Smoke test against a running stack. Exits non-zero on first failure.
set -euo pipefail

set -a
source ../.env
set +a

API="${API:-${API_BASE_URL:-http://localhost:18080}}"
say() { printf "\n\033[1;34m[test]\033[0m %s\n" "$*"; }
ok()  { printf "  \033[32m✓\033[0m %s\n" "$*"; }
die() { printf "  \033[31m✗ %s\033[0m\n" "$*"; exit 1; }

say "1. health"
curl -fsS "$API/health" >/dev/null && ok "health ok" || die "health failed"

say "2. token (admin)"
ADMIN_TOKEN=$(curl -fsS -X POST "$API/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")
[ -n "$ADMIN_TOKEN" ] && ok "got admin token" || die "no token"

say "3. token (bob - user role)"
USER_TOKEN=$(curl -fsS -X POST "$API/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"bob","password":"bob"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")
[ -n "$USER_TOKEN" ] && ok "got user token" || die "no user token"

say "4. catalog (public)"
curl -fsS "$API/catalog" | python3 -m json.tool >/dev/null && ok "catalog renders"

say "5. admin runs converttojson on CSV via file://"
curl -fsS -X PUT "$API/commands/converttojson" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/products.csv","meta":{"mode":"csv"}}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); payload=json.loads(base64.b64decode(r['payload_b64'])); assert len(payload['rows'])==5, payload; print('rows:',len(payload['rows']))" \
  && ok "csv → json conversion works"

say "6. admin runs converttojson with schema validation"
curl -fsS -X PUT "$API/commands/converttojson" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/products.csv","schema_uri":"file:///schemas/public-products.json","meta":{"mode":"csv"}}' \
  >/dev/null && ok "schema validation ok"

say "7. user (bob) is denied on internal CSV"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$API/commands/converttojson" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/products.csv"}')
[ "$STATUS" = "403" ] && ok "user correctly denied (403)" || die "expected 403 got $STATUS"

say "8. user (bob) CAN read public data"
curl -fsS -X PUT "$API/commands/converttojson" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/public/posts.json","meta":{"mode":"json"}}' \
  >/dev/null && ok "user can read public"

say "9. unauthenticated gets 401"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$API/commands/fetch" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///data/doc.txt"}')
[ "$STATUS" = "401" ] && ok "anonymous correctly denied (401)" || die "expected 401 got $STATUS"

say "10. pipeline: csv → json → render"
curl -fsS -X PUT "$API/commands/pipeline" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"meta":{"steps":[{"command":"converttojson","request":{"input_uri":"file:///data/products.csv","meta":{"mode":"csv"}}},{"command":"render","request":{"input_uri":"$previous.output","meta":{"title":"Products"}}}]}}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); assert r['mime']=='text/html', r; print('pipeline produced html:', r['mime'])" \
  && ok "pipeline composition works"

say "11. path traversal is blocked"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$API/commands/fetch" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///etc/passwd"}')
[ "$STATUS" = "403" ] || [ "$STATUS" = "400" ] && ok "traversal blocked ($STATUS)" || die "expected 403/400 got $STATUS"

say "12. catalog includes agent backends"
curl -fsS "$API/catalog" \
  | python3 -c "import json,sys; r=json.load(sys.stdin); assert 'agent_backends' in r and 'mcp' in r['agent_backends'], r; print('backends:', r['agent_backends'])" \
  && ok "agent backends in catalog"

say "13. agent backends endpoint"
curl -fsS "$API/agents/backends" \
  | python3 -c "import json,sys; r=json.load(sys.stdin); assert any(b['name']=='mcp' for b in r.get('backends',[])), r" \
  && ok "/agents/backends lists backends"

say "14. pipeline with agent_node (bash_cli backend)"
python3 -c "
import json,sys
json.dump({
  'meta': {
    'steps': [
      {'command':'fetch','request':{'input_uri':'data:text/plain;base64,cXdlcnR5'}},
      {
        'command':'agent',
        'request':{'meta':{'input':'\$previous.output'}},
        'agent_node':{
          'id':'smoke-agent','role':'tester','goal':'echo hello',
          'tools':[],'backend':'bash_cli',
          'backend_config':{'command_template':'echo hello_from_agent'}
        }
      }
    ]
  }
}, open('/tmp/smoke_agent.json','w'))
"
curl -fsS -X PUT "$API/commands/pipeline" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  --data @/tmp/smoke_agent.json \
  | python3 -c "import json,sys; r=json.load(sys.stdin); trace=r['meta']['pipeline_trace']; assert len(trace)==2, trace; assert trace[1]['command']=='agent', trace; print('agent step ok')" \
  && ok "pipeline with agent_node works"

say "15. compile_service generates artifacts"
curl -fsS -X PUT "$API/commands/compile_service" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_uri":"file:///home/tom/github/semcod/codot/examples/view-bundle-protocol-dashboard.json","meta":{"targets":"view/php-standalone"}}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); files=r.get('meta',{}).get('files',[]); assert any('view/php-standalone/index.php' in f for f in files), files; print('files:', files)" \
  && ok "compile_service produced view/php-standalone/index.php"

printf "\n\033[32m✓ all smoke tests passed\033[0m\n"

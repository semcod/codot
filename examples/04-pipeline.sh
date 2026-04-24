#!/usr/bin/env bash
# Example 4: Pipeline - chain multiple commands together
set -euo pipefail

set -a
source ../.env
set +a

API="${API:-${API_BASE_URL:-http://localhost:18080}}"
say() { printf "\n\033[1;36m[example]\033[0m %s\n" "$*"; }
ok()  { printf "  \033[32m✓\033[0m %s\n" "$*"; }

say "Example 4: Pipeline Composition"
say "==============================="
say "Get admin token"
TOKEN=$(curl -fsS -X POST "$API/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")

say "1. Pipeline: CSV → JSON → Render"
curl -fsS -X PUT "$API/commands/pipeline" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meta": {
      "steps": [
        {
          "command": "converttojson",
          "request": {
            "input_uri": "file:///data/products.csv",
            "meta": {"mode": "csv"}
          }
        },
        {
          "command": "render",
          "request": {
            "input_uri": "$previous.output",
            "meta": {"title": "Products Table"}
          }
        }
      ]
    }
  }' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); print('MIME:', r['mime']); print('Pipeline trace:', r['meta']['pipeline_trace']); html=base64.b64decode(r['payload_b64']).decode('utf-8'); print('HTML length:', len(html))"
ok "Pipeline completed successfully"

say "2. Pipeline: CSV → JSON → CSV (round trip)"
curl -fsS -X PUT "$API/commands/pipeline" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meta": {
      "steps": [
        {
          "command": "converttojson",
          "request": {
            "input_uri": "file:///data/products.csv",
            "meta": {"mode": "csv"}
          }
        },
        {
          "command": "converttocsv",
          "request": {
            "input_uri": "$previous.output"
          }
        }
      ]
    }
  }' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); print('MIME:', r['mime']); csv=base64.b64decode(r['payload_b64']).decode('utf-8'); print('CSV length:', len(csv)); print('First line:', csv.split('\n')[0])"
ok "CSV round-trip completed"

say "3. Pipeline: Fetch → Base64 → JSON"
curl -fsS -X PUT "$API/commands/pipeline" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meta": {
      "steps": [
        {
          "command": "fetch",
          "request": {
            "input_uri": "file:///data/doc.txt"
          }
        },
        {
          "command": "converttobase64",
          "request": {
            "input_uri": "$previous.output"
          }
        }
      ]
    }
  }' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); print('MIME:', r['mime']); print('Pipeline trace:', r['meta']['pipeline_trace'])"
ok "Fetch → Base64 pipeline completed"

say "4. Complex pipeline: CSV → JSON → Render"
curl -fsS -X PUT "$API/commands/pipeline" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meta": {
      "steps": [
        {
          "command": "converttojson",
          "request": {
            "input_uri": "file:///data/products.csv",
            "meta": {"mode": "csv"}
          }
        },
        {
          "command": "render",
          "request": {
            "input_uri": "$previous.output",
            "meta": {
              "title": "Product Catalog",
              "template": "<!doctype html><html><head><title>{{ title }}</title></head><body><h1>{{ title }}</h1>{% for row in data.rows %}<p>{{ row.name }} - {{ row.price }} {{ row.currency }}</p>{% endfor %}</body></html>"
            }
          }
        }
      ]
    }
  }' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); html=base64.b64decode(r['payload_b64']).decode('utf-8'); print('MIME:', r['mime']); print('HTML preview:', html[:200])"
ok "Complex pipeline with custom template"

printf "\n\033[32m✓ Example 4 completed\033[0m\n"

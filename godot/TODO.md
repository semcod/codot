# Godot Bundle System — TODO / Roadmap

## P0 — Infrastructure (DONE ✅)
- [x] Fix go.sum / Dockerfile — `go mod download` works in container
- [x] Fix schema-server reachability on :8084 (Caddy healthcheck)
- [x] Fix Temporal DB init (`DB=postgres12`, `temporal-ui` on :8233)
- [x] `scripts/test-services.sh` uses real HTTP checks (not just socket open)
- [x] `make start` passes end-to-end (schema + Temporal + PostgreSQL + Go tests + LLM/ACL)
- [x] Port extraction tolerates legacy `output.port` and current `output.runtime.port`
- [x] Schema URI fallback (`resolvedSchemaURI`) + Go tests
- [x] `infer_kind` priority fix (workflow → view → application → service)
- [x] `APPLICATION_BUNDLE` defaults to `go_temporal` runner
- [x] README synchronized with current stack
- [x] Remove obsolete `PFIX_*` env vars

## P1 — Practical Bundles & Data Workflows (NEXT)
- [x] Add real-world bundles using public APIs (no API key needed):
  - [x] Weather dashboard (Open-Meteo) — VIEW_BUNDLE
  - [x] Currency rates service (NBP.pl) — SERVICE_BUNDLE
  - [x] Internet data report (weather + NBP combined) — VIEW_BUNDLE
  - [x] News aggregator / RSS — SERVICE_BUNDLE + VIEW_BUNDLE
- [x] Bundle-to-bundle composition: one bundle's output as another's source
- [x] `report` output.format — render JSON data as HTML report (`scripts/render-report.py`)
- [x] Internet data fetching + TTL cache (`scripts/render-report.py` caches to `~/.cache/godot-bundle/`)
- [x] Test that practical bundles validate and can be LLM-generated from prompts (`scripts/test-practical-bundles.py`)

## P2 — DOQL Bridge (App Generation) [DONE ✅]
- [x] Bundle → `app.doql.css` generator (`scripts/bundle-to-doql.py`)
- [x] DOQL validate + plan + build passing from generated `app.doql.css`
- [x] Makefile targets: `generate-doql`, `build-doql`, `run-doql`
- [x] `APPLICATION_BUNDLE` targets map to DOQL interfaces (desktop/Tauri, web/React, mobile/PWA)
- [x] Temporal workflow: `BuildAppWorkflow` (bundle → doql → build → artifact) — `src/deploy_workflow.go`
- [x] Test script: `scripts/test-buildapp-workflow.sh` + `make test-buildapp`
- [ ] Artifact storage: MinIO/S3 container for generated apps

## P3 — Auth, Observability & DX
- [ ] Auth layer (Caddy forward_auth + bundle `auth` field with scopes)
- [x] ACL for LLM: network CIDR, endpoint deny-lists, field redaction (`llm/app.py`, `llm/acl.yaml`)
- [x] Audit log table in Postgres for every LLM decision (`llm/audit.py`, `scripts/init-audit.sql`, `make test-audit`)
- [x] Human-in-the-loop: `bundles/pending/` for WORKFLOW_BUNDLE approval (`scripts/approve-bundle.sh`, `scripts/test-human-in-the-loop.sh`, `make pending-bundle`)
- [x] Prometheus + Grafana dashboards per runner (`prometheus.yml`, `grafana/provisioning/`, `llm/app.py` /metrics, `make test-prometheus`)
- [ ] OpenTelemetry tracing through bundle execution
- [ ] Go test coverage >80%, mutation testing
- [ ] devcontainer.json + pre-commit hooks

## LLM / NLP Fixtures (Test Prompts)
1. "Show protocol 123 status every second" → VIEW_BUNDLE, refresh_sec: 1
2. "Build REST service for user management on port 8090" → SERVICE_BUNDLE
3. "Hourly workflow: fetch weather API and save to DB" → WORKFLOW_BUNDLE
4. "Render /api/v3/orders as PHP dashboard" → VIEW_BUNDLE, format: php
5. "ChatGPT proxy with 10/min rate limit" → SERVICE_BUNDLE, middleware
6. "Something cool for Docker monitoring" → clarification / vague-input handling

## DOQL Target Mapping
| Bundle Kind | DOQL Target | Generated Stack |
|---|---|---|
| SERVICE_BUNDLE | api | FastAPI backend |
| VIEW_BUNDLE | web | React frontend |
| APPLICATION_BUNDLE | desktop | Tauri |
| APPLICATION_BUNDLE | mobile | PWA / Expo |
| WORKFLOW_BUNDLE | infra | Temporal workers |


# Godot Bundle System

Service Factory for bundle-driven services, views, workflows, and applications with JSON schema validation, Go Temporal orchestration, LiteLLM-assisted generation, ACL-controlled fetching, and Docker orchestration.

## Overview

The Godot Bundle System provides:
- **Bundle Validation**: JSON Schema validation with fallback schema resolution
- **Multiple Bundle Kinds**: Service, view, workflow, and application bundles
- **LLM + ACL Layer**: FastAPI LiteLLM service with `/fetch`, `/context`, and bundle generation endpoints
- **Docker Orchestration**: Full stack with Temporal, PostgreSQL, Schema Server, LLM API, and Mock API
- **Automated Testing**: Shell and Go tests for bundles, service readiness, ACL, and NLP generation
- **Environment Configuration**: Root `.env` for stack ports and `llm/.env` for model/runtime settings

## Directory Structure

| Directory | Contents |
|-----------|----------|
| `bundles/` | Bundle manifest files (SERVICE_BUNDLE, VIEW_BUNDLE, WORKFLOW_BUNDLE, APPLICATION_BUNDLE) |
| `llm/` | FastAPI LiteLLM service, ACL policy, and model/runtime configuration |
| `src/` | Go source: bundle structs, validation, runners, Temporal integration |
| `generated/` | Runtime output: deployed apps |
| `scripts/` | Bash helpers: validation, testing, Docker management |
| `Makefile` | Convenience targets for build, start, test, and Docker operations |
| `docker-compose.yml` | Docker services: godot, Temporal, PostgreSQL, Schema Server, LLM API, Mock API |
| `.env` | Root port and service configuration for the stack |

## Files

| File | Purpose |
|------|---------|
| `bundle.schema.json` | JSON Schema for bundle validation |
| `llm/app.py` | LiteLLM/ACL service and mock API endpoints |
| `llm/acl.yaml` | Allowed and denied URI policy for LLM-driven fetches |
| `src/bundle.go` | Canonical Go bundle structs with schema resolution and runner dispatch |
| `src/bundle_test.go` | Go tests for bundle validation |
| `src/starter.go` | Temporal client for bundle execution |
| `scripts/validate-bundle.sh` | Validate single bundle JSON |
| `scripts/validate-all.sh` | Recursively validate all bundle JSON files |
| `scripts/test-services.sh` | Verify stack readiness and bundle validation in Docker |
| `scripts/test-llm.sh` | Verify LLM health, ACL enforcement, context fetch, and NLP bundle generation |
| `scripts/quickstart.sh` | Wrapper that delegates to `make start` |
| `scripts/install.sh` | Install dependencies (Go, Python3, PHP, Docker) |

## Architecture

```
bundles/*.json
  → JSON Schema Validation (bundle.schema.json)
  → Go Structs (Bundle, Source, Output)
  → Runner Selection (go_temporal, python_fastapi)
  → Temporal Workflow / Direct Execution
  → Generated Services
```

**Schema Validation Strategy:**
- Explicit bundle schema URIs are used as-is
- Placeholder schema URIs resolve via `BUNDLE_SCHEMA_URI` or a local bundled schema file
- DEBUG or `BUNDLE_SKIP_VALIDATION=true` enables soft-fallback warnings

## Quick Start

Recommended flow:

```bash
make start
make status
make test-services
make llm-test
```

`bash scripts/quickstart.sh` remains available as a thin wrapper around `make start`.

If you want to start the stack manually:

```bash
make docker-build
make docker-up
bash scripts/test-services.sh
bash scripts/test-llm.sh
```

## Docker Services

| Service | Description | Ports |
|---------|-------------|-------|
| godot | Bundle validation and execution service | 9000-9003 (host), 8080-8083 (container) |
| temporal | Temporal workflow orchestration (gRPC) | 7233 |
| temporal-ui | Temporal Web UI | 8233 |
| postgres | PostgreSQL for Temporal | 5433 (host), 5432 (container) |
| schema-server | Caddy server for bundle schema | 8084 (host), 80 (container) |
| llm | LiteLLM + ACL FastAPI service | 18094 (host), 8000 (container) |
| mock-api | Mock API for ACL and NLP tests | 18095 (host), 8001 (container) |

**Service URLs:**
- Schema Server: http://localhost:8084/bundle.schema.json
- Temporal gRPC: localhost:7233
- Temporal Web UI: http://localhost:8233
- PostgreSQL: localhost:5433
- LLM API: http://localhost:18094/health
- Mock API: http://localhost:18095/health

## Configuration

Edit `.env` to customize stack ports and service wiring:

```bash
POSTGRES_PORT=5433
TEMPORAL_PORT=7233
SCHEMA_SERVER_PORT=8084
GODOT_PORT_8080=9000
GODOT_PORT_8081=9001
GODOT_PORT_8082=9002
GODOT_PORT_8083=9003
LLM_PORT=18094
MOCK_API_PORT=18095
BUNDLE_SCHEMA_URI=http://schema-server:80/bundle.schema.json
```

Edit `llm/.env` to customize model/runtime settings:

```bash
LLM_MODEL=openrouter/qwen/qwen3-coder-next
LLM_OFFLINE=true
OPENROUTER_API_KEY=
BUNDLE_SCHEMA_FILE=/app/bundle.schema.json
BUNDLE_OUTPUT_DIR=/app/bundles/generated
LLM_ACL_FILE=/app/acl.yaml
```

## Make Commands

```bash
make help            # Show all available commands
make start           # Clean, build, start the full stack, and run service checks
make stop            # Stop services and clean bound ports
make restart         # Restart the full stack
make status          # Show container and port status
make build           # Validate all bundles + run Go bundle tests
make validate        # Validate single bundle
make validate-all    # Recursively validate all bundles
make test            # Run Go bundle tests
make test-services   # Run stack readiness tests + LLM/ACL tests
make llm-test        # Run only the LLM/ACL/NLP tests
make docker-build    # Build Docker image
make docker-test     # Run bundle validation tests in Docker
make docker-up       # Start Docker services
make docker-down     # Stop Docker services
make generate-doql   # Generate DOQL app.doql.css from a bundle
make build-doql      # Build DOQL web/desktop/mobile app
make render-report   # Render HTML report from bundle sources
make test-practical  # Test LLM inference on all practical bundles
```

## Practical Bundles

The `bundles/` directory includes real-world examples using public APIs (no API key required):

| Bundle | Kind | Data Source |
|---|---|---|
| `weather-europe-view.json` | VIEW_BUNDLE | Open-Meteo (Berlin, Paris, Rome, Warsaw) |
| `nbp-currency-service.json` | SERVICE_BUNDLE | NBP.pl exchange rates |
| `internet-data-report.json` | VIEW_BUNDLE | Weather + currency combined |
| `news-aggregator-service.json` | SERVICE_BUNDLE | Hacker News / Reddit / Lobsters RSS |
| `news-aggregator-view.json` | VIEW_BUNDLE | Dashboard for news-aggregator-service |
| `combined-weather-news-report.json` | VIEW_BUNDLE | Bundle-to-bundle composition |

Generate and view a report:
```bash
make render-report BUNDLE=bundles/internet-data-report.json
open generated/report.html
```

## DOQL Bridge

Any bundle can be exported to an `app.doql.css` and built with the DOQL toolchain (FastAPI + React + Tauri):

```bash
make build-doql BUNDLE=bundles/weather-europe-view.json
# Generates generated/app.doql.css + generated/build/web/
```

## Bundle Validation

### Shell Validation

```bash
# Validate single bundle
bash scripts/validate-bundle.sh bundles/protocol-dashboard.json

# Validate all bundles
bash scripts/validate-all.sh

# Or use Make
make validate-all
```

### Go Validation

```bash
cd src
GOFLAGS=-mod=mod go test -v bundle.go bundle_test.go
```

### Docker Validation

```bash
# Run validation in Docker container
docker exec godot-bundle-service bash scripts/validate-all.sh

# Or use Make
make docker-test
```

## Schema Validation Modes

### 1. Explicit bundle schema URI

When `schema_uri` is set to a real URI in the bundle, `bundle.go` validates against that exact schema.

### 2. Placeholder/default schema resolution

When a bundle uses the placeholder `https://example.com/bundle.schema.json`, `bundle.go` resolves the schema from:

1. `BUNDLE_SCHEMA_URI`, if set
2. `../bundle.schema.json`
3. `bundle.schema.json`

This lets the bundled examples work in both repo-local and containerized flows without hardcoding a host-specific schema endpoint.

### 3. Soft-Fallback Mode (Development)

Skip validation in DEBUG mode with warnings:

```bash
export DEBUG=true
# or
export BUNDLE_SKIP_VALIDATION=true
```

**Behavior:**
- Validates if schema_uri is present
- Logs warnings on validation failure
- Continues execution (doesn't fail)

## Bundle Examples

### VIEW_BUNDLE

```json
{
  "bundle": "protocol-dashboard",
  "kind": "VIEW_BUNDLE",
  "version": "1.0.0",
  "schema_uri": "https://example.com/bundle.schema.json",
  "runner": "go_temporal",
  "sources": [
    {
      "name": "protocol",
      "uri": "http://localhost:8080/api/v3/protocols/123",
      "refresh_sec": 1
    }
  ],
  "output": {
    "format": "php",
    "runtime": {
      "port": 8082,
      "lang": "php"
    }
  }
}
```

### SERVICE_BUNDLE

```json
{
  "bundle": "connect-test-service",
  "kind": "SERVICE_BUNDLE",
  "version": "1.0.0",
  "schema_uri": "https://example.com/bundle.schema.json",
  "runner": "go_temporal",
  "contracts": [...],
  "output": {
    "format": "python_fastapi",
    "runtime": {
      "port": 8080,
      "lang": "python"
    }
  }
}
```

## Testing

### Service Health Check

```bash
# Run comprehensive service tests
bash scripts/test-services.sh
bash scripts/test-llm.sh
```

This tests:
1. Schema server accessibility
2. Temporal server connectivity
3. PostgreSQL connectivity
4. Bundle validation in Docker
5. Go bundle tests
6. Schema URI configuration
7. Bundle file presence
8. LLM and mock API health
9. ACL allow/deny behavior
10. `/context` fetching and NLP-driven bundle generation

### Go Tests

```bash
cd src
GOFLAGS=-mod=mod go test -v bundle.go bundle_test.go
```

Tests cover:
- Bundle JSON unmarshaling
- Required field validation
- Kind enum validation
- Runner enum validation
- Source/Output struct validation

## Docker Operations

### Enter Container

```bash
docker exec -it godot-bundle-service bash
```

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs godot
docker-compose logs temporal
docker-compose logs postgres
```

### Restart Services

```bash
make restart
```

### Clean Up

```bash
# Stop and remove containers
make stop

# Remove volumes (deletes PostgreSQL data)
docker-compose down -v

# Remove images
docker rmi godot-bundle-service
```

## Troubleshooting

### Port Conflicts

If ports are already allocated, edit `.env`:

```bash
# Change exposed Godot and LLM ports
GODOT_PORT_8080=9010
LLM_PORT=18096
SCHEMA_SERVER_PORT=8085
```

### Container Won't Start

```bash
# Check logs
docker-compose logs

# Rebuild without cache
docker-compose build --no-cache

# Remove and recreate
docker-compose down -v
docker-compose up -d
```

### Validation Failures

```bash
# Enable DEBUG mode for soft-fallback
export DEBUG=true
make build
make test-services

# Check bundle schema
cat bundle.schema.json

# Validate JSON syntax
python3 -m json.tool bundles/protocol-dashboard.json
```

## Development

### Adding New Bundle Types

1. Update `bundle.schema.json` with new kind enum
2. Add validation in `src/bundle_test.go`
3. Add runner implementation in `src/bundle.go`
4. Create example bundle in `bundles/`

### Adding New Runners

1. Add runner to enum in `src/bundle.go`
2. Implement `runNewRunner()` method
3. Update schema validation if needed
4. Add tests in `src/bundle_test.go`

## License

See LICENSE file in project root.

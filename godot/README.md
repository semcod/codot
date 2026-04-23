# Godot Bundle System

Service Factory for CQRS/Temporal bundles with JSON schema validation, multiple runners (Go Temporal, Python FastAPI), and Docker orchestration.

## Overview

The Godot Bundle System provides:
- **Bundle Validation**: JSON Schema validation with default/soft-fallback modes
- **Multiple Runners**: Go Temporal, Python FastAPI (extensible)
- **Docker Orchestration**: Full stack with Temporal, PostgreSQL, Schema Server
- **Automated Testing**: Shell and Go tests for all bundles
- **Environment Configuration**: .env support for flexible deployment

## Directory Structure

| Directory | Contents |
|-----------|----------|
| `bundles/` | Bundle manifest files (SERVICE_BUNDLE, VIEW_BUNDLE, WORKFLOW_BUNDLE) |
| `src/` | Go source: bundle structs, validation, runners, Temporal integration |
| `generated/` | Runtime output: deployed apps |
| `scripts/` | Bash helpers: validation, testing, Docker management |
| `Makefile` | Convenience targets for build, test, Docker operations |
| `docker-compose.yml` | Docker services: godot, Temporal, PostgreSQL, Schema Server |
| `.env` | Environment configuration for ports and services |

## Files

| File | Purpose |
|------|---------|
| `bundle.schema.json` | JSON Schema for bundle validation |
| `src/bundle.go` | Go structs (Bundle, Source, Output) with LoadSchema/Run methods |
| `src/bundle_test.go` | Go tests for bundle validation |
| `src/starter.go` | Temporal client for bundle execution |
| `scripts/validate-bundle.sh` | Validate single bundle JSON |
| `scripts/validate-all.sh` | Validate all bundle JSONs |
| `scripts/test-services.sh` | Test all Docker services after startup |
| `scripts/quickstart.sh` | Automated setup and testing |
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
- Default global schema from `BUNDLE_SCHEMA_URI` env var
- Soft-fallback mode in DEBUG (warnings, no errors)
- Supports `file://` and `http://` schema URIs

## Quick Start

### Option 1: Automated Quick Start

```bash
bash scripts/quickstart.sh
```

This will:
1. Build Docker image
2. Start all services (godot, Temporal, PostgreSQL, Schema Server)
3. Run service tests
4. Display service URLs and next steps

### Option 2: Manual Setup

```bash
# Build Docker image
make docker-build

# Start services
make docker-up

# Wait for services to start (5-10 seconds)
sleep 5

# Test services
make docker-test

# Or run comprehensive service tests
bash scripts/test-services.sh
```

## Docker Services

| Service | Description | Ports |
|---------|-------------|-------|
| godot | Bundle validation and execution service | 8080-8083 |
| temporal | Temporal workflow orchestration | 7233, 8233 |
| postgres | PostgreSQL for Temporal | 5433 (host) |
| schema-server | Caddy server for bundle schema | 8084 (host) |

**Service URLs:**
- Schema Server: http://localhost:8084/bundle.schema.json
- Temporal Web: http://localhost:7233
- PostgreSQL: localhost:5433

## Configuration

Edit `.env` to customize:

```bash
# Port Configuration
POSTGRES_PORT=5433
TEMPORAL_PORT=7233
SCHEMA_SERVER_PORT=8084

# Bundle Configuration
BUNDLE_SCHEMA_URI=http://schema-server:80/bundle.schema.json
DEBUG=false
BUNDLE_SKIP_VALIDATION=false

# Temporal Configuration
TEMPORAL_HOST=temporal:7233
POSTGRES_USER=temporal
POSTGRES_PASSWORD=temporal
POSTGRES_DB=temporal
```

## Make Commands

```bash
make help           # Show all available commands
make build          # Validate all bundles + check Go structs
make validate       # Validate single bundle
make validate-all   # Validate all bundles
make test           # Run Go tests
make docker-build   # Build Docker image
make docker-test    # Run validation tests in Docker
make docker-up      # Start Docker services
make docker-down    # Stop Docker services
make clean          # Kill running processes
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
go test -v -run TestBundle
```

### Docker Validation

```bash
# Run validation in Docker container
docker exec godot-bundle-service bash scripts/validate-all.sh

# Or use Make
make docker-test
```

## Schema Validation Modes

### 1. Default Global Schema (Production)

When `schema_uri` is empty in bundle, uses default from environment:

```go
// In bundle.go
if b.SchemaURI == "" {
    defaultSchema := os.Getenv("BUNDLE_SCHEMA_URI")
    if defaultSchema == "" {
        defaultSchema = "https://example.com/bundle.schema.json"
    }
    b.SchemaURI = defaultSchema
}
```

**Environment:**
```bash
export BUNDLE_SCHEMA_URI=file:///app/bundle.schema.json
```

### 2. Soft-Fallback Mode (Development)

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
      "port": 8082
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
      "port": 8080
    }
  }
}
```

## Testing

### Service Health Check

```bash
# Run comprehensive service tests
bash scripts/test-services.sh
```

This tests:
1. Schema server accessibility
2. Temporal server connectivity
3. PostgreSQL connectivity
4. Bundle validation in Docker
5. Go compilation
6. Schema URI configuration
7. Bundle file presence

### Go Tests

```bash
cd src
go test -v
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
make docker-down
make docker-up
```

### Clean Up

```bash
# Stop and remove containers
make docker-down

# Remove volumes (deletes PostgreSQL data)
docker-compose down -v

# Remove images
docker rmi godot-bundle-service
```

## Troubleshooting

### Port Conflicts

If ports are already allocated, edit `.env`:

```bash
# Change PostgreSQL port
POSTGRES_PORT=5434

# Change schema server port
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
make docker-test

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

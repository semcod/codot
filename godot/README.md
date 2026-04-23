# Protocol Dashboard — VIEW_BUNDLE Generated Project

Generated from `bundles/protocol-dashboard.json` (VIEW_BUNDLE). Demonstrates the CQRS/Service Factory pipeline: JSON bundle definition → Go struct validation → standalone PHP dashboard with live JS refresh.

## Directory Structure

| Directory | Contents |
|-----------|----------|
| `bundles/` | VIEW_BUNDLE manifest files (JSON input) |
| `src/` | Go source: structs, Temporal workflow + starter |
| `generated/` | Runtime output: deployed app (`dashboard.php`) |
| `scripts/` | Bash helpers: `build.sh`, `run.sh`, `starter.sh` |
| `Makefile` | Convenience targets |

## Files

| File | Purpose |
|------|---------|
| `bundles/protocol-dashboard.json` | VIEW_BUNDLE input — sources, refresh, template, output |
| `src/structs.go` | Go structs with JSON tags for unmarshal + validation |
| `src/deploy_workflow.go` | Temporal worker: generate → deploy → healthcheck → rollback |
| `src/starter.go` | Temporal client: submits `DeployViewBundle` workflow |
| `generated/dashboard.php` | Standalone PHP dev server with JS live-refresh |
| `scripts/run.sh` | Start PHP server using port from bundle JSON |
| `scripts/build.sh` | Validate bundle JSON + syntax-check Go structs |
| `scripts/starter.sh` | Run Temporal starter for a given bundle |

## Architecture

```
bundles/*.json  →  src/structs.go (validate)  →  src/deploy_workflow.go (orchestrate)  →  generated/dashboard.php (runtime)
```

**Sources:**
- `protocol` — `http://localhost:8080/api/v3/protocols/123` (refresh: 1s)
- `devices` — `http://localhost:8081/api/v3/devices` (refresh: 5s, `depends_on: protocol`)

**Output:** PHP standalone on port 8082.

## Quick Start

```bash
make build    # validate bundle
make run      # php -S 0.0.0.0:8082 generated/dashboard.php
make deploy   # temporal worker + starter (needs temporal server)
make clean    # kill php / go processes
```

Or use scripts directly:

```bash
bash scripts/build.sh
bash scripts/run.sh
bash scripts/starter.sh bundles/protocol-dashboard.json
```

Open http://localhost:8082 — the dashboard auto-refetches `protocol` every 1s and `devices` every 5s via client-side `fetch()`.

## Validate Bundle (Go)

```bash
cd src && go run structs.go - <<'EOF'
package main
import ("encoding/json"; "fmt"; "os")
func main() {
    data, _ := os.ReadFile("../bundles/protocol-dashboard.json")
    var b ViewBundle
    json.Unmarshal(data, &b)
    fmt.Printf("%s v%s\n", b.Bundle, b.Version)
}
EOF
```

## Notes

- `depends_on` is informational in the PHP runtime; a full orchestrator enforces topological ordering
- `template.engine: jinja2` is declared but not wired in the PHP output — could be added server-side

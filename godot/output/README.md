# Protocol Dashboard — VIEW_BUNDLE Generated Project

Generated from `protocol-dashboard.json` (VIEW_BUNDLE). This project demonstrates the CQRS/Service Factory pipeline: a JSON bundle definition is parsed, validated via Go structs, and emitted as a standalone PHP dashboard with live data refresh.

---

## Files

| File | Purpose |
|------|---------|
| `protocol-dashboard.json` | VIEW_BUNDLE input — defines sources, refresh intervals, template engine, and output format |
| `structs.go` | Go structs with JSON tags for `encoding/json` unmarshal + validation. Includes `ViewBundle`, `Source`, `Template`, `Output` |
| `dashboard.php` | Standalone PHP dev server — serves an HTML dashboard with JS live-refresh against configured sources |
| `deploy_workflow.go` | Temporal workflow for automated deploy of VIEW_BUNDLE: generate → deploy → healthcheck → rollback on failure |
| `README.md` | This file |

---

## Architecture

```
protocol-dashboard.json
        |
        v
   structs.go  (validation layer — Go structs + json.Unmarshal)
        |
        v
   dashboard.php  (runtime — PHP standalone with curl + JS fetch)
```

**Sources:**
- `protocol` — `http://localhost:8080/api/v3/protocols/123` (refresh: 1s)
- `devices` — `http://localhost:8081/api/v3/devices` (refresh: 5s, depends_on: protocol)

**Output:** PHP standalone server on port 8082.

---

## Quick Start

### 1. Start backend mock APIs (optional)

The dashboard expects two upstream APIs. If you don't have them running, the JS fetch will show errors in browser devtools — the dashboard itself still serves.

### 2. Run the PHP server

```bash
php -S 0.0.0.0:8082 dashboard.php
```

### 3. Open in browser

```
http://localhost:8082
```

The dashboard auto-refetches `protocol` every 1 second and `devices` every 5 seconds via client-side JS `fetch()`.

---

## Validate the Bundle (Go)

```bash
go run - <<'EOF'
package main
import (
    "encoding/json"
    "fmt"
    "os"
)
// structs.go contents here
func main() {
    data, _ := os.ReadFile("protocol-dashboard.json")
    var bundle ViewBundle
    if err := json.Unmarshal(data, &bundle); err != nil {
        panic(err)
    }
    fmt.Printf("Bundle: %s v%s (%s)\n", bundle.Bundle, bundle.Version, bundle.Description)
    for _, s := range bundle.Sources {
        fmt.Printf("  Source: %s -> %s (refresh: %s)\n", s.Name, s.URI, s.Refresh)
    }
}
EOF
```

---

## Adapting for Another Bundle

1. Edit `protocol-dashboard.json` — change `sources`, `template`, `output`
2. Regenerate `structs.go` from JSON schema (or manually update types)
3. Regenerate `dashboard.php` from bundle definition
4. Re-run `php -S 0.0.0.0:<port> dashboard.php`

---

## Notes

- `depends_on` in sources is informational in this PHP runtime; a full orchestrator (e.g., Temporal, Airflow) would enforce topological ordering
- `template.engine: jinja2` is declared in the bundle but not used in the PHP output — it could be wired to a server-side renderer if needed

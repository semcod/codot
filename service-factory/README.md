# Service Factory

A contract-driven code & infrastructure generator for the CQRS-URL ecosystem.

Takes a **Service Bundle** — a JSON file that aggregates existing CQRS contracts
(`*.command.json`, `*.query.json`, `*.event.json`) plus runtime/infra decisions —
and emits a deployable service across three orthogonal axes:

| Axis  | Generators                                           |
|-------|------------------------------------------------------|
| code  | `python-fastapi`, `node-fastify`                     |
| infra | `docker`, `kubernetes`                               |
| wire  | `openapi` (AsyncAPI, Proto are 1-file additions)     |
| view  | `php-standalone`, `static-html`, `fastapi-sse`, `docker-fastapi-sse`, `kubernetes-fastapi-sse` |

The same bundle compiles to **any combination** — swap `--targets` and nothing
else changes. No DTOs, no per-target IR forks, no Traefik.

## Quick start

```bash
# List what generators are available
python -m factory.cli list

# Show the stable hash of a bundle (useful for image caching)
python -m factory.cli hash bundles/connect-test-service.bundle.json --contracts contracts

# Compile SERVICE_BUNDLE into Python+Docker+OpenAPI
python -m factory.cli compile bundles/connect-test-service.bundle.json \
    --contracts contracts \
    --targets python-fastapi,docker,openapi \
    --out ./dist

# Same bundle as Node + k8s
python -m factory.cli compile bundles/connect-test-service-node.bundle.json \
    --contracts contracts \
    --targets node-fastify,kubernetes \
    --out ./dist-node

# Compile VIEW_BUNDLE (read-only aggregation view) into a PHP standalone
python -m factory.cli compile bundles/protocol-dashboard.bundle.json \
    --targets view/php-standalone \
    --out ./dist-dashboard

# Tests
pytest tests/
```

## Why this format

Your existing contract directory is already a near-perfect IR. Each
`*.command.json` describes one command end-to-end: input schema, output schema,
HTTP/WS transport, storage mapping, success/failure events, and which layers
implement it. We don't replace that — we build **one layer above**:

```
bundle.json → references N contracts + adds { runtime, storage, companions, ttl }
     ↓
   loader produces Bundle (in-memory IR)
     ↓
   each Generator is Bundle → {path: content}
     ↓
   CLI writes all the paths to disk
```

Generators are **pure, stateless, independent**. The Docker generator knows
nothing about Python. The Python generator knows nothing about k8s. The OpenAPI
generator knows nothing about either. That's the whole point — three axes, one
IR, every combination works.

## The bundle format

```jsonc
{
  "bundle": "connect-test-service",
  "kind": "SERVICE_BUNDLE",
  "version": "1.0.0",
  "description": "Test protocol and device lifecycle service",

  "runtime": {
    "language": "python",        // python | node | go | rust
    "version": "3.12",
    "framework": "fastapi"       // fastapi | fastify | chi | actix
  },

  "contracts": [                 // paths resolved against --contracts dir
    "CompleteProtocol.command.json",
    "DemoLogin.command.json",
    "DeviceCreated.event.json",
    "DeviceUpdated.event.json"
  ],

  "storage": {
    "kind": "postgres",          // none | postgres | sqlite | mongodb
    "database": "IdentificationDb",
    "tables": ["protocols", "devices"]
  },

  "companions": [
    {
      "name": "llm-proxy",
      "kind": "litellm",          // litellm | mcp | redis | postgres | custom
      "config": {
        "model": "openrouter/qwen/qwen3-coder-next"
      }
    }
  ],

  "resources": { "cpu": "500m", "memory": "512Mi" },
  "ttl": "24h",
  "exposure": { "port": 8080, "health_path": "/health" }
}
```

Bundle hash (first 16 hex chars of sha256 over the canonical JSON of
runtime + storage + companions + resources + exposure + contracts) is
**deterministic** — two bundles with identical input produce identical
artifacts byte-for-byte, which is what lets a runtime cache built images by
hash.

## Adding a new generator

Three steps, same loop everywhere:

1. Write a class with `target`, `category`, and `generate(bundle) -> dict`.

   ```python
   class GoChiGenerator:
       target = "go-chi"
       category = "code"

       def generate(self, bundle: Bundle) -> dict[str, str]:
           return {
               "main.go": self._main(bundle),
               "go.mod": self._gomod(bundle),
           }
   ```

2. Register it in `factory/__init__.py::register_default_generators`.

3. Write tests that at minimum parse the output (`ast.parse` for code, `yaml.safe_load` for YAML, `json.loads` for JSON).

That's the whole contract. Generators can't see each other, can't read the
filesystem, can't hold state.

## What's intentionally NOT in scope

- **Reverse proxy / TLS termination.** No Traefik, no Nginx in front of
  generated services. Each service exposes one host port directly. If you need
  ingress, layer it on top — the factory doesn't opinion.
- **Runtime management.** The factory emits artifacts; it doesn't run
  containers. `docker compose up` or `kubectl apply` is the next module's job.
- **Business logic.** Generated handlers are stubs that raise 501. The
  contracts include `layers.handler` pointing at where the real logic lives;
  wiring that in is the integrator's choice.
- **Migrations, auth, telemetry.** Out of scope. Cross-cutting concerns belong
  in sidecars or platform-wide middleware, not in a per-service generator.

## Layout

```
service-factory/
├── factory/
│   ├── __init__.py             Generator registry
│   ├── cli.py                  compile | list | hash
│   ├── ir/
│   │   └── __init__.py         Bundle + Contract + BundleLoader
│   └── generators/
│       ├── types.py            Cross-target type mapping
│       ├── code/
│       │   ├── python_fastapi.py
│       │   └── node_fastify.py
│       ├── infra/
│       │   ├── docker.py
│       │   └── kubernetes.py
│       ├── wire/
│       │   └── openapi.py
│       └── view/
│           ├── php_standalone.py
│           ├── static_html.py
│           ├── fastapi_sse.py
│           ├── docker_fastapi_sse.py
│           └── kubernetes_fastapi_sse.py
├── bundles/
│   ├── connect-test-service.bundle.json        (Python + Docker + Postgres + LiteLLM)
│   ├── connect-test-service-node.bundle.json   (Node + k8s, no storage)
│   └── protocol-dashboard.bundle.json          (VIEW_BUNDLE → PHP standalone)
├── contracts/                   Sample CQRS contracts (from the existing ecosystem)
├── tests/
│   └── test_factory.py          15 tests, all green
└── README.md
```

## Coupling back to the ecosystem

This module is self-contained and has no runtime dependency on the main
CQRS-URL API. It's a pure build tool — one side reads contracts, the other
writes artifacts. The obvious integration point with the rest of the platform
is exposing it as a CQRS command:

```
PUT /commands/compile-service
  body: { bundle_uri: "file:///bundles/connect-test-service.bundle.json",
          targets: ["python-fastapi", "docker"] }
  → returns artifacts bundle URI (data:application/gzip;base64,…)
```

That's a 20-line wrapper around this CLI. Deliberately not written yet — it
belongs in the next module, the **Service Runtime** that actually deploys the
compiled artifacts.

## License

Apache-2.0.

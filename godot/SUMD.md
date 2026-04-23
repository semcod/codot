# Godot

Godot

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Workflows](#workflows)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Environment Variables (`.env.example`)](#environment-variables-envexample)
- [Makefile Targets](#makefile-targets)
- [Code Analysis](#code-analysis)
- [Call Graph](#call-graph)
- [Intent](#intent)

## Metadata

- **name**: `godot`
- **version**: `0.0.0`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: Makefile, app.doql.less, .env.example, Dockerfile, docker-compose.yml, project/(2 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: godot;
  version: 0.1.0;
}

database[name="postgres"] {
  type: postgresql;
  url: env.DATABASE_URL;
}

interface[type="api"] {
  type: rest;
  framework: fastapi;
}

workflow[name="build"] {
  trigger: manual;
  step-1: run cmd=bash scripts/build.sh;
}

workflow[name="validate"] {
  trigger: manual;
  step-1: run cmd=bash scripts/validate-bundle.sh $(BUNDLE);
}

workflow[name="validate-all"] {
  trigger: manual;
  step-1: run cmd=bash scripts/validate-all.sh;
}

workflow[name="test"] {
  trigger: manual;
  step-1: run cmd=cd src && GOFLAGS=-mod=mod go test -v bundle.go bundle_test.go;
}

workflow[name="docker-build"] {
  trigger: manual;
  step-1: run cmd=docker build -t godot-bundle-service .;
}

workflow[name="docker-test"] {
  trigger: manual;
  step-1: run cmd=docker run --rm godot-bundle-service bash scripts/validate-all.sh;
}

workflow[name="docker-up"] {
  trigger: manual;
  step-1: run cmd=docker-compose up -d;
}

workflow[name="docker-down"] {
  trigger: manual;
  step-1: run cmd=docker-compose down;
}

workflow[name="stop"] {
  trigger: manual;
  step-1: run cmd=echo "=== Stopping Godot Bundle System ===";
  step-2: run cmd=-docker-compose down 2>/dev/null;
  step-3: run cmd=-docker rm -f godot-bundle-service godot-llm godot-mock-api temporal-server temporal-postgres schema-server 2>/dev/null;
  step-4: run cmd=echo "Killing processes on ports...";
  step-5: run cmd=-for port in 9000 9001 9002 9003 18094 18095 5433 8084; do \;
  step-6: run cmd=pid=$$(lsof -t -i:$$port 2>/dev/null) && kill -9 $$pid 2>/dev/null || true; \;
  step-7: run cmd=done;
  step-8: run cmd=echo "✓ Stopped";
}

workflow[name="restart"] {
  trigger: manual;
  step-1: depend target=stop;
  step-2: depend target=start;
}

workflow[name="status"] {
  trigger: manual;
  step-1: run cmd=echo "=== Godot Bundle System Status ===";
  step-2: run cmd=echo "Docker containers:";
  step-3: run cmd=docker ps --filter name=godot --filter name=temporal --filter name=schema --filter name=mock-api --filter name=godot-llm --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No containers running";
  step-4: run cmd=echo "";
  step-5: run cmd=echo "Port status:";
  step-6: run cmd=for port in 9000 9001 9002 9003 18094 18095 5433 7233 8084; do \;
  step-7: run cmd=if lsof -i:$$port >/dev/null 2>&1; then \;
  step-8: run cmd=echo "  Port $$port: ✓ in use"; \;
  step-9: run cmd=else \;
  step-10: run cmd=echo "  Port $$port: - free"; \;
  step-11: run cmd=fi \;
  step-12: run cmd=done;
  step-13: run cmd=echo "";
  step-14: run cmd=echo "Logs: docker-compose logs -f";
}

workflow[name="start"] {
  trigger: manual;
  step-1: run cmd=echo "=== Starting Godot Bundle System ===";
  step-2: run cmd=echo "Step 1: Cleaning up existing containers and ports...";
  step-3: run cmd=$(MAKE) stop;
  step-4: run cmd=echo "";
  step-5: run cmd=echo "Step 2: Building Docker image...";
  step-6: run cmd=$(MAKE) docker-build;
  step-7: run cmd=echo "";
  step-8: run cmd=echo "Step 3: Starting Docker services...";
  step-9: run cmd=docker-compose up -d;
  step-10: run cmd=echo "";
  step-11: run cmd=echo "Waiting for services to start...";
  step-12: run cmd=sleep 5;
  step-13: run cmd=echo "";
  step-14: run cmd=echo "Step 4: Running service tests...";
  step-15: run cmd=$(MAKE) test-services;
  step-16: run cmd=echo "";
  step-17: run cmd=echo "=== Godot Bundle System is running ===";
  step-18: run cmd=echo "";
  step-19: run cmd=bash -c 'source .env && echo "Service URLs:" && \;
  step-20: run cmd=echo "  Schema Server:  http://localhost:$${SCHEMA_SERVER_PORT:-8084}/bundle.schema.json" && \;
  step-21: run cmd=echo "  Temporal Web:   http://localhost:$${TEMPORAL_PORT:-7233}" && \;
  step-22: run cmd=echo "  PostgreSQL:     localhost:$${POSTGRES_PORT:-5433}" && \;
  step-23: run cmd=echo "  LLM API:        http://localhost:$${LLM_PORT:-18094}/health" && \;
  step-24: run cmd=echo "  Mock API:       http://localhost:$${MOCK_API_PORT:-18095}/health"';
  step-25: run cmd=echo "";
  step-26: run cmd=echo "Useful commands:";
  step-27: run cmd=echo "  make stop     - Stop all services";
  step-28: run cmd=echo "  make restart  - Restart all services";
  step-29: run cmd=echo "  make status   - Check service status";
}

workflow[name="quickstart"] {
  trigger: manual;
  step-1: run cmd=$(MAKE) start;
}

workflow[name="test-services"] {
  trigger: manual;
  step-1: run cmd=bash scripts/test-services.sh;
  step-2: run cmd=bash scripts/test-llm.sh;
}

workflow[name="llm-test"] {
  trigger: manual;
  step-1: run cmd=bash scripts/test-llm.sh;
}

workflow[name="run"] {
  trigger: manual;
  step-1: run cmd=echo "Starting PHP server on port $(PORT)...";
  step-2: run cmd=cd generated && php -S 0.0.0.0:$(PORT) dashboard.php;
}

workflow[name="run-bundle"] {
  trigger: manual;
  step-1: run cmd=bash scripts/run-bundle.sh $(BUNDLE);
}

workflow[name="deploy"] {
  trigger: manual;
  step-1: run cmd=echo "Starting Temporal worker (background)...";
  step-2: run cmd=cd src && GOFLAGS=-mod=mod go run deploy_workflow.go &;
  step-3: run cmd=echo "Starting workflow with bundle $(BUNDLE)...";
  step-4: run cmd=cd src && GOFLAGS=-mod=mod go run starter.go @../$(BUNDLE);
}

workflow[name="clean"] {
  trigger: manual;
  step-1: run cmd=-pkill -f "php -S 0.0.0.0";
  step-2: run cmd=-pkill -f "go run deploy_workflow.go";
  step-3: run cmd=echo "Cleaned up";
}

deploy {
  target: docker-compose;
  compose_file: docker-compose.yml;
}

environment[name="local"] {
  runtime: docker-compose;
  env_file: .env;
}
```

## Workflows

## Configuration

```yaml
project:
  name: godot
  version: 0.0.0
  env: local
```

## Deployment

```bash markpact:run
pip install godot

# development install
pip install -e .[dev]
```

### Docker

- **base image**: `golang:1.21-alpine`
- **expose**: `8080`, `8081`, `8082`, `8083`
- **entrypoint**: `["/bin/bash"]`

### Docker Compose (`docker-compose.yml`)

- **godot** image=`{'context': '.', 'dockerfile': 'Dockerfile'}` ports: `${GODOT_PORT_8080:-8080}:8080`, `${GODOT_PORT_8081:-8081}:8081`, `${GODOT_PORT_8082:-8082}:8082`, `${GODOT_PORT_8083:-8083}:8083`
- **temporal** image=`temporalio/auto-setup:latest` ports: `${TEMPORAL_PORT:-7233}:7233`, `8233:8233`
- **postgres** image=`postgres:13-alpine` ports: `${POSTGRES_PORT:-5433}:5432`
- **schema-server** image=`caddy:latest` ports: `${SCHEMA_SERVER_PORT:-8084}:80`
- **llm** image=`{'context': '.', 'dockerfile': 'llm/Dockerfile'}` ports: `${LLM_PORT:-18094}:8000`
- **mock-api** image=`{'context': '.', 'dockerfile': 'llm/Dockerfile'}` ports: `${MOCK_API_PORT:-18095}:8001`

## Environment Variables (`.env.example`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | `*(not set)*` | Required: OpenRouter API key (https://openrouter.ai/keys) |
| `LLM_MODEL` | `openrouter/qwen/qwen3-coder-next` | Model (default: openrouter/qwen/qwen3-coder-next) |
| `PFIX_AUTO_APPLY` | `true` | true = apply fixes without asking |
| `PFIX_AUTO_INSTALL_DEPS` | `true` | true = auto pip/uv install |
| `PFIX_AUTO_RESTART` | `false` | true = os.execv restart after fix |
| `PFIX_MAX_RETRIES` | `3` |  |
| `PFIX_DRY_RUN` | `false` |  |
| `PFIX_ENABLED` | `true` |  |
| `PFIX_GIT_COMMIT` | `false` | true = auto-commit fixes |
| `PFIX_GIT_PREFIX` | `pfix:` | commit message prefix |
| `PFIX_CREATE_BACKUPS` | `false` | false = disable .pfix_backups/ directory |

## Makefile Targets

- `BUNDLE`
- `PORT`
- `help`
- `all`
- `build`
- `validate`
- `validate-all`
- `test`
- `docker-build`
- `docker-test`
- `docker-up`
- `docker-down`
- `stop`
- `restart`
- `status`
- `start`
- `quickstart`
- `test-services`
- `llm-test`
- `run`
- `run-bundle`
- `deploy`
- `clean`

## Code Analysis

### `project/map.toon.yaml`

```toon markpact:analysis path=project/map.toon.yaml
# godot | 18f 2092L | shell:11,go:5,less:1,python:1 | 2026-04-23
# stats: 34 func | 6 cls | 18 mod | CC̄=3.6 | critical:1 | cycles:0
# alerts[5]: CC fetch_uri=10; CC infer_output_format=9; CC infer_kind=8; CC maybe_refine_bundle=8; CC compact=7
# hotspots[5]: fetch_uri fan=20; build_bundle_from_prompt fan=12; list_bundles fan=8; maybe_refine_bundle fan=7; validate_bundle fan=7
# evolution: baseline
# Keys: M=modules, D=details, i=imports, e=exports, c=classes, f=functions, m=methods
M[18]:
  app.doql.less,178
  llm/app.py,596
  project.sh,40
  scripts/build.sh,17
  scripts/install.sh,101
  scripts/quickstart.sh,22
  scripts/run-bundle.sh,35
  scripts/run.sh,7
  scripts/starter.sh,17
  scripts/test-llm.sh,196
  scripts/test-services.sh,138
  scripts/validate-all.sh,32
  scripts/validate-bundle.sh,66
  src/bundle.go,180
  src/bundle_test.go,231
  src/deploy_workflow.go,118
  src/starter.go,85
  src/structs.go,33
D:
  llm/app.py:
    e: env_bool,env_int,env_float,slugify,dedupe,compact,is_private_host,build_state,infer_kind,infer_targets,infer_runner,infer_output_format,infer_runtime,source_name_from_uri,build_sources,normalize_bundle,maybe_refine_bundle,validate_bundle,fetch_uri,fetch_many,build_bundle_from_prompt,write_bundle,health,list_bundles,describe_acl,fetch_single,fetch_context,generate_bundle,generate_bundles,mock_health,mock_devices,mock_protocol,mock_posts,mock_catalog,Settings,ACLPolicy,FetchRequest,FetchManyRequest,GenerateBundleRequest,AppState
    Settings:
    ACLPolicy: from_file(2),_matches_any(2),allows(1),describe(0)
    FetchRequest:
    FetchManyRequest:
    GenerateBundleRequest:
    AppState:
    env_bool(name;default)
    env_int(name;default)
    env_float(name;default)
    slugify(value)
    dedupe(values)
    compact(value)
    is_private_host(hostname)
    build_state()
    infer_kind(prompt;explicit)
    infer_targets(prompt;explicit;kind)
    infer_runner(kind;targets;explicit)
    infer_output_format(kind;targets;prompt;runner)
    infer_runtime(kind;targets;runner)
    source_name_from_uri(uri;index)
    build_sources(uris)
    normalize_bundle(bundle)
    maybe_refine_bundle(prompt;base_bundle)
    validate_bundle(bundle)
    fetch_uri(request)
    fetch_many(uris)
    build_bundle_from_prompt(request)
    write_bundle(bundle;output_dir)
    health()
    list_bundles()
    describe_acl()
    fetch_single(request)
    fetch_context(request)
    generate_bundle(request)
    generate_bundles(requests)
    mock_health()
    mock_devices()
    mock_protocol(protocol_id)
    mock_posts()
    mock_catalog()
```

## Call Graph

*37 nodes · 31 edges · 5 modules · CC̄=3.1*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `fetch_uri` *(in llm.app)* | 10 ⚠ | 2 | 25 | **27** |
| `main` *(in src.starter)* | 16 ⚠ | 0 | 18 | **18** |
| `build_bundle_from_prompt` *(in llm.app)* | 5 | 1 | 12 | **13** |
| `allows` *(in llm.app.ACLPolicy)* | 13 ⚠ | 0 | 12 | **12** |
| `runGoTemporal` *(in src.bundle)* | 5 | 1 | 9 | **10** |
| `LoadSchema` *(in src.bundle)* | 4 | 1 | 9 | **10** |
| `Run` *(in src.bundle)* | 11 ⚠ | 0 | 9 | **9** |
| `validateBundleData` *(in src.bundle_test)* | 18 ⚠ | 1 | 8 | **9** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/codot/godot
# nodes: 37 | edges: 31 | modules: 5
# CC̄=3.1

HUBS[20]:
  llm.app.fetch_uri
    CC=10  in:2  out:25  total:27
  src.starter.main
    CC=16  in:0  out:18  total:18
  llm.app.build_bundle_from_prompt
    CC=5  in:1  out:12  total:13
  llm.app.ACLPolicy.allows
    CC=13  in:0  out:12  total:12
  src.bundle.runGoTemporal
    CC=5  in:1  out:9  total:10
  src.bundle.LoadSchema
    CC=4  in:1  out:9  total:10
  src.bundle.Run
    CC=11  in:0  out:9  total:9
  src.bundle_test.validateBundleData
    CC=18  in:1  out:8  total:9
  llm.app.maybe_refine_bundle
    CC=8  in:1  out:7  total:8
  llm.app.validate_bundle
    CC=4  in:1  out:7  total:8
  llm.app.compact
    CC=7  in:3  out:5  total:8
  src.deploy_workflow.DeployViewBundle
    CC=7  in:3  out:5  total:8
  src.bundle_test.collectBundleFiles
    CC=5  in:1  out:6  total:7
  llm.app.source_name_from_uri
    CC=4  in:1  out:6  total:7
  src.bundle.fetchSchema
    CC=6  in:1  out:6  total:7
  src.bundle_test.TestBundleSchemaValidation
    CC=3  in:0  out:6  total:6
  llm.app.fetch_many
    CC=3  in:2  out:4  total:6
  llm.app.generate_bundle
    CC=2  in:1  out:5  total:6
  llm.app.normalize_bundle
    CC=2  in:2  out:3  total:5
  llm.app.is_private_host
    CC=5  in:1  out:4  total:5

MODULES:
  llm.app  [22 funcs]
    allows  CC=13  out:12
    build_bundle_from_prompt  CC=5  out:12
    build_sources  CC=4  out:3
    compact  CC=7  out:5
    dedupe  CC=3  out:3
    fetch_context  CC=1  out:3
    fetch_many  CC=3  out:4
    fetch_single  CC=1  out:2
    fetch_uri  CC=10  out:25
    generate_bundle  CC=2  out:5
  src.bundle  [6 funcs]
    LoadSchema  CC=4  out:9
    Run  CC=11  out:9
    fetchSchema  CC=6  out:6
    runGoTemporal  CC=5  out:9
    runPythonFastAPI  CC=2  out:3
    workflowNameForKind  CC=5  out:0
  src.bundle_test  [3 funcs]
    TestBundleSchemaValidation  CC=3  out:6
    collectBundleFiles  CC=5  out:6
    validateBundleData  CC=18  out:8
  src.deploy_workflow  [4 funcs]
    DeployApplicationBundle  CC=1  out:1
    DeployServiceBundle  CC=1  out:1
    DeployViewBundle  CC=7  out:5
    DeployWorkflowBundle  CC=1  out:1
  src.starter  [2 funcs]
    main  CC=16  out:18
    workflowNameForKind  CC=5  out:0

EDGES:
  src.bundle_test.TestBundleSchemaValidation → src.bundle_test.collectBundleFiles
  src.bundle_test.TestBundleSchemaValidation → src.bundle_test.validateBundleData
  src.starter.main → src.starter.workflowNameForKind
  src.bundle.LoadSchema → src.bundle.fetchSchema
  src.bundle.Run → src.bundle.LoadSchema
  src.bundle.Run → src.bundle.runGoTemporal
  src.bundle.Run → src.bundle.runPythonFastAPI
  src.bundle.runGoTemporal → src.bundle.workflowNameForKind
  src.deploy_workflow.DeployServiceBundle → src.deploy_workflow.DeployViewBundle
  src.deploy_workflow.DeployWorkflowBundle → src.deploy_workflow.DeployViewBundle
  src.deploy_workflow.DeployApplicationBundle → src.deploy_workflow.DeployViewBundle
  llm.app.ACLPolicy.allows → llm.app.is_private_host
  llm.app.infer_targets → llm.app.dedupe
  llm.app.build_sources → llm.app.source_name_from_uri
  llm.app.normalize_bundle → llm.app.compact
  llm.app.maybe_refine_bundle → llm.app.normalize_bundle
  llm.app.fetch_many → llm.app.fetch_uri
  llm.app.build_bundle_from_prompt → llm.app.infer_kind
  llm.app.build_bundle_from_prompt → llm.app.infer_targets
  llm.app.build_bundle_from_prompt → llm.app.infer_runner
  llm.app.build_bundle_from_prompt → llm.app.build_sources
  llm.app.build_bundle_from_prompt → llm.app.normalize_bundle
  llm.app.build_bundle_from_prompt → llm.app.validate_bundle
  llm.app.build_bundle_from_prompt → llm.app.slugify
  llm.app.build_bundle_from_prompt → llm.app.infer_output_format
  llm.app.build_bundle_from_prompt → llm.app.maybe_refine_bundle
  llm.app.fetch_single → llm.app.fetch_uri
  llm.app.fetch_context → llm.app.fetch_many
  llm.app.generate_bundle → llm.app.build_bundle_from_prompt
  llm.app.generate_bundle → llm.app.write_bundle
  llm.app.generate_bundles → llm.app.generate_bundle
```

## Intent

Godot

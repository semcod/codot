# Godot

SUMD - Structured Unified Markdown Descriptor for AI-aware project refactorization

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Workflows](#workflows)
- [Call Graph](#call-graph)
- [Refactoring Analysis](#refactoring-analysis)
- [Intent](#intent)

## Metadata

- **name**: `godot`
- **version**: `0.0.0`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: Makefile, app.doql.less, .env.example, Dockerfile, docker-compose.yml, project/(5 analysis files)

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

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

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

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 34f 4656L | shell:10,json:6,go:5,md:3,yaml:2,conf:1,yml:1,php:1,txt:1,python:1 | 2026-04-23
# CC̄=3.1 | critical:2/88 | dups:0 | cycles:1

HEALTH[4]:
  🔴 GOD   README.md = 2073L, 5 classes, 19m, max CC=0.0
  🔴 GOD   llm/app.py = 595L, 6 classes, 38m, max CC=13
  🟡 CC    validateBundleData CC=18 (limit:15)
  🟡 CC    main CC=16 (limit:15)

REFACTOR[4]:
  1. split README.md  (god module)
  2. split llm/app.py  (god module)
  3. split 2 high-CC methods  (CC>15)
  4. break 1 circular dependencies

PIPELINES[33]:
  [1] Src [fetchData]: fetchData
      PURITY: 100% pure
  [2] Src [updateData]: updateData
      PURITY: 100% pure
  [3] Src [TestBundleSchemaValidation]: TestBundleSchemaValidation → collectBundleFiles
      PURITY: 100% pure
  [4] Src [TestSourceValidation]: TestSourceValidation
      PURITY: 100% pure
  [5] Src [TestOutputValidation]: TestOutputValidation
      PURITY: 100% pure

LAYERS:
  src/                            CC̄=5.3    ←in:0  →out:0
  │ !! bundle_test.go             230L  0C    6m  CC=18     ←0
  │ bundle.go                  179L  3C    6m  CC=11     ←0
  │ deploy_workflow.go         117L  3C    9m  CC=7      ←0
  │ !! starter.go                  84L  1C    2m  CC=16     ←0
  │ structs.go                  32L  4C    0m  CC=0.0    ←0
  │
  llm/                            CC̄=3.9    ←in:0  →out:0
  │ !! app                        595L  6C   38m  CC=13     ←0
  │ acl.yaml                    31L  0C    0m  CC=0.0    ←0
  │ requirements.txt             7L  0C    0m  CC=0.0    ←0
  │ Dockerfile                   0L  0C    0m  CC=0.0    ←0
  │
  generated/                      CC̄=1.0    ←in:0  →out:0
  │ dashboard.php               34L  0C    2m  CC=1      ←0
  │
  scripts/                        CC̄=0.0    ←in:0  →out:0
  │ test-llm.sh                195L  0C    3m  CC=0.0    ←0
  │ test-services.sh           137L  0C    2m  CC=0.0    ←0
  │ install.sh                 100L  0C    0m  CC=0.0    ←0
  │ validate-bundle.sh          65L  0C    1m  CC=0.0    ←0
  │ run-bundle.sh               34L  0C    0m  CC=0.0    ←0
  │ validate-all.sh             31L  0C    0m  CC=0.0    ←0
  │ quickstart.sh               21L  0C    0m  CC=0.0    ←0
  │ starter.sh                  16L  0C    0m  CC=0.0    ←0
  │ run.sh                       6L  0C    0m  CC=0.0    ←0
  │
  ./                              CC̄=0.0    ←in:0  →out:0
  │ !! README.md                 2073L  5C   19m  CC=0.0    ←0
  │ SUMD.md                    203L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml         122L  0C    0m  CC=0.0    ←0
  │ bundle.schema.json          91L  0C    0m  CC=0.0    ←0
  │ project.sh                  40L  0C    0m  CC=0.0    ←0
  │ TODO.md                     21L  0C    0m  CC=0.0    ←0
  │ caddy.conf                  16L  0C    0m  CC=0.0    ←0
  │ Dockerfile                   0L  0C    0m  CC=0.0    ←0
  │ Makefile                     0L  0C    0m  CC=0.0    ←0
  │
  bundles/                        CC̄=0.0    ←in:0  →out:0
  │ service_bundle.json         33L  0C    0m  CC=0.0    ←0
  │ workflow_bundle.json        33L  0C    0m  CC=0.0    ←0
  │ protocol-dashboard.json     33L  0C    0m  CC=0.0    ←0
  │ view_bundle_sse.json        29L  0C    0m  CC=0.0    ←0
  │ static_bundle.json          25L  0C    0m  CC=0.0    ←0
  │
  project/                        CC̄=0.0    ←in:0  →out:0
  │ map.toon.yaml               23L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
     Dockerfile                                0L
     Makefile                                  0L
     llm/Dockerfile                            0L

COUPLING: no cross-package imports detected

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 1 groups | 1f 595L | 2026-04-23

SUMMARY:
  files_scanned: 1
  total_lines:   595
  dup_groups:    1
  dup_fragments: 2
  saved_lines:   8
  scan_ms:       4765

HOTSPOTS[1] (files with most duplication):
  llm/app.py  dup=16L  groups=1  frags=2  (2.7%)

DUPLICATES[1] (ranked by impact):
  [07c2810340de43fb]   STRU  env_int  L=8 N=2 saved=8 sim=1.00
      llm/app.py:48-55  (env_int)
      llm/app.py:58-65  (env_float)

REFACTOR[1] (ranked by priority):
  [1] ○ extract_function   → llm/utils/env_int.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: llm/app.py

QUICK_WINS[1] (low risk, high savings — do first):
  [1] extract_function   saved=8L  → llm/utils/env_int.py
      FILES: app.py

EFFORT_ESTIMATE (total ≈ 0.3h):
  easy   env_int                             saved=8L  ~16min

METRICS-TARGET:
  dup_groups:  1 → 0
  saved_lines: 8 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 82 func | 7f | 2026-04-23

NEXT[3] (ranked by impact):
  [1] !! SPLIT           llm/app.py
      WHY: 595L, 6 classes, max CC=13
      EFFORT: ~4h  IMPACT: 7735

  [2] !  SPLIT-FUNC      main  CC=16  fan=18
      WHY: CC=16 exceeds 15
      EFFORT: ~1h  IMPACT: 288

  [3] !  SPLIT-FUNC      validateBundleData  CC=18  fan=8
      WHY: CC=18 exceeds 15
      EFFORT: ~1h  IMPACT: 144


RISKS[1]:
  ⚠ Splitting llm/app.py may break 38 import paths

METRICS-TARGET:
  CC̄:          3.3 → ≤2.3
  max-CC:      18 → ≤9
  god-modules: 1 → 0
  high-CC(≥15): 2 → ≤1
  hub-types:   0 → ≤0

PATTERNS (language parser shared logic):
  _extract_declarations() in base.py — unified extraction for:
    - TypeScript: interfaces, types, classes, functions, arrow funcs
    - PHP: namespaces, traits, classes, functions, includes
    - Ruby: modules, classes, methods, requires
    - C++: classes, structs, functions, #includes
    - C#: classes, interfaces, methods, usings
    - Java: classes, interfaces, methods, imports
    - Go: packages, functions, structs
    - Rust: modules, functions, traits, use statements

  Shared regex patterns per language:
    - import: language-specific import/require/using patterns
    - class: class/struct/trait declarations with inheritance
    - function: function/method signatures with visibility
    - brace_tracking: for C-family languages ({ })
    - end_keyword_tracking: for Ruby (module/class/def...end)

  Benefits:
    - Consistent extraction logic across all languages
    - Reduced code duplication (~70% reduction in parser LOC)
    - Easier maintenance: fix once, apply everywhere
    - Standardized FunctionInfo/ClassInfo models

HISTORY:
  (first run — no previous data)
```

## Intent

Godot

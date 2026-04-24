---
title: "CQRS-URL Platform — reference implementation is live"
status: publish
categories: [Architecture, Projects]
tags: [cqrs, python, fastapi, docker]
author: Softreck
date: 2026-04-22
---

## What this project is

The **CQRS-URL Platform** is a compact reference implementation of a pattern we've been refining for a while: treating every Command and every Query as a **URL-addressable resource** that operates on other URL-addressable resources. No DTOs baked into `.proto` files or schema registries, no per-command type gymnastics. The command you want to run is the URL you call; the data you want to act on is the URL you pass as `input_uri`; the optional schema you want to validate against is a third URL.

The design goal was to remove the friction of adding a new command. Today, in this repo, that friction is three steps:

1. Drop a file into `api/commands/`.
2. Register it in `register_default_commands`.
3. Optionally add a policy rule.

That's it. No proto regeneration, no frontend DTOs, no migrations.

## Status — April 2026

The platform is **runnable end-to-end** and covers the full loop described in the design notes. A single `make up` brings up four containers (API, schema server, sample-data server, frontend playground) and a `make test` runs fifteen curl-level checks against the running stack, including path-traversal blocking, role-based denials, agent backends, pipeline with agent nodes, and service-factory code generation.

What works today:

- **Protocol registry** with `http://`, `https://`, `file://` (root-contained), and `data:` (RFC 2397). Adding a new scheme is one class with a `scheme` attribute and an async `fetch` method.
- **Command registry** with eight built-ins: `fetch`, `converttojson`, `converttoxml`, `converttocsv`, `converttobase64`, `render` (Jinja2 → HTML), `pipeline` (composes the others with `"$previous.output"` as a URI reference), and `compile_service` (generates deployable artifacts from a bundle via the service-factory generator registry).
- **Query registry** with `from-url` and `introspect`.
- **Policy engine** — RBAC with shell-style glob patterns over command names, URIs, and schema URIs. Rules live in a YAML file that's mounted into the API container, so they can be changed without rebuilding the image.
- **JWT auth** with three demo roles — `admin`, `analyst`, `user` — each mapped to a different slice of the policy space.
- **Runtime JSON Schema validation** where the schema is fetched from any protocol (so the schema itself can live in a file, at an HTTP URL, or inline as a `data:` URI).
- **Agent execution layer** — multi-backend agent runtime with support for MCP (Model Context Protocol via JSON-RPC 2.0 over stdio/SSE), LiteLLM, Bash CLI, HTTP API, and WebSocket. Agents are defined by `role`, `goal`, `tools`, and `backend_config`.
- **MCP client** — lightweight JSON-RPC 2.0 client (`api/mcp_client.py`) with `MCPStdioClient` and `MCPSseClient`, handling `initialize`, `tools/list`, and `tools/call`.
- **Pipeline with agent nodes** — `PipelineStep` accepts an optional `agent_node`, so a workflow can mix deterministic commands and autonomous agents. The pipeline decodes `data:` URIs from `$previous.output` and injects them into the agent context automatically.
- **CLI runner** — `codot_run.py` lets you execute workflows and agents from shell without writing curl: `python3 codot_run.py workflow.json` (reads `API_BASE_URL` from `.env`).

What doesn't exist yet, and what would come next:

- **More protocols** — S3, FTP, Redis, Postgres, Kafka. The registry is ready for them; nobody has written them.
- **Horizontal scaling story** — the service is stateless, but there's no queue in front of long-running commands. `converttobase64` on a 40 MB PDF is fine; anything heavier should be backgrounded.
- **Better error taxonomy** — validation errors, policy denials and fetch failures all currently land as generic 400/403/404 JSON. A typed error body with `error_code` strings would make clients happier.
- **No write-side commands yet** — `store`, `publish`, `enqueue` are sketched in the design doc but not implemented. We want to get the policy story airtight for writes before shipping them.
- **Agent memory / shared blackboard** — agents have `memory_uri` in the schema but no persistent memory store is wired up yet.

## Why we're happy with it

Three things we learned that we didn't expect:

1. **Commands that reference the previous step's output as a URI are surprisingly clean.** The `pipeline` command substitutes `"$previous.output"` with a `data:<mime>;base64,<...>` URI at runtime. That means step N never has to know whether step N-1 produced text or a PDF — it just reads a URI like any other. The composition is protocol-polymorphic without any special code paths.
2. **Having the file protocol refuse anything outside `ALLOWED_LOCAL_ROOTS` at the fetch layer means policy rules don't have to double-check paths.** It turned a whole class of misconfigurations into a non-issue.
3. **JSON Schema loaded at runtime from a URL is expressive enough for almost every "Command requires a schema" case** from the design doc. We haven't needed to reach for OpenAPI or protobuf yet.

## How to try it

### Basic stack

```bash
git clone <this-repo>
cd cqrs-url-platform
make build && make up
make token                      # admin token
open http://localhost:8000      # playground
```

Sign in as `bob/bob` (role: user) and try to hit `file:///data/products.csv` — you'll get a 403. Sign in as `alice/alice` (role: analyst) and the same call succeeds. That's the policy engine earning its keep.

### Run an MCP agent from CLI

```bash
# Start the API server
cd api && python3 -m uvicorn main:app --host 0.0.0.0 --port 18080

# Run a standalone MCP agent (reads API_BASE_URL from .env)
python3 codot_run.py examples/agent_mcp.json --agent

# Run a workflow with an MCP agent step
python3 codot_run.py examples/workflow_agent_mcp.json
```

The CLI (`codot_run.py`) reads a JSON workflow or agent definition, authenticates, and dispatches to the API. For workflows it converts the DAG JSON into a `pipeline` command with `$previous.output` wiring. For agents it hits `POST /agents/{id}/run`.

### Run the integration test suite

```bash
pytest api/test_all_agents.py -v
```

This exercises all backends: MCP stdio, Bash CLI, LiteLLM (mock), and pipeline with an agent node.

## Links

- Repository layout and adding-a-command guide: `README.md`
- Policy rules: `api/policy/rules.yaml`
- Agent design notes: `docs/03-multi-agent-architecture.md`
- Workflow editor spec: `docs/04-workflow-editor-spec.md`
- Design notes: `articles/` (four Markdown posts covering decoupling DTOs, Command-as-URL, required schemas, and access control)

# codot is CQRS-URL Platform


## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-0.1.13-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$2.10-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-6.3h-blue) ![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)

- 🤖 **LLM usage:** $2.1000 (14 commits)
- 👤 **Human dev:** ~$626 (6.3h @ $100/h, 30min dedup)

Generated on 2026-04-23 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/qwen/qwen3-coder-next)

---

Commands and Queries as **URL-addressable resources**. Operate on arbitrary data over pluggable protocols (`http://`, `https://`, `file://`, `data:`, …), with runtime JSON-Schema validation and policy-based access control — no DTOs, no codegen, no per-command type churn.

This is the reference implementation of the design discussed in the accompanying articles:

- CQRS decoupled from data models (bytes + Struct envelope)
- Command/Query as a URL resource (`PUT /commands/converttojson`)
- Required schemas at runtime (JSON Schema at `schema_uri`)
- Controlling who can do what on which URI (policy engine with URL globs)

## Quick start

### Full Docker stack

```bash
# 1. Build and run everything
make build
make up

# 2. Issue a token (admin)
make token

# 3. Open the playground
#    → http://localhost:8000
#
#    Sign in with admin/admin, alice/alice (analyst), or bob/bob (user).
#    Hit one of the preset buttons: CSV → JSON, render posts, pipeline.

# 4. Smoke-test the API (15 tests: commands, queries, policy, agents, compile_service)
make test
```

### Local development (agents / MCP)

For agent execution with local MCP servers, run the API directly (outside Docker) so the spawned MCP subprocesses can access your filesystem:

```bash
# Start the API locally
cd api && python3 -m uvicorn main:app --host 0.0.0.0 --port 28080

# Run a standalone MCP agent
python3 codot_run.py examples/agent_mcp.json --url http://localhost:28080 --agent

# Run a workflow with an agent step
python3 codot_run.py examples/workflow_agent_mcp.json --url http://localhost:28080
# or simply:
make workflow

# Run the agent integration test suite
make test-agent
```

## Endpoints

| Method | Path                          | Purpose                                   |
|--------|-------------------------------|-------------------------------------------|
| GET    | `/health`                     | liveness probe                            |
| GET    | `/catalog`                    | public catalog of commands/queries/protocols/backends |
| POST   | `/auth/token`                 | issue a dev JWT                           |
| GET    | `/auth/me`                    | current principal                         |
| GET    | `/commands`                   | list commands (auth)                      |
| PUT    | `/commands/{name}`            | run a command                             |
| GET    | `/queries`                    | list queries (auth)                       |
| POST   | `/queries/{name}`             | run a query                               |
| POST   | `/agents/{agent_id}/run`      | execute an agent (MCP, LiteLLM, Bash, etc.) |
| GET    | `/agents/backends`            | list registered agent backends            |
| PUT    | `/commands/compile_service`   | compile a bundle into deployable artifacts |
| GET    | `/docs`                       | OpenAPI / Swagger UI                      |

## Bundled commands

| Name            | Purpose                                                                 |
|-----------------|-------------------------------------------------------------------------|
| `fetch`         | read a resource from any protocol and return its raw bytes (base64)    |
| `converttojson` | fetch + transform CSV/text/XML to JSON (+ optional schema validation)   |
| `converttoxml`  | fetch JSON/CSV and emit XML                                             |
| `converttocsv`  | fetch JSON list-of-objects and emit CSV                                 |
| `converttobase64` | base64-encode any resource (useful for PDFs, images)                  |
| `render`        | Jinja2 template → HTML page (data from URI or inline)                   |
| `pipeline`      | chain other commands; use `"$previous.output"` as a URI reference       |
| `compile_service`| compile a SERVICE_BUNDLE or VIEW_BUNDLE into deployable artifacts (Python/Docker/PHP/k8s) |

Adding your own command is three steps: subclass `Command`, register it, optionally add a policy rule.

## Bundled queries

| Name         | Purpose                                                 |
|--------------|---------------------------------------------------------|
| `from-url`   | fetch one or more URIs and return them in a list        |
| `introspect` | list commands, queries, protocols                       |

## Agent backends

The platform now supports autonomous agents via multiple communication backends. An agent is defined by a `role`, `goal`, `tools`, and a `backend_config`.

| Backend     | Driver | Typical use |
|-------------|--------|-------------|
| `mcp`       | `MCPStdioClient` / `MCPSseClient` | Any MCP-compatible server (JSON-RPC 2.0 over stdio or SSE) |
| `litellm`   | `httpx` | LLM inference via LiteLLM / OpenAI-compatible APIs |
| `bash_cli`  | `asyncio.create_subprocess_shell` | Shell scripts, local tools |
| `http_api`  | `httpx` | Generic REST / GraphQL endpoints |
| `websocket` | `websockets` | Real-time streaming agents |

Agents can be invoked standalone (`POST /agents/{id}/run`) or embedded inside a `pipeline` step via the optional `agent_node` field. The pipeline automatically decodes `data:` URIs from `$previous.output` and injects them into the agent context.

## CLI runner

Run workflows and agents from shell without writing curl:

```bash
# Standalone MCP agent (reads API_BASE_URL from .env by default)
python3 codot_run.py examples/agent_mcp.json --agent

# Workflow with an agent step
python3 codot_run.py examples/workflow_agent_mcp.json
```

## Protocols

| Scheme          | Notes                                                   |
|-----------------|---------------------------------------------------------|
| `http`, `https` | standard fetch via httpx, size-limited                  |
| `file://`       | local reads limited to `ALLOWED_LOCAL_ROOTS` (default: `/data`, `/schemas`) |
| `data:`         | RFC 2397 inline payloads, base64 or percent-encoded     |

Adding a new protocol (e.g. `s3://`, `ftp://`, `sqlite://`) is a matter of writing a class with a `scheme` attribute and an async `fetch(uri)` method, then registering it in `protocols/__init__.py`.

## Policy

Policies are loaded from `api/policy/rules.yaml` at startup. Each rule matches by role and lists glob patterns of allowed command/query names, URIs and schema URIs. Reload without rebuild: edit the file and restart the container (`make restart`).

Three built-in roles:

- **admin** — everything
- **analyst** — all commands/queries, all `http(s)://` and `file:///data`, `file:///schemas`
- **user** — only `fetch`, `converttojson`, `converttobase64`, `render` and public queries, only against `http://cqrs-data/*`, `https://public-*`, `file:///data/public/*`, `data:*`

See also: `api/policy/__init__.py` (the engine), `api/auth/__init__.py` (JWT issuance), `api/main.py` (enforcement point).

## Layout

```
.
├── api/                 FastAPI service
│   ├── commands/        one file per command
│   ├── queries/         one file per query
│   ├── protocols/       pluggable URI fetchers
│   ├── policy/          RBAC engine + rules.yaml
│   ├── validators/      JSON Schema over arbitrary URIs
│   ├── auth/            JWT issuance + FastAPI dependencies
│   ├── agent.py         multi-backend agent execution (MCP, LiteLLM, Bash, HTTP, WS)
│   ├── mcp_client.py    JSON-RPC 2.0 MCP client (stdio + SSE)
│   ├── models.py        envelope (CommandRequest/Response, AgentNode, AgentRequest)
│   ├── config.py        env-based settings
│   ├── test_all_agents.py  integration tests for all agent backends
│   └── main.py          HTTP layer
├── codot_run.py         CLI runner for workflows and agents
├── mcp_servers/         example MCP servers for local testing
│   └── summary_server.py
├── examples/            example workflow and agent JSONs
│   ├── workflow_agent_mcp.json
│   └── agent_mcp.json
├── frontend/            nginx + static playground (HTML/CSS/JS)
├── schemas/             JSON Schemas served at http://schemas/
├── sample-data/         demo data served at http://cqrs-data/
├── tests/
│   ├── smoke.sh         curl-based end-to-end tests
│   ├── test_policy.py   pytest unit tests
│   └── test_protocols.py
├── cqrs-workflow-editor/  React + Vite visual workflow editor (@xyflow/react)
├── articles/            status articles (Markdown, for WordPress)
├── docker-compose.yml
└── Makefile
```

## Adding a command

1. Create `api/commands/my_thing.py`:

```python
from . import Command
from models import CommandRequest, CommandResponse

class MyThingCommand(Command):
    name = "mything"
    description = "Short sentence."
    input_hint = {"input_uri": "...", "meta.foo": "..."}

    async def execute(self, request: CommandRequest) -> CommandResponse:
        # ... do work, return CommandResponse(payload_b64=..., mime=..., meta=...)
```

2. Register it in `api/commands/__init__.py::register_default_commands`.
3. Optionally add an entry in `rules.yaml` if you want non-admins to call it.

That's the whole loop.

## Environment

Copy `.env.example` → `.env` and adjust. Key variables:

- `JWT_SECRET` — must be ≥ 32 chars in production
- `ACCESS_TOKEN_EXPIRE_MINUTES` — default 60
- `ALLOWED_LOCAL_ROOTS` — comma list, default `/data,/schemas`
- `FETCH_MAX_BYTES` — size cap for fetched resources (default 50 MiB)

## License

Licensed under Apache-2.0.

<!-- taskill:status:start -->

## Status

_Last updated by [taskill](https://github.com/oqlos/taskill) at 2026-04-25 13:36 UTC_

| Metric | Value |
|---|---|
| HEAD | `1cb5ec9` |
| Coverage | — |
| Failing tests | — |
| Commits in last cycle | 25 |

> Primarily documentation updates and widespread refactoring. Added a docs-oriented code analysis engine and CLI improvements, and fixed Markdown output in the docs pipeline.

<!-- taskill:status:end -->

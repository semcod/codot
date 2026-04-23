# Multi-Agent Architecture — implemented

> Status: implemented and tested (April 2026)

This document describes the multi-agent execution layer that now lives on top of the CQRS-URL platform. What used to be a "command executor" is now a hybrid system where each pipeline node can be either a deterministic command or an autonomous agent with its own communication backend.

---

# 1. What changed

Before:

> **command executor (deterministic pipeline)**

Now:

> **graph of commands + agents with multiple communication backends**

A node is no longer just a command. It can be an `AgentNode` with:

- `role` — e.g. `data-researcher`, `summarizer`
- `goal` — what the agent should accomplish
- `tools` — list of tool names the agent may call
- `backend` — how the agent communicates (`mcp`, `litellm`, `bash_cli`, `http_api`, `websocket`)
- `backend_config` — backend-specific parameters (e.g. `stdio_command`, `server_url`)

---

# 2. Models

All agent models live in `api/models.py`:

```python
class AgentCommunicationBackend(str, Enum):
    MCP = "mcp"
    LITELLM = "litellm"
    BASH_CLI = "bash_cli"
    HTTP_API = "http_api"
    WEBSOCKET = "websocket"

class AgentNode(BaseModel):
    id: str
    role: str
    goal: str
    tools: list[str]
    backend: AgentCommunicationBackend = AgentCommunicationBackend.MCP
    backend_config: dict[str, Any]
    memory_uri: str | None
    input: str | None
    inputs: list[str]
    description: str | None

class AgentRequest(BaseModel):
    agent_node: AgentNode
    context: dict[str, Any]
    shared_state_uri: str | None

class AgentResponse(BaseModel):
    ok: bool
    output: dict[str, Any]
    reasoning_trace: list[str]
    meta: dict[str, Any]
```

`PipelineStep` was extended with an optional `agent_node` field, so a workflow can mix commands and agents in the same pipeline.

---

# 3. Agent execution backends

All backends are registered in `api/agent.py`.

| Backend   | Driver | Typical use |
|-----------|--------|-------------|
| `mcp`     | `MCPStdioClient` / `MCPSseClient` | Any MCP-compatible server (JSON-RPC 2.0 over stdio or SSE) |
| `litellm` | `httpx` | LLM inference via LiteLLM/OpenAI-compatible APIs |
| `bash_cli`| `asyncio.create_subprocess_shell` | Shell scripts, local tools |
| `http_api`| `httpx` | Generic REST/GraphQL endpoints |
| `websocket`| `websockets` | Real-time streaming agents |

## 3.1 MCP backend

The MCP backend is the most important one. It uses `api/mcp_client.py` — a lightweight JSON-RPC 2.0 client that implements the Model Context Protocol initialize handshake:

1. `initialize` — protocol version negotiation
2. `notifications/initialized` — client ready
3. `tools/list` — discover available tools
4. `tools/call` — invoke the requested tool with arguments from `context`

Example `backend_config` for stdio:

```json
{
  "stdio_command": ["python3", "/abs/path/to/mcp_server.py"]
}
```

Example for SSE:

```json
{
  "server_url": "http://mcp-server:8080/sse"
}
```

A minimal test server is provided in `mcp_servers/summary_server.py`. It exposes a single `summarize` tool.

---

# 4. Pipeline integration

`PipelineCommand` (`api/commands/pipeline.py`) now recognises `agent_node` inside a step:

```python
for idx, step in enumerate(steps):
    agent_node_raw = step.get("agent_node")
    if agent_node_raw is not None:
        agent_node = AgentNode(**agent_node_raw)
        # decode data: URI from $previous.output into agent context
        agent_req = AgentRequest(agent_node=agent_node, context=...)
        agent_resp = await execute_agent(agent_req)
        # agent output becomes a data:application/json;base64 URI for next step
```

This means a workflow DAG can contain a mix of `fetch` / `convert` / `render` commands **and** `agent` nodes, all wired together through `$previous.output`.

---

# 5. API endpoints

Two new endpoints were added in `api/main.py`:

- `POST /agents/{agent_id}/run` — execute a single agent given an `AgentRequest` body
- `GET /agents/backends` — list registered backends (returned by `/catalog` as well)

Policy rules in `api/policy/rules.yaml` grant `agent_run` permission to `admin` and `analyst` roles.

---

# 6. CLI runner

`codot_run.py` in the repo root lets you run workflows and agents from shell without writing curl:

```bash
# Standalone MCP agent
python3 codot_run.py examples/agent_mcp.json --url http://localhost:18080 --agent

# Workflow with an agent step
python3 codot_run.py examples/workflow_agent_mcp.json --url http://localhost:18080
```

The CLI authenticates, converts the JSON definition into the correct API payload, and prints a human-friendly trace.

---

# 7. Mapping: old pipeline → new hybrid pipeline

Old pipeline:

```text
fetch → convert → render
```

New hybrid pipeline:

| Step | Type   | Role / Command | Backend |
|------|--------|----------------|---------|
| fetch1 | command | `fetch` | protocol registry |
| agent1 | agent | `data-researcher` | `mcp` (stdio server) |
| convert1 | command | `converttojson` | — |
| render1 | command | `render` | Jinja2 |

---

# 8. Shared state

`$previous.output` is still the primary mechanism for passing data between steps. When an agent step receives a `data:` URI from the previous step, the pipeline executor decodes it and injects the decoded text into `AgentRequest.context["text"]`.

A full "shared blackboard / memory store" is sketched (the `memory_uri` field exists in the schema) but not yet wired to a persistent backend.

---

# 9. Test harness

`api/test_all_agents.py` exercises all backends end-to-end:

1. **MCP stdio** — talks to `mcp_servers/summary_server.py`
2. **Bash CLI** — runs `echo hello_from_bash`
3. **LiteLLM** — spins up a mock HTTP server and queries it
4. **Pipeline + agent** — runs a two-step pipeline where step 2 is an MCP agent

Run it:

```bash
cd api && python3 test_all_agents.py
```

---

# 10. What comes next

- **Agent memory** — wire `memory_uri` to a real store (Redis, Postgres, S3)
- **Swarm / branching** — currently linear pipeline; add conditional branching and parallel agent execution
- **More MCP servers** — integrate real-world MCP servers (filesystem, GitHub, databases)
- **LLM-agent layer** — hook a real LiteLLM/OpenAI backend for goal-driven agents that choose their own tools

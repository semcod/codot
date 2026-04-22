"""Agent formula executor supporting multiple communication backends.

Backends:
- mcp: Model Context Protocol server (stdio/sse)
- litellm: Unified LLM API gateway
- bash_cli: Shell command execution
- http_api: Generic HTTP REST calls
- websocket: WebSocket client
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import subprocess
from typing import Any

import httpx

from models import AgentNode, AgentRequest, AgentResponse, AgentCommunicationBackend

log = logging.getLogger("api.agent")

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_BACKEND_EXECUTORS: dict[AgentCommunicationBackend, Any] = {}


def register_backend(
    backend: AgentCommunicationBackend,
    executor: Any,
) -> None:
    _BACKEND_EXECUTORS[backend] = executor


# ---------------------------------------------------------------------------
# MCP backend
# ---------------------------------------------------------------------------

async def _mcp_execute(node: AgentNode, request: AgentRequest) -> AgentResponse:
    """Execute agent via MCP server.

    backend_config keys:
        - server_url: SSE endpoint URL (or stdio command if absent)
        - stdio_command: list[str] command to spawn MCP server
        - tools: list of tool names to expose
    """
    cfg = node.backend_config
    server_url = cfg.get("server_url")
    stdio_cmd = cfg.get("stdio_command")

    trace: list[str] = [f"mcp backend for role={node.role!r}"]
    output: dict[str, Any] = {}

    if server_url:
        trace.append(f"connect SSE {server_url}")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "role": node.role,
                    "goal": node.goal,
                    "tools": node.tools,
                    "context": request.context,
                }
                resp = await client.post(
                    f"{server_url.rstrip('/')}/invoke",
                    json=payload,
                )
                resp.raise_for_status()
                body = resp.json()
                output = body.get("output", body)
                trace.append("mcp_sse_ok")
        except Exception as exc:
            trace.append(f"mcp_sse_err: {exc}")
            return AgentResponse(ok=False, output=output, reasoning_trace=trace, meta={"error": str(exc)})
    elif stdio_cmd:
        trace.append(f"spawn stdio: {stdio_cmd}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *stdio_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            msg = json.dumps(
                {
                    "role": node.role,
                    "goal": node.goal,
                    "tools": node.tools,
                    "context": request.context,
                }
            ).encode()
            stdout, stderr = await asyncio.wait_for(proc.communicate(msg), timeout=60.0)
            if stderr:
                trace.append(f"stderr: {stderr.decode()[:500]}")
            try:
                output = json.loads(stdout.decode())
            except json.JSONDecodeError:
                output = {"raw_stdout": stdout.decode()}
            trace.append("mcp_stdio_ok")
        except Exception as exc:
            trace.append(f"mcp_stdio_err: {exc}")
            return AgentResponse(ok=False, output=output, reasoning_trace=trace, meta={"error": str(exc)})
    else:
        return AgentResponse(
            ok=False,
            output={},
            reasoning_trace=["mcp missing server_url or stdio_command"],
        )

    return AgentResponse(ok=True, output=output, reasoning_trace=trace)


register_backend(AgentCommunicationBackend.MCP, _mcp_execute)


# ---------------------------------------------------------------------------
# LiteLLM backend
# ---------------------------------------------------------------------------

async def _litellm_execute(node: AgentNode, request: AgentRequest) -> AgentResponse:
    """Execute agent via LiteLLM proxy.

    backend_config keys:
        - model: LiteLLM model string (e.g. "gpt-4", "openrouter/qwen/...")
        - api_base: LiteLLM proxy base URL (optional)
        - api_key: API key (falls back to LITELLM_API_KEY env)
        - temperature: float (default 0.7)
        - max_tokens: int (default 1024)
    """
    cfg = node.backend_config
    model = cfg.get("model", "gpt-4")
    api_base = cfg.get("api_base", os.environ.get("LITELLM_API_BASE", "http://localhost:4000"))
    api_key = cfg.get("api_key", os.environ.get("LITELLM_API_KEY", ""))
    temperature = cfg.get("temperature", 0.7)
    max_tokens = cfg.get("max_tokens", 1024)

    trace: list[str] = [f"litellm backend model={model!r} role={node.role!r}"]

    messages = [
        {"role": "system", "content": f"You are a {node.role}. Goal: {node.goal}. Available tools: {node.tools}"},
        {"role": "user", "content": json.dumps(request.context, ensure_ascii=False)},
    ]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{api_base.rstrip('/')}/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            body = resp.json()
            choice = body.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            trace.append("litellm_ok")
            output = {
                "content": content,
                "finish_reason": choice.get("finish_reason"),
                "usage": body.get("usage"),
            }
    except Exception as exc:
        trace.append(f"litellm_err: {exc}")
        return AgentResponse(ok=False, output={}, reasoning_trace=trace, meta={"error": str(exc)})

    return AgentResponse(ok=True, output=output, reasoning_trace=trace)


register_backend(AgentCommunicationBackend.LITELLM, _litellm_execute)


# ---------------------------------------------------------------------------
# Bash CLI backend
# ---------------------------------------------------------------------------

async def _bash_cli_execute(node: AgentNode, request: AgentRequest) -> AgentResponse:
    """Execute agent via shell / CLI.

    backend_config keys:
        - shell: shell path (default /bin/bash)
        - timeout: seconds (default 30)
        - working_dir: cwd for command
        - command_template: script template string; {context_json} and {goal} are substituted.
        Or you can pass the command directly in request.context["command"].
    """
    cfg = node.backend_config
    shell = cfg.get("shell", "/bin/bash")
    timeout = cfg.get("timeout", 30)
    working_dir = cfg.get("working_dir")

    command_template = cfg.get("command_template")
    if command_template:
        command = command_template.replace("{context_json}", shlex.quote(json.dumps(request.context))).replace("{goal}", shlex.quote(node.goal))
    else:
        command = request.context.get("command", "echo 'no command provided'")

    trace: list[str] = [f"bash_cli backend role={node.role!r} shell={shell!r}"]

    try:
        proc = await asyncio.create_subprocess_exec(
            shell, "-c", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=float(timeout))
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        trace.append(f"exit_code={proc.returncode}")
        if stderr_text:
            trace.append(f"stderr: {stderr_text[:500]}")
        output = {
            "stdout": stdout_text,
            "stderr": stderr_text,
            "exit_code": proc.returncode,
            "command": command,
        }
        ok = proc.returncode == 0
    except asyncio.TimeoutError:
        trace.append("bash_cli_timeout")
        output = {"error": "timeout", "command": command}
        ok = False
    except Exception as exc:
        trace.append(f"bash_cli_err: {exc}")
        output = {"error": str(exc), "command": command}
        ok = False

    return AgentResponse(ok=ok, output=output, reasoning_trace=trace)


register_backend(AgentCommunicationBackend.BASH_CLI, _bash_cli_execute)


# ---------------------------------------------------------------------------
# HTTP API backend
# ---------------------------------------------------------------------------

async def _http_api_execute(node: AgentNode, request: AgentRequest) -> AgentResponse:
    """Execute agent via generic HTTP REST API.

    backend_config keys:
        - url: endpoint URL
        - method: HTTP method (default POST)
        - headers: dict
        - timeout: seconds (default 30)
    """
    cfg = node.backend_config
    url = cfg.get("url")
    method = cfg.get("method", "POST")
    headers = cfg.get("headers", {"Content-Type": "application/json"})
    timeout = cfg.get("timeout", 30)

    trace: list[str] = [f"http_api backend role={node.role!r} {method} {url}"]

    if not url:
        return AgentResponse(ok=False, output={}, reasoning_trace=[*trace, "missing url in backend_config"])

    payload = {
        "role": node.role,
        "goal": node.goal,
        "tools": node.tools,
        "context": request.context,
    }

    try:
        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            resp = await client.request(method.upper(), url, headers=headers, json=payload)
            resp.raise_for_status()
            try:
                output = resp.json()
            except json.JSONDecodeError:
                output = {"raw_response": resp.text}
            trace.append("http_api_ok")
    except Exception as exc:
        trace.append(f"http_api_err: {exc}")
        return AgentResponse(ok=False, output={}, reasoning_trace=trace, meta={"error": str(exc)})

    return AgentResponse(ok=True, output=output, reasoning_trace=trace)


register_backend(AgentCommunicationBackend.HTTP_API, _http_api_execute)


# ---------------------------------------------------------------------------
# WebSocket backend
# ---------------------------------------------------------------------------

async def _websocket_execute(node: AgentNode, request: AgentRequest) -> AgentResponse:
    """Execute agent via WebSocket (sends JSON, waits for first text message).

    backend_config keys:
        - uri: WebSocket URI (ws://... / wss://...)
        - subprotocol: optional subprotocol string
        - timeout: seconds to wait for response (default 30)
    """
    cfg = node.backend_config
    uri = cfg.get("uri")
    subprotocol = cfg.get("subprotocol")
    timeout = float(cfg.get("timeout", 30))

    trace: list[str] = [f"websocket backend role={node.role!r} uri={uri}"]

    if not uri:
        return AgentResponse(ok=False, output={}, reasoning_trace=[*trace, "missing uri in backend_config"])

    try:
        import websockets
    except ImportError as exc:
        trace.append(f"websockets not installed: {exc}")
        return AgentResponse(ok=False, output={}, reasoning_trace=trace, meta={"error": "websockets package required"})

    payload = json.dumps({
        "role": node.role,
        "goal": node.goal,
        "tools": node.tools,
        "context": request.context,
    })

    try:
        kwargs = {"subprotocols": [subprotocol]} if subprotocol else {}
        async with websockets.connect(uri, **kwargs) as ws:
            await ws.send(payload)
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            try:
                output = json.loads(raw)
            except json.JSONDecodeError:
                output = {"raw_message": raw}
            trace.append("websocket_ok")
    except Exception as exc:
        trace.append(f"websocket_err: {exc}")
        return AgentResponse(ok=False, output={}, reasoning_trace=trace, meta={"error": str(exc)})

    return AgentResponse(ok=True, output=output, reasoning_trace=trace)


register_backend(AgentCommunicationBackend.WEBSOCKET, _websocket_execute)


# ---------------------------------------------------------------------------
# Public executor
# ---------------------------------------------------------------------------

async def execute_agent(request: AgentRequest) -> AgentResponse:
    """Dispatch to the registered backend executor."""
    node = request.agent_node
    backend = node.backend

    executor = _BACKEND_EXECUTORS.get(backend)
    if not executor:
        return AgentResponse(
            ok=False,
            output={},
            reasoning_trace=[f"unsupported backend: {backend}"],
            meta={"error": f"No executor registered for {backend}"},
        )

    return await executor(node, request)

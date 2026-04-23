#!/usr/bin/env python3
"""Full test suite: all agent backends + pipeline with agent."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

_SUMMARY_SERVER = str(Path(__file__).resolve().parent.parent / "mcp_servers" / "summary_server.py")

sys.path.insert(0, ".")

from models import AgentNode, AgentRequest, AgentCommunicationBackend
from agent import execute_agent


@pytest.mark.asyncio
async def test_mcp() -> None:
    print("\n=== TEST 1: MCP stdio ===")
    node = AgentNode(
        id="test-mcp",
        role="summarizer",
        goal="Summarize text",
        tools=["summarize"],
        backend=AgentCommunicationBackend.MCP,
        backend_config={"stdio_command": ["python3", _SUMMARY_SERVER]},
    )
    req = AgentRequest(agent_node=node, context={"text": "Quantum computing is revolutionizing cryptography."})
    resp = await execute_agent(req)
    assert resp.ok, f"MCP failed: {resp.reasoning_trace}"
    print("PASS — output:", resp.output["tool_result"]["content"][0]["text"])


@pytest.mark.asyncio
async def test_bash() -> None:
    print("\n=== TEST 2: Bash CLI ===")
    node = AgentNode(
        id="test-bash",
        role="runner",
        goal="run echo",
        backend=AgentCommunicationBackend.BASH_CLI,
        backend_config={"command_template": "echo hello_from_bash"},
    )
    req = AgentRequest(agent_node=node, context={})
    resp = await execute_agent(req)
    assert resp.ok, f"Bash failed: {resp.reasoning_trace}"
    assert "hello_from_bash" in resp.output["stdout"], resp.output
    print("PASS — stdout:", resp.output["stdout"].strip())


@pytest.mark.asyncio
async def test_litellm_mock() -> None:
    print("\n=== TEST 3: LiteLLM (mock server) ===")
    # Start a tiny mock litellm server
    import http.server
    import socketserver
    import threading

    class MockHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            body = json.dumps({
                "choices": [{"message": {"content": "mock_llm_reply"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            })
            self.wfile.write(body.encode())

        def log_message(self, fmt, *args):
            pass

    port = 9876
    srv = socketserver.TCPServer(("", port), MockHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()

    try:
        node = AgentNode(
            id="test-llm",
            role="writer",
            goal="write poem",
            backend=AgentCommunicationBackend.LITELLM,
            backend_config={"api_base": f"http://localhost:{port}", "model": "mock-model"},
        )
        req = AgentRequest(agent_node=node, context={"topic": "stars"})
        resp = await execute_agent(req)
        assert resp.ok, f"LiteLLM failed: {resp.reasoning_trace}"
        assert "mock_llm_reply" == resp.output["content"], resp.output
        print("PASS — content:", resp.output["content"])
    finally:
        srv.shutdown()


@pytest.mark.asyncio
async def test_pipeline_with_agent() -> None:
    print("\n=== TEST 4: Pipeline with agent step ===")
    from commands.pipeline import PipelineCommand
    from models import CommandRequest

    cmd = PipelineCommand()
    request = CommandRequest(meta={
        "steps": [
            {"command": "fetch", "request": {"input_uri": "data:text/plain;base64,cXVhbnR1bSBjb21wdXRpbmc="}},
            {
                "command": "agent",
                "request": {"meta": {"input": "$previous.output"}},
                "agent_node": {
                    "id": "pipe-agent",
                    "role": "summarizer",
                    "goal": "Summarize base64-decoded text",
                    "tools": ["summarize"],
                    "backend": "mcp",
                    "backend_config": {
                        "stdio_command": ["python3", _SUMMARY_SERVER],
                    },
                },
            },
        ]
    })
    resp = await cmd.execute(request)
    assert resp.ok
    trace = resp.meta.get("pipeline_trace", [])
    assert len(trace) == 2
    agent_meta = trace[1]["meta"]
    assert agent_meta.get("agent_ok") is True
    print("PASS — pipeline trace:", [t["command"] for t in trace])
    print("Agent output keys:", list(agent_meta.get("agent_trace", [])))


async def main() -> None:
    await test_mcp()
    await test_bash()
    await test_litellm_mock()
    await test_pipeline_with_agent()
    print("\n=== ALL 4 TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())

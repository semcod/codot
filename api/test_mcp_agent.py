#!/usr/bin/env python3
"""Integration test: Agent MCP backend talking to a local stdio MCP server."""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")

from models import AgentNode, AgentRequest, AgentCommunicationBackend
from agent import execute_agent


async def main() -> None:
    node = AgentNode(
        id="test-mcp",
        role="summarizer",
        goal="Summarize provided text",
        tools=["summarize"],
        backend=AgentCommunicationBackend.MCP,
        backend_config={
            "stdio_command": ["python3", "../mcp_servers/summary_server.py"],
        },
    )
    req = AgentRequest(
        agent_node=node,
        context={"text": "This is a long article about quantum computing and its applications in cryptography and drug discovery."},
    )
    print("=== Calling MCP agent ===")
    resp = await execute_agent(req)
    print("ok:", resp.ok)
    print("output:", resp.output)
    print("trace:", resp.reasoning_trace)
    if not resp.ok:
        print("meta error:", resp.meta.get("error"))
        sys.exit(1)
    print("\n=== SUCCESS ===")


if __name__ == "__main__":
    asyncio.run(main())

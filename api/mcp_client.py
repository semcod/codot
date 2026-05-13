"""Lightweight MCP (Model Context Protocol) client.

Supports stdio and SSE transports per the MCP spec:
https://modelcontextprotocol.io/

JSON-RPC 2.0 over stdio or Server-Sent Events.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Any

import httpx

log = logging.getLogger("api.mcp")


class MCPError(Exception):
    pass


class MCPClient:
    """Base MCP client (transport-agnostic)."""

    def __init__(self) -> None:
        self._req_id = 0

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def initialize(
        self, client_name: str = "codot", version: str = "2024-11-05"
    ) -> dict[str, Any]:
        result = await self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"sampling": {}, "roots": {"listChanged": True}},
                    "clientInfo": {"name": client_name, "version": version},
                },
            }
        )
        await self._send(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
        )
        return result

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list",
                "params": {},
            }
        )
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        return result

    async def close(self) -> None:
        pass


class MCPStdioClient(MCPClient):
    """Spawn an MCP server as a subprocess and speak JSON-RPC over stdio."""

    def __init__(self, command: list[str], env: dict[str, str] | None = None) -> None:
        super().__init__()
        self.command = command
        self.env = {**os.environ, **(env or {})}
        self._proc: asyncio.subprocess.Process | None = None
        self._read_buffer = ""

    async def _read_message(self) -> dict[str, Any] | None:
        assert self._proc is not None and self._proc.stdout is not None
        while True:
            line = await self._proc.stdout.readline()
            if not line:
                return None
            text = line.decode("utf-8", errors="replace").strip()
            if not text:
                continue
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                log.warning("mcp_stdio_parse_error: %s", text[:200])
                continue

    async def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._proc is None:
            self._proc = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env,
            )
        assert self._proc.stdin is not None
        raw = json.dumps(payload, ensure_ascii=False) + "\n"
        self._proc.stdin.write(raw.encode())
        await self._proc.stdin.drain()

        if "id" in payload:
            resp = await asyncio.wait_for(self._read_message(), timeout=60.0)
            if resp is None:
                raise MCPError("mcp_stdio_eof")
            if "error" in resp:
                raise MCPError(f"mcp_error: {resp['error']}")
            return resp.get("result", {})
        return {}

    async def close(self) -> None:
        if self._proc is not None:
            try:
                if self._proc.stdin and not self._proc.stdin.is_closing():
                    self._proc.stdin.write(
                        b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
                    )
                    await self._proc.stdin.drain()
            except (RuntimeError, BrokenPipeError):
                pass
            try:
                if self._proc.returncode is None:
                    self._proc.kill()
                    await self._proc.wait()
            except ProcessLookupError:
                pass
            self._proc = None


class MCPSseClient(MCPClient):
    """Connect to an MCP server via HTTP SSE transport."""

    def __init__(self, base_url: str, headers: dict[str, str] | None = None) -> None:
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self._session_id: str | None = None
        self._client: httpx.AsyncClient | None = None

    async def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0, headers=self.headers)
        sess = self._session_id or str(uuid.uuid4())
        if self._session_id is None:
            self._session_id = sess
        url = f"{self.base_url}/messages?session_id={sess}"
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    async def initialize(
        self, client_name: str = "codot", version: str = "0.1.0"
    ) -> dict[str, Any]:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0, headers=self.headers)
        result = await super().initialize(client_name, version)
        return result

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

#!/usr/bin/env python3
"""A minimal MCP server (stdio transport) for testing.

Implements JSON-RPC 2.0 over stdio per the MCP spec:
https://modelcontextprotocol.io/

Tools:
    - summarize: takes {"text": str} returns {"summary": str}
"""
from __future__ import annotations

import json
import sys


def _send(msg: dict) -> None:
    raw = json.dumps(msg, ensure_ascii=False)
    sys.stdout.write(raw + "\n")
    sys.stdout.flush()


def _handle(req: dict) -> dict | None:
    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "summary-server", "version": "0.1.0"},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "summarize",
                        "description": "Summarize a text into 1-2 sentences",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                    }
                ]
            },
        }

    if method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        if name == "summarize":
            text = args.get("text", "")
            summary = f"Summary: {text[:50]}..." if len(text) > 50 else f"Summary: {text}"
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": summary}
                    ]
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown tool: {name}"},
        }

    if req_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }
    return None


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            _send({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
            })
            continue
        resp = _handle(req)
        if resp is not None:
            _send(resp)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Simple CLI to run CQRS workflows from shell.

Usage:
    python codot_run.py workflow.json
    python codot_run.py --agent agent.json
    python codot_run.py --url http://localhost:18080 workflow.json
"""
from __future__ import annotations

import argparse
import base64
import json
import sys

import httpx


DEFAULT_URL = "http://localhost:18080"
DEFAULT_USER = "admin"
DEFAULT_PASS = "admin"


def _get_token(base: str, username: str, password: str) -> str:
    r = httpx.post(f"{base}/auth/token", json={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def run_pipeline(base: str, token: str, workflow_path: str) -> dict:
    with open(workflow_path) as f:
        wf = json.load(f)

    # Convert DAG JSON to PipelineRequest (steps with $previous.output wiring)
    nodes = wf.get("nodes", [])
    steps = []
    for i, node in enumerate(nodes):
        req = {}
        if node.get("input"):
            if i == 0:
                req["input_uri"] = node.get("uri", "")
            else:
                req["meta"] = {"input": "$previous.output"}
        elif node.get("uri"):
            req["input_uri"] = node.get("uri")

        if node.get("type") == "agent":
            steps.append({
                "command": "agent",
                "request": req,
                "agent_node": {
                    "id": node["id"],
                    "role": node.get("role", "agent"),
                    "goal": node.get("goal", ""),
                    "tools": node.get("tools", []),
                    "backend": node.get("backend", "mcp"),
                    "backend_config": node.get("backend_config", {}),
                }
            })
        else:
            req["meta"] = req.get("meta", {})
            if node.get("command_type"):
                req["meta"]["command_type"] = node["command_type"]
            if node.get("schema_uri"):
                req["schema_uri"] = node["schema_uri"]
            steps.append({
                "command": node.get("type", "fetch"),
                "request": req,
            })

    payload = {"meta": {"steps": steps}}
    r = httpx.put(
        f"{base}/commands/pipeline",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
    )
    r.raise_for_status()
    return r.json()


def run_agent(base: str, token: str, agent_path: str) -> dict:
    with open(agent_path) as f:
        node = json.load(f)
    r = httpx.post(
        f"{base}/agents/{node.get('id', 'cli')}/run",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "agent_node": node,
            "context": node.get("context", {}),
        },
    )
    r.raise_for_status()
    return r.json()


def _print_agent_result(result: dict) -> None:
    print("=== AGENT OUTPUT ===")
    print(json.dumps(result.get("output", {}), indent=2, ensure_ascii=False))
    trace = result.get("reasoning_trace", [])
    if trace:
        print("\n=== TRACE ===")
        for line in trace:
            print(f"  {line}")


def _print_pipeline_result(result: dict) -> None:
    meta = result.get("meta", {})
    trace = meta.get("pipeline_trace", [])
    for t in trace:
        print(f"  step {t['step']}: {t['command']} → mime={t.get('mime')}")
    if "payload_b64" in result:
        try:
            decoded = base64.b64decode(result["payload_b64"]).decode("utf-8")
            print("\n=== OUTPUT ===")
            print(decoded)
        except Exception:
            print("\n=== OUTPUT (base64) ===")
            print(result["payload_b64"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CQRS workflows / agents from CLI")
    parser.add_argument("file", help="JSON workflow or agent definition")
    parser.add_argument("--url", default=DEFAULT_URL, help="API base URL")
    parser.add_argument("--user", default=DEFAULT_USER, help="Username")
    parser.add_argument("--password", default=DEFAULT_PASS, help="Password")
    parser.add_argument("--agent", action="store_true", help="Run as agent instead of pipeline")
    parser.add_argument("--raw", action="store_true", help="Print raw JSON")
    args = parser.parse_args()

    token = _get_token(args.url, args.user, args.password)

    if args.agent:
        result = run_agent(args.url, token, args.file)
    else:
        result = run_pipeline(args.url, token, args.file)

    if args.raw:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if not result.get("ok"):
        print("FAILED:", result.get("error", result))
        return 1

    if args.agent:
        _print_agent_result(result)
    else:
        _print_pipeline_result(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())

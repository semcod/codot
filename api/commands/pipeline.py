"""Pipeline command - compose other commands with reference substitution.

Each step may reference the previous step's result via the special URI
"$previous.output" which is expanded at runtime to a data:<mime>;base64,<...>
URI containing the previous command's payload. This is exactly the DSL sketched
in the design doc and makes command composition protocol-agnostic.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from models import AgentRequest, CommandRequest, CommandResponse
from . import Command, get_registry as get_command_registry


def _to_data_uri(resp: CommandResponse) -> str:
    mime = resp.mime or "application/octet-stream"
    return f"data:{mime};base64,{resp.payload_b64 or ''}"


def _substitute(value: Any, previous: CommandResponse | None) -> Any:
    if previous is None:
        return value
    if isinstance(value, str) and value == "$previous.output":
        return _to_data_uri(previous)
    if isinstance(value, dict):
        return {k: _substitute(v, previous) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, previous) for v in value]
    return value


async def _run_agent_step(agent_node_raw: dict, req: CommandRequest) -> CommandResponse:
    from models import AgentNode
    from agent import execute_agent

    agent_node = AgentNode(**agent_node_raw)
    agent_ctx = dict(req.meta)
    text = _extract_text_from_data_uri(agent_ctx.get("input", ""))
    if text is not None:
        agent_ctx["text"] = text
    agent_req = AgentRequest(agent_node=agent_node, context=agent_ctx)
    agent_resp = await execute_agent(agent_req)
    payload_b64 = base64.b64encode(json.dumps(agent_resp.output).encode()).decode()
    return CommandResponse(
        payload_b64=payload_b64,
        mime="application/json",
        meta={
            "agent_trace": agent_resp.reasoning_trace,
            "agent_meta": agent_resp.meta,
            "agent_ok": agent_resp.ok,
        },
    )


def _extract_text_from_data_uri(data_uri: str) -> str | None:
    if not data_uri.startswith("data:"):
        return None
    try:
        after_colon = data_uri.split(":", 1)[1]
        if ";" in after_colon:
            mime_b64 = after_colon.split(";", 1)
            b64_part = mime_b64[1].split(",", 1)[1]
        else:
            b64_part = after_colon.split(",", 1)[1]
        return base64.b64decode(b64_part).decode("utf-8", errors="replace")
    except Exception:
        return None


class PipelineCommand(Command):
    name = "pipeline"
    description = (
        "Execute a sequence of commands. Any field in a step's request that "
        "equals '$previous.output' is replaced with a data: URI pointing at "
        "the prior step's output."
    )
    input_hint = {
        "meta.steps": "[{command: <name>, request: {<CommandRequest>}}, ...]",
    }

    async def execute(self, request: CommandRequest) -> CommandResponse:
        steps = (request.meta or {}).get("steps") or []
        if not steps:
            raise ValueError("pipeline requires meta.steps (non-empty list)")

        reg = get_command_registry()
        previous: CommandResponse | None = None
        trace: list[dict[str, Any]] = []

        for idx, step in enumerate(steps):
            cmd_name = step.get("command")
            if not cmd_name:
                raise ValueError(f"Step {idx} missing 'command'")
            raw_req = step.get("request") or {}
            substituted = _substitute(raw_req, previous)
            req = CommandRequest(**substituted)

            agent_node_raw = step.get("agent_node")
            if agent_node_raw is not None:
                resp = await _run_agent_step(agent_node_raw, req)
            else:
                command = reg.get(cmd_name)
                resp = await command.execute(req)

            previous = resp
            trace.append(
                {
                    "step": idx,
                    "command": cmd_name,
                    "mime": resp.mime,
                    "meta": resp.meta,
                }
            )

        assert previous is not None
        return CommandResponse(
            payload_b64=previous.payload_b64,
            mime=previous.mime,
            meta={"pipeline_trace": trace, "final_meta": previous.meta},
        )

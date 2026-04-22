"""Thin envelope models. We intentionally DO NOT model domain DTOs here -
Commands/Queries operate on arbitrary bytes + meta (Struct-like dicts),
matching the 'URL-addressable resources' pattern described in the design docs.
"""
from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class CommandRequest(BaseModel):
    """Envelope for every command invocation.

    - input_uri: URI of the resource the command should act upon (http://, https://,
      file://, data:base64,... - resolved via protocol registry).
    - schema_uri: optional URI pointing to a JSON Schema the meta/payload must match.
    - meta: free-form structured parameters (like google.protobuf.Struct).
    - payload_b64: optional inline payload (base64) when the caller doesn't want
      to host the data at a URL.
    """

    input_uri: str | None = Field(default=None, description="Source resource URI")
    schema_uri: str | None = Field(default=None, description="JSON Schema URI for validation")
    output_mime: str | None = Field(default=None)
    meta: dict[str, Any] = Field(default_factory=dict)
    payload_b64: str | None = Field(default=None)


class CommandResponse(BaseModel):
    ok: bool = True
    payload_b64: str | None = None
    mime: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    source_uris: list[str] = Field(default_factory=list)
    schema_uri: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    ok: bool = True
    data: Any = None
    meta: dict[str, Any] = Field(default_factory=dict)


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    role: str


class PipelineStep(BaseModel):
    command: str
    request: CommandRequest


class PipelineRequest(BaseModel):
    steps: list[PipelineStep]


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
    details: dict[str, Any] = Field(default_factory=dict)


# ---------- Agent formula -----------------------------------------------------

class AgentCommunicationBackend(str, Enum):
    """Supported communication backends for Agent formula."""
    MCP = "mcp"
    LITELLM = "litellm"
    BASH_CLI = "bash_cli"
    HTTP_API = "http_api"
    WEBSOCKET = "websocket"


class AgentNode(BaseModel):
    """Agent node definition for DAG / orchestration.

    An Agent node replaces the traditional command executor with an autonomous
    worker that may use memory, reasoning traces, and delegated tools.
    """
    id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    role: str
    goal: str
    tools: list[str] = Field(default_factory=list)
    backend: AgentCommunicationBackend = AgentCommunicationBackend.MCP
    backend_config: dict[str, Any] = Field(default_factory=dict)
    memory_uri: str | None = None
    input: str | None = None
    inputs: list[str] = Field(default_factory=list)
    description: str | None = None


class AgentRequest(BaseModel):
    """Request to execute an Agent node.

    - backend_config: backend-specific settings, e.g.:
        mcp:        {"server_url": "...", "tools": [...]}
        litellm:    {"model": "gpt-4", "api_base": "...", "api_key": "..."}
        bash_cli:   {"shell": "/bin/bash", "timeout": 30}
        http_api:   {"url": "...", "method": "POST", "headers": {...}}
        websocket:  {"uri": "ws://...", "subprotocol": "..."}
    """
    agent_node: AgentNode
    context: dict[str, Any] = Field(default_factory=dict)
    shared_state_uri: str | None = None


class AgentResponse(BaseModel):
    ok: bool = True
    output: dict[str, Any] = Field(default_factory=dict)
    reasoning_trace: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)

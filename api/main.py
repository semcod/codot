"""FastAPI entry point.

Every command becomes `PUT /commands/{name}`.
Every query becomes `POST /queries/{name}` (GET form also accepted for simple cases).

Commands and Queries are URL-addressable resources exactly as described in
the design docs - the URL is the identifier of the action, the body carries
input_uri / schema_uri / meta. No DTOs per command.
"""
from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, Query as FQuery, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from models import (
    AgentNode,
    AgentRequest,
    AgentResponse,
    CommandRequest,
    CommandResponse,
    ErrorResponse,
    PipelineRequest,
    QueryRequest,
    QueryResponse,
    TokenRequest,
    TokenResponse,
)
from auth import authenticate, current_user, get_jwt_manager
from policy import get_engine, User
from commands import get_registry as cmd_registry
from queries import get_registry as qry_registry
from agent import execute_agent

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("api")

app = FastAPI(
    title="CQRS-URL Platform",
    description=(
        "Commands and Queries as URL-addressable resources. "
        "Operates on arbitrary resources over pluggable protocols (http, file, data, ...) "
        "with runtime JSON-Schema validation and policy-based access control."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Error mapping -----------------------------------------------------

@app.exception_handler(ValueError)
async def _value_error(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content=ErrorResponse(error=str(exc)).model_dump())


@app.exception_handler(PermissionError)
async def _perm_error(_: Request, exc: PermissionError) -> JSONResponse:
    return JSONResponse(status_code=403, content=ErrorResponse(error=str(exc)).model_dump())


@app.exception_handler(FileNotFoundError)
async def _nf_error(_: Request, exc: FileNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content=ErrorResponse(error=str(exc)).model_dump())


@app.exception_handler(KeyError)
async def _key_error(_: Request, exc: KeyError) -> JSONResponse:
    return JSONResponse(status_code=404, content=ErrorResponse(error=str(exc)).model_dump())


# ---------- Health & auth -----------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "cqrs-url-platform", "version": "0.1.0"}


@app.post("/auth/token", response_model=TokenResponse)
async def issue_token(req: TokenRequest) -> TokenResponse:
    record = authenticate(req.username, req.password)
    if not record:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token, expires = get_jwt_manager().issue(
        sub=record["sub"], username=req.username, role=record["role"]
    )
    return TokenResponse(access_token=token, expires_in=expires, role=record["role"])


@app.get("/auth/me")
async def me(user: User = Depends(current_user)) -> dict:
    return {"sub": user.sub, "username": user.username, "role": user.role}


# ---------- Commands ----------------------------------------------------------

@app.get("/commands")
async def list_commands(user: User = Depends(current_user)) -> dict:
    return {"commands": cmd_registry().list()}


@app.put("/commands/{name}", response_model=CommandResponse)
async def execute_command(
    name: str,
    body: CommandRequest,
    user: User = Depends(current_user),
) -> CommandResponse:
    # 1. Policy check
    decision = get_engine().can_execute_command(
        user=user,
        command_type=name,
        input_uri=body.input_uri,
        schema_uri=body.schema_uri,
    )
    if not decision.allowed:
        log.info("DENY command=%s user=%s reason=%s", name, user.username, decision.reason)
        raise HTTPException(status_code=403, detail=decision.reason)

    # 2. Dispatch
    try:
        command = cmd_registry().get(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown command: {name}")

    log.info("EXEC command=%s user=%s uri=%s", name, user.username, body.input_uri)
    return await command.execute(body)


# ---------- Queries -----------------------------------------------------------

@app.get("/queries")
async def list_queries(user: User = Depends(current_user)) -> dict:
    return {"queries": qry_registry().list()}


@app.post("/queries/{name}", response_model=QueryResponse)
async def execute_query(
    name: str,
    body: QueryRequest,
    user: User = Depends(current_user),
) -> QueryResponse:
    decision = get_engine().can_execute_query(
        user=user,
        query_type=name,
        source_uris=body.source_uris,
        schema_uri=body.schema_uri,
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    try:
        query = qry_registry().get(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown query: {name}")
    return await query.execute(body)


@app.get("/queries/{name}", response_model=QueryResponse)
async def execute_query_get(
    name: str,
    source_uris: list[str] = FQuery(default_factory=list),
    user: User = Depends(current_user),
) -> QueryResponse:
    """Convenience GET form: /queries/from-url?source_uris=...&source_uris=..."""
    body = QueryRequest(source_uris=source_uris)
    return await execute_query(name, body, user)


# ---------- Introspection (no auth - catalog is public) -----------------------

@app.get("/catalog")
async def catalog() -> dict:
    """Public catalog, handy for the frontend to render the command list."""
    from protocols import get_registry as proto_reg
    from models import AgentCommunicationBackend
    return {
        "commands": cmd_registry().list(),
        "queries": qry_registry().list(),
        "protocols": proto_reg().supported(),
        "agent_backends": [b.value for b in AgentCommunicationBackend],
    }


# ---------- Agents ------------------------------------------------------------

@app.post("/agents/{agent_id}/run", response_model=AgentResponse)
async def run_agent(
    agent_id: str,
    body: AgentRequest,
    user: User = Depends(current_user),
) -> AgentResponse:
    decision = get_engine().can_execute_command(
        user=user,
        command_type="agent_run",
        input_uri=body.shared_state_uri,
        schema_uri=None,
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    log.info("AGENT role=%s backend=%s user=%s", body.agent_node.role, body.agent_node.backend.value, user.username)
    return await execute_agent(body)


@app.get("/agents/backends")
async def list_agent_backends() -> dict:
    from models import AgentCommunicationBackend
    return {
        "backends": [
            {
                "name": b.value,
                "description": {
                    AgentCommunicationBackend.MCP: "Model Context Protocol (stdio or SSE)",
                    AgentCommunicationBackend.LITELLM: "LiteLLM unified LLM API gateway",
                    AgentCommunicationBackend.BASH_CLI: "Shell / CLI command execution",
                    AgentCommunicationBackend.HTTP_API: "Generic HTTP REST API call",
                    AgentCommunicationBackend.WEBSOCKET: "WebSocket client connection",
                }.get(b, ""),
            }
            for b in AgentCommunicationBackend
        ]
    }

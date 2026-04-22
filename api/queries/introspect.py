from __future__ import annotations

from models import QueryRequest, QueryResponse
from commands import get_registry as command_registry
from protocols import get_registry as protocol_registry
from . import Query, get_registry as query_registry


class IntrospectQuery(Query):
    name = "introspect"
    description = "List commands, queries and protocols exposed by this service."
    input_hint = {}

    async def execute(self, request: QueryRequest) -> QueryResponse:
        return QueryResponse(
            data={
                "commands": command_registry().list(),
                "queries": query_registry().list(),
                "protocols": protocol_registry().supported(),
            },
            meta={"version": "0.1.0"},
        )

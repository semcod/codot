"""Query registry. Same idea as commands, but for reads."""

from __future__ import annotations

import abc
from typing import Any

from models import QueryRequest, QueryResponse


class Query(abc.ABC):
    name: str = ""
    description: str = ""
    input_hint: dict[str, Any] = {}

    @abc.abstractmethod
    async def execute(self, request: QueryRequest) -> QueryResponse: ...


class QueryRegistry:
    def __init__(self) -> None:
        self._queries: dict[str, Query] = {}

    def register(self, query: Query) -> None:
        if not query.name:
            raise ValueError("Query must have a name")
        self._queries[query.name] = query

    def get(self, name: str) -> Query:
        if name not in self._queries:
            raise KeyError(f"Unknown query: {name}")
        return self._queries[name]

    def list(self) -> list[dict[str, Any]]:
        return [
            {"name": q.name, "description": q.description, "input_hint": q.input_hint}
            for q in self._queries.values()
        ]


_registry = QueryRegistry()


def get_registry() -> QueryRegistry:
    return _registry


def register_default_queries() -> None:
    from .from_url import FromUrlQuery
    from .introspect import IntrospectQuery

    reg = get_registry()
    reg.register(FromUrlQuery())
    reg.register(IntrospectQuery())


register_default_queries()

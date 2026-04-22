from __future__ import annotations

import base64

from models import QueryRequest, QueryResponse
from protocols import get_registry
from . import Query


class FromUrlQuery(Query):
    name = "from-url"
    description = (
        "Fetch one or more resources by URI and return them as a list. "
        "Binary content is base64-encoded; text content is returned as a string."
    )
    input_hint = {"source_uris": "list of URIs to fetch"}

    async def execute(self, request: QueryRequest) -> QueryResponse:
        if not request.source_uris:
            raise ValueError("from-url requires source_uris")

        registry = get_registry()
        parts = []
        for uri in request.source_uris:
            fetched = await registry.fetch(uri)
            mime = fetched.mime or ""
            if mime.startswith("text/") or "json" in mime or "xml" in mime or "csv" in mime:
                try:
                    body = fetched.content.decode("utf-8")
                    encoding = "utf-8"
                except UnicodeDecodeError:
                    body = base64.b64encode(fetched.content).decode("ascii")
                    encoding = "base64"
            else:
                body = base64.b64encode(fetched.content).decode("ascii")
                encoding = "base64"
            parts.append({
                "uri": uri,
                "mime": fetched.mime,
                "size": len(fetched.content),
                "encoding": encoding,
                "content": body,
                "extra": fetched.extra,
            })
        return QueryResponse(data=parts, meta={"count": len(parts)})

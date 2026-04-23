from __future__ import annotations

import base64

from models import QueryRequest, QueryResponse
from protocols import get_registry
from . import Query


def _is_text_mime(mime: str) -> bool:
    return mime.startswith("text/") or "json" in mime or "xml" in mime or "csv" in mime


def _decode_body(content: bytes, mime: str) -> tuple[str, str]:
    if not _is_text_mime(mime):
        return base64.b64encode(content).decode("ascii"), "base64"
    try:
        return content.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return base64.b64encode(content).decode("ascii"), "base64"


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
            body, encoding = _decode_body(fetched.content, fetched.mime or "")
            parts.append({
                "uri": uri,
                "mime": fetched.mime,
                "size": len(fetched.content),
                "encoding": encoding,
                "content": body,
                "extra": fetched.extra,
            })
        return QueryResponse(data=parts, meta={"count": len(parts)})

from __future__ import annotations

import base64
from urllib.parse import unquote

from . import FetchResult


class DataProtocol:
    """Implements RFC 2397 data URIs: data:[<mime>][;base64],<data>.

    Useful when callers want to pass inline payloads without hosting them
    somewhere - e.g. the frontend converting a textarea to a data URI before
    sending it to a command.
    """

    scheme = "data"

    async def fetch(self, uri: str) -> FetchResult:
        if not uri.startswith("data:"):
            raise ValueError(f"Not a data: URI: {uri}")
        header, _, data = uri[5:].partition(",")
        if not data and not header:
            raise ValueError("Empty data URI")

        meta = header.split(";") if header else []
        mime = meta[0] if meta and meta[0] and "=" not in meta[0] else "text/plain"
        is_b64 = "base64" in meta

        if is_b64:
            content = base64.b64decode(data)
        else:
            content = unquote(data).encode("utf-8")

        return FetchResult(
            content=content,
            mime=mime,
            source_uri=uri,
            extra={"inline": True, "base64": is_b64},
        )

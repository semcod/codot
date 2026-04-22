from __future__ import annotations

import httpx

from config import settings
from . import FetchResult


class HttpProtocol:
    def __init__(self, scheme: str = "http") -> None:
        self.scheme = scheme

    async def fetch(self, uri: str) -> FetchResult:
        async with httpx.AsyncClient(
            timeout=settings.fetch_timeout_seconds,
            follow_redirects=True,
        ) as client:
            resp = await client.get(uri)
            resp.raise_for_status()
            content = resp.content
            if len(content) > settings.fetch_max_bytes:
                raise ValueError(
                    f"Resource too large ({len(content)} > {settings.fetch_max_bytes})"
                )
            return FetchResult(
                content=content,
                mime=resp.headers.get("content-type", "application/octet-stream"),
                source_uri=uri,
                extra={
                    "status": resp.status_code,
                    "headers": dict(resp.headers),
                },
            )

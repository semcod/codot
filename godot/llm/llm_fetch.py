"""URI fetch helpers for bundle context gathering."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any
from urllib.parse import unquote_to_bytes, urlparse

import httpx
from fastapi import HTTPException

from llm_schemas import FetchRequest, STATE


def _read_file_bytes(uri: str, parsed) -> tuple[bytes, str]:
    path = Path(unquote_to_bytes(parsed.path).decode("utf-8", errors="ignore")).resolve()
    return path.read_bytes(), "application/octet-stream"


def _read_data_bytes(uri: str) -> tuple[bytes, str]:
    header, _, payload = uri.partition(",")
    metadata = header[5:]
    is_base64 = ";base64" in metadata
    content_type = metadata.split(";")[0] or "text/plain;charset=US-ASCII"
    data = base64.b64decode(payload) if is_base64 else unquote_to_bytes(payload)
    return data, content_type


async def _read_http_bytes(request: FetchRequest) -> tuple[bytes, str]:
    async with httpx.AsyncClient(
        timeout=STATE.settings.fetch_timeout_sec, follow_redirects=False
    ) as client:
        response = await client.request(
            request.method.upper(),
            request.uri,
            headers=request.headers,
            content=request.body.encode("utf-8") if request.body is not None else None,
        )
        response.raise_for_status()
        return response.content, response.headers.get("content-type", "application/octet-stream")


def _payload_result(uri: str, data: bytes, content_type: str) -> dict[str, Any]:
    if len(data) > STATE.settings.max_fetch_bytes:
        raise HTTPException(status_code=413, detail="payload is too large")
    result: dict[str, Any] = {
        "uri": uri,
        "content_type": content_type,
        "size": len(data),
    }
    try:
        text = data.decode("utf-8")
        result["text"] = text
        try:
            import json

            result["json"] = json.loads(text)
        except json.JSONDecodeError:
            pass
    except UnicodeDecodeError:
        result["payload_b64"] = base64.b64encode(data).decode("ascii")
    return result


async def fetch_uri(request: FetchRequest) -> dict[str, Any]:
    allowed, reason = STATE.acl.allows(request.uri)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    parsed = urlparse(request.uri)
    if parsed.scheme == "file":
        data, content_type = _read_file_bytes(request.uri, parsed)
    elif parsed.scheme == "data":
        data, content_type = _read_data_bytes(request.uri)
    else:
        data, content_type = await _read_http_bytes(request)
    return _payload_result(request.uri, data, content_type)


async def fetch_many(uris: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for uri in uris:
        try:
            items.append(
                {
                    "uri": uri,
                    "ok": True,
                    "result": await fetch_uri(FetchRequest(uri=uri)),
                }
            )
        except HTTPException as exc:
            items.append(
                {
                    "uri": uri,
                    "ok": False,
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                }
            )
    return items

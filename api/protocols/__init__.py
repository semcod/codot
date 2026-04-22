"""Pluggable protocol registry.

Every Command/Query that needs to read a resource goes through this registry.
New protocols (s3, ftp, sqlite, redis, kafka) can be added by registering a
Protocol implementation against a scheme prefix.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol as TypingProtocol
from urllib.parse import urlparse


@dataclass
class FetchResult:
    content: bytes
    mime: str | None = None
    source_uri: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class Protocol(TypingProtocol):
    scheme: str

    async def fetch(self, uri: str) -> FetchResult: ...


class ProtocolRegistry:
    def __init__(self) -> None:
        self._protocols: dict[str, Protocol] = {}

    def register(self, protocol: Protocol) -> None:
        self._protocols[protocol.scheme] = protocol

    def supported(self) -> list[str]:
        return sorted(self._protocols.keys())

    async def fetch(self, uri: str) -> FetchResult:
        scheme = urlparse(uri).scheme.lower()
        if not scheme:
            raise ValueError(f"URI has no scheme: {uri!r}")
        proto = self._protocols.get(scheme)
        if proto is None:
            raise ValueError(
                f"Unsupported protocol {scheme!r}. Available: {self.supported()}"
            )
        return await proto.fetch(uri)


_registry = ProtocolRegistry()


def get_registry() -> ProtocolRegistry:
    return _registry


def register_default_protocols() -> None:
    from .http_protocol import HttpProtocol
    from .file_protocol import FileProtocol
    from .data_protocol import DataProtocol

    reg = get_registry()
    reg.register(HttpProtocol("http"))
    reg.register(HttpProtocol("https"))
    reg.register(FileProtocol())
    reg.register(DataProtocol())


register_default_protocols()

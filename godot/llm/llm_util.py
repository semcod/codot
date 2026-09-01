"""Small helpers shared across the Godot LLM service."""
from __future__ import annotations

import ipaddress
import os
import re
from typing import Any
from urllib.parse import urlparse


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError:
        return default


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "generated-bundle"


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def compact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: compact(item)
            for key, item in value.items()
            if item not in (None, [], {}, "")
        }
    if isinstance(value, list):
        return [compact(item) for item in value if item not in (None, [], {}, "")]
    return value


def is_private_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    lowered = hostname.lower()
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return any(
        [
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_reserved,
            ip.is_multicast,
            ip.is_unspecified,
        ]
    )


def source_name_from_uri(uri: str, index: int) -> str:
    parsed = urlparse(uri)
    candidate = parsed.hostname or parsed.path.strip("/") or f"source-{index + 1}"
    candidate = candidate.replace(":", "-").replace("/", "-")
    candidate = re.sub(r"[^a-zA-Z0-9_-]+", "-", candidate).strip("-")
    return candidate or f"source-{index + 1}"

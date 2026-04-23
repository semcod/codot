"""Helpers shared by all ``view/*`` generators.

Kept in a private module (not ``__init__``) so that the ``view`` package
itself remains side-effect free: importing ``factory.generators.view``
pulls nothing beyond an empty namespace.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

_REFRESH_RE = re.compile(r"^\s*(\d+)\s*(ms|s|m|h)?\s*$", re.IGNORECASE)


def refresh_to_ms(value: str) -> int:
    """Convert a human-readable refresh interval to milliseconds.

    Accepts ``"500ms"``, ``"1s"``, ``"2m"``, ``"1h"``. ``"never"`` and any
    unparseable value fall back to 60_000 ms (one minute) so callers never
    need to branch on a missing interval.
    """
    if not value or value.strip().lower() == "never":
        return 60_000
    m = _REFRESH_RE.match(value)
    if not m:
        return 60_000
    n = int(m.group(1))
    unit = (m.group(2) or "ms").lower()
    return {"ms": n, "s": n * 1000, "m": n * 60_000, "h": n * 3_600_000}[unit]


def is_never(value: str) -> bool:
    """Return True when the refresh value means 'fetch once, do not poll'."""
    return bool(value) and value.strip().lower() == "never"


def uses_host_local_sources(bundle) -> bool:
    for source in bundle.sources:
        host = urlparse(source.uri).hostname or ""
        if host in {"localhost", "127.0.0.1"}:
            return True
    return False

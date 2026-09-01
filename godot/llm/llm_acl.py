"""ACL policy for URI fetch and bundle redaction."""
from __future__ import annotations

import fnmatch
import ipaddress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote_to_bytes, urlparse

import yaml

from llm_util import is_private_host


@dataclass(frozen=True)
class ACLPolicy:
    allow_patterns: list[str] = field(default_factory=list)
    deny_patterns: list[str] = field(default_factory=list)
    allow_file_roots: list[Path] = field(default_factory=list)
    allowed_schemes: list[str] = field(
        default_factory=lambda: ["http", "https", "file", "data"]
    )
    deny_private_networks: bool = True
    deny_cidrs: list[str] = field(default_factory=list)
    allow_cidrs: list[str] = field(default_factory=list)
    endpoint_deny_patterns: list[str] = field(default_factory=list)
    redact_fields: list[str] = field(
        default_factory=lambda: ["password", "secret_key", "api_key", "token"]
    )

    @classmethod
    def from_file(cls, path: Path) -> "ACLPolicy":
        if not path.exists():
            return cls()
        raw = yaml.safe_load(path.read_text()) or {}
        return cls(
            allow_patterns=list(raw.get("allow_patterns", []) or []),
            deny_patterns=list(raw.get("deny_patterns", []) or []),
            allow_file_roots=[Path(p) for p in raw.get("allow_file_roots", []) or []],
            allowed_schemes=list(
                raw.get("allowed_schemes", ["http", "https", "file", "data"]) or []
            ),
            deny_private_networks=bool(raw.get("deny_private_networks", True)),
            deny_cidrs=list(raw.get("deny_cidrs", []) or []),
            allow_cidrs=list(raw.get("allow_cidrs", []) or []),
            endpoint_deny_patterns=list(raw.get("endpoint_deny_patterns", []) or []),
            redact_fields=list(
                raw.get("redact_fields", ["password", "secret_key", "api_key", "token"])
                or []
            ),
        )

    def _matches_any(self, patterns: list[str], values: list[str]) -> bool:
        for pattern in patterns:
            for value in values:
                if fnmatch.fnmatch(value, pattern):
                    return True
        return False

    def _ip_in_cidrs(self, host: str, cidrs: list[str]) -> bool:
        try:
            addr = ipaddress.ip_address(host)
            for cidr in cidrs:
                if addr in ipaddress.ip_network(cidr, strict=False):
                    return True
        except ValueError:
            pass
        return False

    def _allows_file(self, uri: str, path: str, values: list[str]) -> tuple[bool, str]:
        fpath = Path(unquote_to_bytes(path).decode("utf-8", errors="ignore")).resolve()
        for root in self.allow_file_roots:
            try:
                fpath.relative_to(root.resolve())
                return True, "file path allowed"
            except ValueError:
                continue
        if self._matches_any(self.allow_patterns, values):
            return True, "allowed by explicit pattern"
        return False, f"file path '{fpath}' is not inside an allowed root"

    def _allows_network(self, uri: str, host: str, path: str, values: list[str]) -> tuple[bool, str]:
        if self._matches_any(self.allow_patterns, values):
            return True, "allowed by explicit pattern"
        if self.deny_private_networks and is_private_host(host):
            return False, f"host '{host}' is private or loopback"
        if self._ip_in_cidrs(host, self.deny_cidrs):
            return False, f"host '{host}' matches deny CIDR"
        if self.allow_cidrs and not self._ip_in_cidrs(host, self.allow_cidrs):
            return False, f"host '{host}' is not in any allowed CIDR"
        return False, f"uri '{uri}' does not match any allow rule"

    def allows(self, uri: str) -> tuple[bool, str]:
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()
        host = parsed.hostname or ""
        netloc = parsed.netloc or ""
        path = parsed.path or "/"
        values = [uri, host, netloc, f"{scheme}://{host}{path}"]

        if scheme not in self.allowed_schemes:
            return False, f"scheme '{scheme}' is not allowed"
        if self._matches_any(self.deny_patterns, values):
            return False, f"uri '{uri}' matches deny policy"
        if self._matches_any(self.endpoint_deny_patterns, [path, f"{host}{path}"]):
            return False, f"uri '{uri}' matches endpoint deny policy"
        if scheme == "file":
            return self._allows_file(uri, path, values)
        return self._allows_network(uri, host, path, values)

    def redact_bundle(self, bundle: dict[str, Any]) -> dict[str, Any]:
        if not self.redact_fields:
            return bundle

        def _redact(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {
                    k: "***REDACTED***" if k in self.redact_fields else _redact(v)
                    for k, v in obj.items()
                }
            if isinstance(obj, list):
                return [_redact(i) for i in obj]
            return obj

        return _redact(bundle)

    def describe(self) -> dict[str, Any]:
        return {
            "allow_patterns": self.allow_patterns,
            "deny_patterns": self.deny_patterns,
            "allow_file_roots": [str(path) for path in self.allow_file_roots],
            "allowed_schemes": self.allowed_schemes,
            "deny_private_networks": self.deny_private_networks,
            "deny_cidrs": self.deny_cidrs,
            "allow_cidrs": self.allow_cidrs,
            "endpoint_deny_patterns": self.endpoint_deny_patterns,
            "redact_fields": self.redact_fields,
        }

"""Policy engine.

Decides whether a given user can execute a given command/query on a given
resource URI. Rules are loaded from YAML so they can be changed without
rebuilding the image.
"""
from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class User:
    sub: str
    username: str
    role: str
    claims: dict[str, Any]

    def has_role(self, role: str) -> bool:
        return self.role == role


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str = ""

    @classmethod
    def allow(cls, reason: str = "") -> "PolicyDecision":
        return cls(True, reason)

    @classmethod
    def deny(cls, reason: str) -> "PolicyDecision":
        return cls(False, reason)


class PolicyEngine:
    def __init__(self, rules: list[dict[str, Any]]) -> None:
        self.rules = rules

    @classmethod
    def from_file(cls, path: str | Path) -> "PolicyEngine":
        p = Path(path)
        if not p.exists():
            logger.warning("Policy file not found at %s - using deny-all", p)
            return cls([])
        data = yaml.safe_load(p.read_text()) or {}
        return cls(data.get("policies", []))

    def _rules_for(self, role: str) -> list[dict[str, Any]]:
        return [r for r in self.rules if r.get("role") == role or r.get("role") == "*"]

    @staticmethod
    def _match_any(patterns: list[str], value: str) -> bool:
        return any(fnmatch.fnmatchcase(value, pat) for pat in patterns)

    def can_execute_command(
        self,
        user: User,
        command_type: str,
        input_uri: str | None = None,
        schema_uri: str | None = None,
    ) -> PolicyDecision:
        rules = self._rules_for(user.role)
        if not rules:
            return PolicyDecision.deny(f"No rules for role {user.role!r}")

        for rule in rules:
            # command name check
            allowed_cmds = rule.get("allowed_commands", [])
            if not self._match_any(allowed_cmds, command_type):
                continue

            # input URI check (only when a URI was supplied)
            if input_uri:
                allowed_uris = rule.get("allowed_uris", ["*"])
                if not self._match_any(allowed_uris, input_uri):
                    continue

            # schema URI check (only when a schema was supplied)
            if schema_uri:
                allowed_schemas = rule.get("allowed_schemas", ["*"])
                if not self._match_any(allowed_schemas, schema_uri):
                    continue

            return PolicyDecision.allow(f"matched rule for role {user.role}")

        return PolicyDecision.deny(
            f"No matching rule for role={user.role} command={command_type} "
            f"uri={input_uri} schema={schema_uri}"
        )

    def can_execute_query(
        self,
        user: User,
        query_type: str,
        source_uris: list[str],
        schema_uri: str | None = None,
    ) -> PolicyDecision:
        rules = self._rules_for(user.role)
        if not rules:
            return PolicyDecision.deny(f"No rules for role {user.role!r}")

        for rule in rules:
            allowed_qs = rule.get("allowed_queries", [])
            if not self._match_any(allowed_qs, query_type):
                continue

            allowed_uris = rule.get("allowed_uris", ["*"])
            if not all(self._match_any(allowed_uris, u) for u in source_uris):
                continue

            if schema_uri:
                allowed_schemas = rule.get("allowed_schemas", ["*"])
                if not self._match_any(allowed_schemas, schema_uri):
                    continue

            return PolicyDecision.allow(f"matched rule for role {user.role}")

        return PolicyDecision.deny(
            f"No matching rule for role={user.role} query={query_type} "
            f"sources={source_uris}"
        )


_engine: PolicyEngine | None = None


def get_engine() -> PolicyEngine:
    global _engine
    if _engine is None:
        _engine = PolicyEngine.from_file(settings.policy_rules_path)
    return _engine


def reload_engine() -> PolicyEngine:
    global _engine
    _engine = PolicyEngine.from_file(settings.policy_rules_path)
    return _engine

"""Service Bundle — the intermediate representation.

A Bundle is a deployable unit composed of existing CQRS contracts
(*.command.json, *.query.json, *.event.json) plus runtime/infra decisions.
It is the *only* thing generators consume. Generators never read filesystem
state directly — they get a fully-loaded Bundle and emit {path: content}.

This decoupling is why the same Bundle can be emitted as:
  - Python/FastAPI + Docker + OpenAPI
  - Node/Fastify + k8s + AsyncAPI
  - Go/Chi + Nomad + Proto
… without changing the IR.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------- Contract wrappers ------------------------------------------------

@dataclass(frozen=True)
class Contract:
    """Unified view over command/query/event contract JSON."""

    raw: dict[str, Any]
    source_file: str = ""

    @property
    def kind(self) -> str:
        return self.raw.get("kind", "")

    @property
    def name(self) -> str:
        return (
            self.raw.get("command")
            or self.raw.get("query")
            or self.raw.get("event")
            or ""
        )

    @property
    def is_command(self) -> bool:
        return "command" in self.raw

    @property
    def is_query(self) -> bool:
        return "query" in self.raw

    @property
    def is_event(self) -> bool:
        return "event" in self.raw

    @property
    def module(self) -> str:
        return self.raw.get("module", "")

    @property
    def description(self) -> str:
        return self.raw.get("description", "")

    @property
    def version(self) -> str:
        return self.raw.get("version", "1.0.0")

    @property
    def http_method(self) -> str:
        return self.raw.get("transport", {}).get("http", {}).get("method", "POST")

    @property
    def http_endpoint(self) -> str:
        return self.raw.get("transport", {}).get("http", {}).get("endpoint", "")

    @property
    def ws_channel(self) -> str:
        return self.raw.get("transport", {}).get("ws", {}).get("channel", "")

    @property
    def input_fields(self) -> dict[str, dict[str, Any]]:
        return self.raw.get("input", {})

    @property
    def output_fields(self) -> dict[str, dict[str, Any]]:
        return self.raw.get("output", {})

    @property
    def payload_fields(self) -> dict[str, dict[str, Any]]:
        return self.raw.get("payload", {})

    @property
    def success_event(self) -> str:
        return self.raw.get("events", {}).get("success", "")

    @property
    def failure_event(self) -> str:
        return self.raw.get("events", {}).get("failure", "")


# ---------- Bundle -----------------------------------------------------------

@dataclass
class Runtime:
    language: str = "python"     # python | node | go | rust
    version: str = "3.12"
    framework: str = "fastapi"   # fastapi | fastify | chi | actix


@dataclass
class Storage:
    kind: str = "none"           # none | postgres | sqlite | mongodb
    database: str = ""
    tables: list[str] = field(default_factory=list)


@dataclass
class Companion:
    name: str
    kind: str                    # litellm | mcp | redis | postgres | nginx
    config: dict[str, Any] = field(default_factory=dict)
    image: str = ""              # explicit image overrides derived default


@dataclass
class Resources:
    cpu: str = "500m"
    memory: str = "512Mi"


@dataclass
class Exposure:
    port: int = 8080
    health_path: str = "/health"


@dataclass
class Bundle:
    name: str
    version: str = "1.0.0"
    description: str = ""
    runtime: Runtime = field(default_factory=Runtime)
    contracts: list[Contract] = field(default_factory=list)
    storage: Storage = field(default_factory=Storage)
    companions: list[Companion] = field(default_factory=list)
    resources: Resources = field(default_factory=Resources)
    ttl: str = "24h"
    exposure: Exposure = field(default_factory=Exposure)

    # ----- convenience accessors used by generators -------------------------

    @property
    def commands(self) -> list[Contract]:
        return [c for c in self.contracts if c.is_command]

    @property
    def queries(self) -> list[Contract]:
        return [c for c in self.contracts if c.is_query]

    @property
    def events(self) -> list[Contract]:
        return [c for c in self.contracts if c.is_event]

    def contract_hash(self) -> str:
        """Stable hash over all inputs that affect generated output.

        Two bundles with the same hash produce byte-identical artifacts —
        this is what lets the runtime cache built images keyed by hash.
        """
        h = hashlib.sha256()
        payload = {
            "name": self.name,
            "version": self.version,
            "runtime": self.runtime.__dict__,
            "storage": self.storage.__dict__,
            "companions": [c.__dict__ for c in self.companions],
            "resources": self.resources.__dict__,
            "exposure": self.exposure.__dict__,
            "contracts": [c.raw for c in self.contracts],
        }
        h.update(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        return h.hexdigest()[:16]


# ---------- Loader -----------------------------------------------------------

class BundleLoader:
    """Reads a bundle.json plus referenced contract files from disk."""

    def __init__(self, contracts_dir: Path) -> None:
        self.contracts_dir = contracts_dir

    def load(self, bundle_path: Path) -> Bundle:
        raw = json.loads(bundle_path.read_text())
        self._validate(raw, bundle_path)

        contracts: list[Contract] = []
        for ref in raw.get("contracts", []):
            path = self._resolve_contract(ref, bundle_path)
            contract_raw = json.loads(path.read_text())
            contracts.append(Contract(raw=contract_raw, source_file=path.name))

        return Bundle(
            name=raw["bundle"],
            version=raw.get("version", "1.0.0"),
            description=raw.get("description", ""),
            runtime=Runtime(**raw.get("runtime", {})),
            contracts=contracts,
            storage=Storage(**raw.get("storage", {})),
            companions=[Companion(**c) for c in raw.get("companions", [])],
            resources=Resources(**raw.get("resources", {})),
            ttl=raw.get("ttl", "24h"),
            exposure=Exposure(**raw.get("exposure", {})),
        )

    def _resolve_contract(self, ref: str, bundle_path: Path) -> Path:
        candidates = [
            self.contracts_dir / ref,
            bundle_path.parent / ref,
            Path(ref),
        ]
        for c in candidates:
            if c.exists():
                return c
        raise FileNotFoundError(
            f"Contract {ref!r} not found (looked in {[str(c) for c in candidates]})"
        )

    @staticmethod
    def _validate(raw: dict, path: Path) -> None:
        required = ["bundle", "contracts"]
        missing = [k for k in required if k not in raw]
        if missing:
            raise ValueError(f"{path}: bundle missing required fields: {missing}")
        if raw.get("kind") and raw["kind"] != "SERVICE_BUNDLE":
            raise ValueError(f"{path}: kind must be SERVICE_BUNDLE")

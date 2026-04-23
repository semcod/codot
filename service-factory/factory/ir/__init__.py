"""Service & View bundles — the intermediate representation.

Two bundle kinds share the same IR module so they can be compiled by the
same pipeline:

- ``SERVICE_BUNDLE`` — a deployable service composed of CQRS contracts
  (*.command.json, *.query.json, *.event.json) plus runtime/infra decisions.
- ``VIEW_BUNDLE``   — a read-only aggregation view over existing service URLs.
  No contracts, no storage; just sources + template + transport.

Both are consumed by Generator instances that emit ``{path: content}`` maps.
Generators never touch the filesystem — they receive a fully-loaded bundle
object. This is what lets the same IR be emitted to wildly different targets
(Python/FastAPI vs Node/Fastify, Docker vs k8s, PHP standalone vs FastAPI SSE)
without touching the IR itself.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union


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


# ---------- View Bundle ------------------------------------------------------

@dataclass(frozen=True)
class Source:
    """A URL the view aggregates from. Refresh is advisory metadata used by
    generators to decide polling / SSE / cache-control behaviour."""

    name: str
    uri: str
    refresh: str = "5s"        # e.g. "500ms", "1s", "1m", "never"
    depends_on: list[str] = field(default_factory=list)
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Template:
    """How the view is rendered. ``engine`` is a hint for generators;
    each generator is free to ignore engines it cannot honour (e.g. the
    php-standalone generator always uses PHP itself for templating)."""

    engine: str = "inline"     # inline | jinja2 | mustache
    source: str = ""           # inline template body
    source_uri: str = ""       # file:// or http:// reference


@dataclass
class ViewBundle:
    name: str
    version: str = "1.0.0"
    description: str = ""
    sources: list[Source] = field(default_factory=list)
    template: Template = field(default_factory=Template)
    transport: str = "polling"  # polling | sse | static
    exposure: Exposure = field(default_factory=lambda: Exposure(port=8081))

    def contract_hash(self) -> str:
        """Stable hash over every input that affects the generated output."""
        h = hashlib.sha256()
        payload = {
            "name": self.name,
            "version": self.version,
            "sources": [s.__dict__ for s in self.sources],
            "template": self.template.__dict__,
            "transport": self.transport,
            "exposure": self.exposure.__dict__,
        }
        h.update(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        return h.hexdigest()[:16]


AnyBundle = Union[Bundle, ViewBundle]


# ---------- Loader -----------------------------------------------------------

class BundleLoader:
    """Reads a bundle.json from disk.

    Discriminates on the ``kind`` field:
    - ``SERVICE_BUNDLE`` (default) → returns :class:`Bundle` with resolved contracts.
    - ``VIEW_BUNDLE``              → returns :class:`ViewBundle` (no contracts).
    """

    def __init__(self, contracts_dir: Path) -> None:
        self.contracts_dir = contracts_dir

    def load(self, bundle_path: Path) -> AnyBundle:
        raw = json.loads(bundle_path.read_text())
        kind = raw.get("kind", "SERVICE_BUNDLE")
        if kind == "VIEW_BUNDLE":
            return self._load_view(raw, bundle_path)
        if kind == "SERVICE_BUNDLE":
            return self._load_service(raw, bundle_path)
        raise ValueError(
            f"{bundle_path}: unknown kind {kind!r} (expected SERVICE_BUNDLE or VIEW_BUNDLE)"
        )

    def _load_service(self, raw: dict, bundle_path: Path) -> Bundle:
        self._validate_service(raw, bundle_path)
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

    def load_from_dict(self, raw: dict, bundle_path: Path | None = None) -> AnyBundle:
        """Load bundle from an already-parsed dict (no disk read)."""
        path = bundle_path or Path("bundle.json")
        kind = raw.get("kind", "SERVICE_BUNDLE")
        if kind == "VIEW_BUNDLE":
            return self._load_view(raw, path)
        if kind == "SERVICE_BUNDLE":
            return self._load_service(raw, path)
        raise ValueError(f"unknown kind {kind!r} (expected SERVICE_BUNDLE or VIEW_BUNDLE)")

    def _load_view(self, raw: dict, bundle_path: Path) -> ViewBundle:
        self._validate_view(raw, bundle_path)
        sources = [Source(**s) for s in raw.get("sources", [])]
        template = Template(**raw.get("template", {}))
        return ViewBundle(
            name=raw["bundle"],
            version=raw.get("version", "1.0.0"),
            description=raw.get("description", ""),
            sources=sources,
            template=template,
            transport=raw.get("transport", "polling"),
            exposure=Exposure(**raw.get("exposure", {"port": 8081})),
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
    def _validate_service(raw: dict, path: Path) -> None:
        required = ["bundle", "contracts"]
        missing = [k for k in required if k not in raw]
        if missing:
            raise ValueError(f"{path}: service bundle missing required fields: {missing}")

    @staticmethod
    def _validate_view(raw: dict, path: Path) -> None:
        required = ["bundle", "sources"]
        missing = [k for k in required if k not in raw]
        if missing:
            raise ValueError(f"{path}: view bundle missing required fields: {missing}")
        if not isinstance(raw["sources"], list) or not raw["sources"]:
            raise ValueError(f"{path}: view bundle 'sources' must be a non-empty list")
        transport = raw.get("transport", "polling")
        if transport not in {"polling", "sse", "static"}:
            raise ValueError(
                f"{path}: view bundle transport must be one of polling|sse|static, got {transport!r}"
            )

from __future__ import annotations

import base64
import fnmatch
import ipaddress
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from urllib.parse import unquote_to_bytes, urlparse

import httpx
import yaml
from fastapi import FastAPI, HTTPException
from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field

try:
    from litellm import completion as litellm_completion
except Exception:  # pragma: no cover - optional dependency at runtime
    litellm_completion = None

try:
    import audit
    audit.ensure_table()
except Exception:  # pragma: no cover - optional at runtime (no postgres)
    audit = None  # type: ignore[assignment]

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT
DEFAULT_SCHEMA_FILE = REPO_ROOT / "bundle.schema.json"
DEFAULT_ACL_FILE = APP_ROOT / "acl.yaml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "bundles" / "generated"

BundleKind = Literal[
    "SERVICE_BUNDLE",
    "VIEW_BUNDLE",
    "WORKFLOW_BUNDLE",
    "APPLICATION_BUNDLE",
]
TargetKind = Literal["desktop", "mobile", "web", "pwa", "service", "cli"]


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
        return {key: compact(item) for key, item in value.items() if item not in (None, [], {}, "")}
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


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("LLM_MODEL", "openrouter/qwen/qwen3-coder-next")
    api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    api_base: str = os.getenv("LLM_API_BASE", "")
    offline: bool = env_bool("LLM_OFFLINE", True)
    schema_file: Path = Path(os.getenv("BUNDLE_SCHEMA_FILE", str(DEFAULT_SCHEMA_FILE)))
    schema_uri: str = os.getenv("BUNDLE_SCHEMA_URI", "file:///app/bundle.schema.json")
    output_dir: Path = Path(os.getenv("BUNDLE_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR)))
    acl_file: Path = Path(os.getenv("LLM_ACL_FILE", str(DEFAULT_ACL_FILE)))
    fetch_timeout_sec: float = env_float("LLM_FETCH_TIMEOUT_SEC", 10.0)
    max_fetch_bytes: int = env_int("LLM_MAX_FETCH_BYTES", 2_000_000)
    default_runner: str = os.getenv("LLM_DEFAULT_RUNNER", "go_temporal")
    default_runtime_lang: str = os.getenv("LLM_DEFAULT_RUNTIME_LANG", "go")
    default_application_targets: list[str] = field(default_factory=lambda: ["web", "pwa"])


@dataclass(frozen=True)
class ACLPolicy:
    allow_patterns: list[str] = field(default_factory=list)
    deny_patterns: list[str] = field(default_factory=list)
    allow_file_roots: list[Path] = field(default_factory=list)
    allowed_schemes: list[str] = field(default_factory=lambda: ["http", "https", "file", "data"])
    deny_private_networks: bool = True

    @classmethod
    def from_file(cls, path: Path) -> "ACLPolicy":
        if not path.exists():
            return cls()
        raw = yaml.safe_load(path.read_text()) or {}
        return cls(
            allow_patterns=list(raw.get("allow_patterns", []) or []),
            deny_patterns=list(raw.get("deny_patterns", []) or []),
            allow_file_roots=[Path(p) for p in raw.get("allow_file_roots", []) or []],
            allowed_schemes=list(raw.get("allowed_schemes", ["http", "https", "file", "data"]) or []),
            deny_private_networks=bool(raw.get("deny_private_networks", True)),
        )

    def _matches_any(self, patterns: list[str], values: list[str]) -> bool:
        for pattern in patterns:
            for value in values:
                if fnmatch.fnmatch(value, pattern):
                    return True
        return False

    def allows(self, uri: str) -> tuple[bool, str]:
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()
        host = parsed.hostname or ""
        netloc = parsed.netloc or ""
        values = [uri, host, netloc, f"{scheme}://{host}{parsed.path or '/'}"]

        if scheme not in self.allowed_schemes:
            return False, f"scheme '{scheme}' is not allowed"

        if self._matches_any(self.deny_patterns, values):
            return False, f"uri '{uri}' matches deny policy"

        if scheme == "file":
            path = Path(unquote_to_bytes(parsed.path).decode("utf-8", errors="ignore")).resolve()
            for root in self.allow_file_roots:
                try:
                    path.relative_to(root.resolve())
                    return True, "file path allowed"
                except ValueError:
                    continue
            if self._matches_any(self.allow_patterns, values):
                return True, "allowed by explicit pattern"
            return False, f"file path '{path}' is not inside an allowed root"

        if self._matches_any(self.allow_patterns, values):
            return True, "allowed by explicit pattern"

        if self.deny_private_networks and is_private_host(host):
            return False, f"host '{host}' is private or loopback"

        return False, f"uri '{uri}' does not match any allow rule"

    def describe(self) -> dict[str, Any]:
        return {
            "allow_patterns": self.allow_patterns,
            "deny_patterns": self.deny_patterns,
            "allow_file_roots": [str(path) for path in self.allow_file_roots],
            "allowed_schemes": self.allowed_schemes,
            "deny_private_networks": self.deny_private_networks,
        }


class FetchRequest(BaseModel):
    uri: str
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None


class FetchManyRequest(BaseModel):
    uris: list[str] = Field(default_factory=list)


class GenerateBundleRequest(BaseModel):
    prompt: str
    bundle_name: str | None = None
    bundle_kind: BundleKind | None = None
    targets: list[TargetKind] = Field(default_factory=list)
    source_uris: list[str] = Field(default_factory=list)
    runner: str | None = None
    output_format: str | None = None
    write_file: bool = True
    include_context: bool = False


@dataclass(frozen=True)
class AppState:
    settings: Settings
    acl: ACLPolicy
    validator: Draft202012Validator


def build_state() -> AppState:
    settings = Settings()
    schema = json.loads(settings.schema_file.read_text())
    validator = Draft202012Validator(schema)
    acl = ACLPolicy.from_file(settings.acl_file)
    return AppState(settings=settings, acl=acl, validator=validator)


STATE = build_state()


def infer_kind(prompt: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    lower = prompt.lower()
    if any(token in lower for token in ["workflow", "pipeline", "orchestrate", "dag"]):
        return "WORKFLOW_BUNDLE"
    if any(token in lower for token in ["dashboard", "view", "ui", "frontend", "panel", "stream", "live"]):
        return "VIEW_BUNDLE"
    if any(token in lower for token in ["desktop", "mobile", "web", "pwa", "application", "app ", "app\n"]):
        return "APPLICATION_BUNDLE"
    return "SERVICE_BUNDLE"


def infer_targets(prompt: str, explicit: list[str], kind: str) -> list[str]:
    if explicit:
        return dedupe(explicit)
    lower = prompt.lower()
    detected: list[str] = []
    for target in ["desktop", "mobile", "web", "pwa", "service", "cli"]:
        if target in lower:
            detected.append(target)
    if kind == "APPLICATION_BUNDLE" and not detected:
        return ["web", "pwa"]
    return dedupe(detected)


def infer_runner(kind: str, targets: list[str], explicit: str | None = None) -> str:
    if explicit:
        return explicit
    if kind == "APPLICATION_BUNDLE":
        return STATE.settings.default_runner
    if kind == "VIEW_BUNDLE" and any(target in targets for target in ["web", "pwa"]):
        return "go_temporal"
    return STATE.settings.default_runner


def infer_output_format(kind: str, targets: list[str], prompt: str, runner: str) -> str:
    lower = prompt.lower()
    if kind == "APPLICATION_BUNDLE":
        if {"desktop", "mobile"}.intersection(targets):
            return "desktop_mobile_app"
        if {"web", "pwa"}.intersection(targets):
            return "web_pwa"
        return "multi_platform_app"
    if kind == "VIEW_BUNDLE":
        if "stream" in lower or "sse" in lower or "live" in lower:
            return "fastapi_sse"
        return "static_html"
    if kind == "WORKFLOW_BUNDLE":
        return "temporal_workflow"
    return "python_fastapi"


def infer_runtime(kind: str, targets: list[str], runner: str) -> dict[str, Any]:
    if kind == "WORKFLOW_BUNDLE":
        return {"lang": "go"}
    if kind == "APPLICATION_BUNDLE":
        return {"port": 8086, "lang": "python"}
    if kind == "VIEW_BUNDLE":
        return {"port": 8082, "lang": "php"}
    if runner == "python_fastapi":
        return {"port": 8080, "lang": "python"}
    return {"port": 8080, "lang": STATE.settings.default_runtime_lang}


def source_name_from_uri(uri: str, index: int) -> str:
    parsed = urlparse(uri)
    candidate = parsed.hostname or parsed.path.strip("/") or f"source-{index + 1}"
    candidate = candidate.replace(":", "-").replace("/", "-")
    candidate = re.sub(r"[^a-zA-Z0-9_-]+", "-", candidate).strip("-")
    return candidate or f"source-{index + 1}"


def build_sources(uris: list[str]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    previous_name: str | None = None
    for index, uri in enumerate(uris):
        name = source_name_from_uri(uri, index)
        source: dict[str, Any] = {
            "name": name,
            "uri": uri,
            "refresh_sec": 15 if index == 0 else 30,
        }
        if previous_name:
            source["depends_on"] = [previous_name]
        sources.append(source)
        previous_name = name
    return sources


def normalize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    normalized = compact(bundle)
    if isinstance(normalized, dict):
        return normalized
    raise ValueError("bundle normalization failed")


async def maybe_refine_bundle(prompt: str, base_bundle: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    if STATE.settings.offline or not STATE.settings.api_key or litellm_completion is None:
        return base_bundle, False

    system_prompt = (
        "You create JSON bundle specifications for a Go-backed service factory. "
        "Return only a JSON object with the following fields: bundle, kind, version, description, schema_uri, runner, targets, sources, output. "
        "Keep it compatible with the provided base bundle and do not add commentary."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps({"prompt": prompt, "bundle": base_bundle}, ensure_ascii=False)},
    ]

    try:
        response = litellm_completion(
            model=STATE.settings.model,
            messages=messages,
            api_key=STATE.settings.api_key,
            api_base=STATE.settings.api_base or None,
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        candidate = json.loads(content)
        if isinstance(candidate, dict):
            merged = dict(base_bundle)
            merged.update(candidate)
            return normalize_bundle(merged), True
    except Exception:
        return base_bundle, False

    return base_bundle, False


def validate_bundle(bundle: dict[str, Any]) -> None:
    errors = sorted(STATE.validator.iter_errors(bundle), key=lambda error: list(error.path))
    if errors:
        details = []
        for error in errors:
            path = "/".join(str(item) for item in error.path)
            details.append({"path": path, "message": error.message})
        raise HTTPException(status_code=422, detail={"message": "bundle validation failed", "errors": details})


async def fetch_uri(request: FetchRequest) -> dict[str, Any]:
    allowed, reason = STATE.acl.allows(request.uri)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    parsed = urlparse(request.uri)
    if parsed.scheme == "file":
        path = Path(unquote_to_bytes(parsed.path).decode("utf-8", errors="ignore")).resolve()
        data = path.read_bytes()
        content_type = "application/octet-stream"
    elif parsed.scheme == "data":
        header, _, payload = request.uri.partition(",")
        metadata = header[5:]
        is_base64 = ";base64" in metadata
        content_type = metadata.split(";")[0] or "text/plain;charset=US-ASCII"
        data = base64.b64decode(payload) if is_base64 else unquote_to_bytes(payload)
    else:
        async with httpx.AsyncClient(timeout=STATE.settings.fetch_timeout_sec, follow_redirects=False) as client:
            response = await client.request(
                request.method.upper(),
                request.uri,
                headers=request.headers,
                content=request.body.encode("utf-8") if request.body is not None else None,
            )
            response.raise_for_status()
            data = response.content
            content_type = response.headers.get("content-type", "application/octet-stream")

    if len(data) > STATE.settings.max_fetch_bytes:
        raise HTTPException(status_code=413, detail="payload is too large")

    result: dict[str, Any] = {
        "uri": request.uri,
        "content_type": content_type,
        "size": len(data),
    }
    try:
        text = data.decode("utf-8")
        result["text"] = text
        try:
            result["json"] = json.loads(text)
        except json.JSONDecodeError:
            pass
    except UnicodeDecodeError:
        result["payload_b64"] = base64.b64encode(data).decode("ascii")
    return result


async def fetch_many(uris: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for uri in uris:
        try:
            items.append({"uri": uri, "ok": True, "result": await fetch_uri(FetchRequest(uri=uri))})
        except HTTPException as exc:
            items.append({"uri": uri, "ok": False, "status_code": exc.status_code, "detail": exc.detail})
    return items


async def build_bundle_from_prompt(request: GenerateBundleRequest) -> tuple[dict[str, Any], bool, list[dict[str, Any]]]:
    kind = infer_kind(request.prompt, request.bundle_kind)
    targets = infer_targets(request.prompt, request.targets, kind)
    bundle_name = request.bundle_name or slugify(request.prompt)
    runner = infer_runner(kind, targets, request.runner)
    output_format = request.output_format or infer_output_format(kind, targets, request.prompt, runner)
    sources = build_sources(request.source_uris)

    bundle: dict[str, Any] = {
        "bundle": bundle_name,
        "kind": kind,
        "version": "1.0.0",
        "description": request.prompt.strip(),
        "schema_uri": STATE.settings.schema_uri,
        "runner": runner,
        "targets": targets,
        "sources": sources,
        "output": {
            "format": output_format,
            "runtime": infer_runtime(kind, targets, runner),
        },
    }

    bundle = normalize_bundle(bundle)
    bundle, llm_used = await maybe_refine_bundle(request.prompt, bundle)
    validate_bundle(bundle)

    context_items: list[dict[str, Any]] = []
    if request.include_context and request.source_uris:
        context_items = await fetch_many(request.source_uris)

    return bundle, llm_used, context_items


async def write_bundle(bundle: dict[str, Any], output_dir: Path | None = None) -> Path:
    target_dir = output_dir or STATE.settings.output_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{bundle['bundle']}.json"
    target_path = target_dir / filename
    target_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n")
    return target_path


main_app = FastAPI(title="Godot LiteLLM Bundle Service", version="1.0.0")
mock_app = FastAPI(title="Godot Mock API", version="1.0.0")
app = main_app


@main_app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "godot-llm",
        "offline": STATE.settings.offline,
        "model": STATE.settings.model,
        "output_dir": str(STATE.settings.output_dir),
    }


@main_app.get("/bundles")
async def list_bundles() -> dict[str, Any]:
    target_dir = STATE.settings.output_dir
    if not target_dir.exists():
        return {"count": 0, "files": []}
    files = sorted(str(path.relative_to(target_dir)) for path in target_dir.rglob("*.json") if path.is_file())
    return {"count": len(files), "files": files}


@main_app.get("/acl")
async def describe_acl() -> dict[str, Any]:
    return STATE.acl.describe()


@main_app.post("/fetch")
async def fetch_single(request: FetchRequest) -> dict[str, Any]:
    return await fetch_uri(request)


@main_app.post("/context")
async def fetch_context(request: FetchManyRequest) -> dict[str, Any]:
    return {"count": len(request.uris), "items": await fetch_many(request.uris)}


@main_app.post("/generate/bundle")
async def generate_bundle(request: GenerateBundleRequest) -> dict[str, Any]:
    import time as _time
    t0 = _time.time()
    error_text: str | None = None
    bundle: dict[str, Any] = {}
    try:
        bundle, llm_used, context_items = await build_bundle_from_prompt(request)
        file_path = None
        if request.write_file:
            file_path = str(await write_bundle(bundle))
        return {
            "bundle": bundle,
            "bundle_name": bundle.get("bundle", "unknown"),
            "kind": bundle.get("kind", "SERVICE_BUNDLE"),
            "targets": bundle.get("targets", []),
            "file_path": file_path,
            "llm_used": llm_used,
            "context": context_items,
        }
    except Exception as exc:
        error_text = str(exc)
        raise
    finally:
        if audit is not None:
            try:
                audit.log_generation(
                    endpoint="/generate/bundle",
                    prompt=request.prompt or "",
                    kind=bundle.get("kind", "SERVICE_BUNDLE") if bundle else "",
                    runner=bundle.get("runner", "") if bundle else "",
                    targets=bundle.get("targets", []) if bundle else [],
                    generated_bundle=bundle if bundle else None,
                    acl_allowed=True,
                    error=error_text,
                    client_ip=None,
                    duration_ms=(_time.time() - t0) * 1000,
                )
            except Exception:
                pass


@main_app.post("/generate/bundles")
async def generate_bundles(requests: list[GenerateBundleRequest]) -> dict[str, Any]:
    results = []
    for request in requests:
        results.append(await generate_bundle(request))
    return {"count": len(results), "items": results}


@mock_app.get("/health")
async def mock_health() -> dict[str, Any]:
    return {"status": "ok", "service": "mock-api"}


@mock_app.get("/api/v1/devices")
async def mock_devices() -> dict[str, Any]:
    return {
        "items": [
            {"id": "device-1", "name": "temperature-sensor", "status": "online"},
            {"id": "device-2", "name": "humidity-sensor", "status": "offline"},
            {"id": "device-3", "name": "pressure-sensor", "status": "online"},
        ]
    }


@mock_app.get("/api/v1/protocols/{protocol_id}")
async def mock_protocol(protocol_id: str) -> dict[str, Any]:
    return {
        "protocol_id": protocol_id,
        "status": "active",
        "owner": "ops",
        "devices": ["device-1", "device-2"],
    }


@mock_app.get("/api/v1/posts")
async def mock_posts() -> dict[str, Any]:
    return {
        "items": [
            {"id": 1, "title": "Hello from Godot", "body": "mock post payload"},
            {"id": 2, "title": "Second post", "body": "more generated data"},
        ]
    }


@mock_app.get("/api/v1/catalog")
async def mock_catalog() -> dict[str, Any]:
    return {
        "service": "mock-api",
        "endpoints": [
            "/health",
            "/api/v1/devices",
            "/api/v1/protocols/{protocol_id}",
            "/api/v1/posts",
        ],
    }

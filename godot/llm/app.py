"""Godot LiteLLM bundle service — FastAPI entrypoint."""
from __future__ import annotations

import time
from typing import Any

import fastapi
from fastapi import FastAPI, HTTPException, Response

from llm_bundle import build_bundle_from_prompt, write_bundle
from llm_fetch import fetch_many, fetch_uri
from llm_mock import mock_app  # noqa: F401 — uvicorn app:mock_app
from llm_paths import APP_ROOT, DEFAULT_ACL_FILE, DEFAULT_OUTPUT_DIR, DEFAULT_SCHEMA_FILE, REPO_ROOT
from llm_schemas import (
    AppState,
    FetchManyRequest,
    FetchRequest,
    GenerateBundleRequest,
    STATE,
    build_state,
)
from llm_settings import Settings
from llm_acl import ACLPolicy
from llm_util import compact, dedupe, env_bool, env_float, env_int, is_private_host, slugify, source_name_from_uri

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except Exception:  # pragma: no cover
    generate_latest = None  # type: ignore[assignment]
    CONTENT_TYPE_LATEST = "text/plain"  # type: ignore[assignment]
    Counter = None  # type: ignore[assignment,misc]
    Histogram = None  # type: ignore[assignment,misc]

if Counter:
    BUNDLE_GENERATIONS = Counter(
        "llm_bundle_generations_total", "Total bundle generations", ["kind", "status"]
    )
    BUNDLE_GENERATION_DURATION = Histogram(
        "llm_bundle_generation_duration_seconds", "Bundle generation latency"
    )
else:
    BUNDLE_GENERATIONS = None  # type: ignore[assignment]
    BUNDLE_GENERATION_DURATION = None  # type: ignore[assignment]

try:
    import audit

    audit.ensure_table()
except Exception:  # pragma: no cover
    audit = None  # type: ignore[assignment]

# Backward-compatible re-exports for callers/tests importing from app
from llm_bundle import (  # noqa: E402,F401
    infer_kind,
    infer_output_format,
    infer_runner,
    infer_runtime,
    infer_targets,
    maybe_refine_bundle,
    normalize_bundle,
    validate_bundle,
    build_sources,
)

main_app = FastAPI(title="Godot LiteLLM Bundle Service", version="1.0.0")
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
    files = sorted(
        str(path.relative_to(target_dir))
        for path in target_dir.rglob("*.json")
        if path.is_file()
    )
    return {"count": len(files), "files": files}


@main_app.get("/acl")
async def describe_acl() -> dict[str, Any]:
    return STATE.acl.describe()


@main_app.get("/auth")
async def auth_validate(
    request: fastapi.Request,
    x_original_uri: str = fastapi.Header(default=""),
    x_original_method: str = fastapi.Header(default=""),
) -> Response:
    """Caddy forward_auth endpoint: validate Bearer token and return scopes."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = auth_header[7:]
    demo_tokens = {
        "admin-token": ["admin", "bundle:write", "bundle:deploy"],
        "user-token": ["bundle:read"],
        "deploy-token": ["bundle:deploy"],
    }
    scopes = demo_tokens.get(token)
    if scopes is None:
        raise HTTPException(status_code=403, detail="Invalid token")
    return Response(
        status_code=200,
        headers={"X-Auth-Scopes": ",".join(scopes)},
    )


@main_app.get("/metrics")
async def metrics() -> Response:
    if generate_latest is None:
        raise HTTPException(status_code=501, detail="Prometheus client not installed")
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@main_app.post("/fetch")
async def fetch_single(request: FetchRequest) -> dict[str, Any]:
    return await fetch_uri(request)


@main_app.post("/context")
async def fetch_context(request: FetchManyRequest) -> dict[str, Any]:
    return {"count": len(request.uris), "items": await fetch_many(request.uris)}


@main_app.post("/generate/bundle")
async def generate_bundle(request: GenerateBundleRequest) -> dict[str, Any]:
    t0 = time.time()
    error_text: str | None = None
    bundle: dict[str, Any] = {}
    try:
        bundle, llm_used, context_items = await build_bundle_from_prompt(
            request,
            fetch_many=fetch_many,
        )
        file_path = None
        if request.write_file:
            file_path = str(await write_bundle(bundle))
        safe_bundle = STATE.acl.redact_bundle(bundle)
        if BUNDLE_GENERATIONS is not None:
            BUNDLE_GENERATIONS.labels(
                kind=bundle.get("kind", "unknown"), status="success"
            ).inc()
        if BUNDLE_GENERATION_DURATION is not None:
            BUNDLE_GENERATION_DURATION.observe(time.time() - t0)
        return {
            "bundle": safe_bundle,
            "bundle_name": safe_bundle.get("bundle", "unknown"),
            "kind": safe_bundle.get("kind", "SERVICE_BUNDLE"),
            "targets": safe_bundle.get("targets", []),
            "file_path": file_path,
            "llm_used": llm_used,
            "context": context_items,
        }
    except Exception as exc:
        error_text = str(exc)
        if BUNDLE_GENERATIONS is not None:
            BUNDLE_GENERATIONS.labels(
                kind=bundle.get("kind", "unknown") if bundle else "unknown",
                status="error",
            ).inc()
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
                    duration_ms=(time.time() - t0) * 1000,
                )
            except Exception:
                pass


@main_app.post("/generate/bundles")
async def generate_bundles(requests: list[GenerateBundleRequest]) -> dict[str, Any]:
    results = []
    for request in requests:
        results.append(await generate_bundle(request))
    return {"count": len(results), "items": results}

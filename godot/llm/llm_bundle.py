"""Bundle inference, validation, and persistence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException

from llm_schemas import GenerateBundleRequest, STATE
from llm_util import compact, dedupe, slugify, source_name_from_uri

try:
    from litellm import completion as litellm_completion
except Exception:  # pragma: no cover
    litellm_completion = None


def infer_kind(prompt: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    lower = prompt.lower()
    if any(token in lower for token in ["workflow", "pipeline", "orchestrate", "dag"]):
        return "WORKFLOW_BUNDLE"
    if any(
        token in lower
        for token in ["dashboard", "view", "ui", "frontend", "panel", "stream", "live"]
    ):
        return "VIEW_BUNDLE"
    if any(
        token in lower
        for token in ["desktop", "mobile", "web", "pwa", "application", "app ", "app\n"]
    ):
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


async def maybe_refine_bundle(
    prompt: str, base_bundle: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    if (
        STATE.settings.offline
        or not STATE.settings.api_key
        or litellm_completion is None
    ):
        return base_bundle, False

    system_prompt = (
        "You create JSON bundle specifications for a Go-backed service factory. "
        "Return only a JSON object with the following fields: bundle, kind, version, description, schema_uri, runner, targets, sources, output. "
        "Keep it compatible with the provided base bundle and do not add commentary."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": json.dumps(
                {"prompt": prompt, "bundle": base_bundle}, ensure_ascii=False
            ),
        },
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
    errors = sorted(
        STATE.validator.iter_errors(bundle), key=lambda error: list(error.path)
    )
    if errors:
        details = []
        for error in errors:
            path = "/".join(str(item) for item in error.path)
            details.append({"path": path, "message": error.message})
        raise HTTPException(
            status_code=422,
            detail={"message": "bundle validation failed", "errors": details},
        )


def _bundle_shell(
    request: GenerateBundleRequest,
    *,
    kind: str,
    targets: list[str],
    bundle_name: str,
    runner: str,
    output_format: str,
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
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


async def build_bundle_from_prompt(
    request: GenerateBundleRequest,
    *,
    fetch_many,
) -> tuple[dict[str, Any], bool, list[dict[str, Any]]]:
    kind = infer_kind(request.prompt, request.bundle_kind)
    targets = infer_targets(request.prompt, request.targets, kind)
    bundle_name = request.bundle_name or slugify(request.prompt)
    runner = infer_runner(kind, targets, request.runner)
    output_format = request.output_format or infer_output_format(
        kind, targets, request.prompt, runner
    )
    sources = build_sources(request.source_uris)

    bundle = normalize_bundle(
        _bundle_shell(
            request,
            kind=kind,
            targets=targets,
            bundle_name=bundle_name,
            runner=runner,
            output_format=output_format,
            sources=sources,
        )
    )
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

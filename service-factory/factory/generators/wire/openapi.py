"""openapi generator.

Emits an OpenAPI 3.1 document covering all commands and queries. The same
Bundle can later drive AsyncAPI (for events/ws) and Proto (for gRPC) with
separate generators — none of them duplicate IR logic.
"""

from __future__ import annotations

import json

from ...ir import Bundle, Contract
from ..types import openapi_type


def _field_schema(meta: dict) -> dict:
    t = meta.get("type", "string")
    fmt = "date-time" if t == "datetime" else None
    spec = openapi_type(t, fmt)
    if meta.get("enum"):
        spec["enum"] = meta["enum"]
    if meta.get("description"):
        spec["description"] = meta["description"]
    return spec


def _schema_from_fields(fields: dict[str, dict]) -> dict:
    props = {name: _field_schema(meta) for name, meta in fields.items()}
    required = [name for name, meta in fields.items() if meta.get("required")]
    schema: dict = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema


def _path_item(c: Contract) -> tuple[str, str, dict]:
    endpoint = c.http_endpoint or f"/api/v1/{c.name}"
    method = c.http_method.lower()
    op = {
        "operationId": c.name[0].lower() + c.name[1:],
        "summary": c.description or c.name,
        "tags": ["commands" if c.is_command else "queries"],
        "responses": {
            "200": {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{c.name}Output"}
                    }
                },
            },
            "501": {"description": "Not implemented"},
        },
    }
    if c.is_command and c.input_fields:
        op["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{c.name}Input"}
                }
            },
        }
    elif c.is_query and c.input_fields:
        op["parameters"] = [
            {
                "name": name,
                "in": "query",
                "required": bool(meta.get("required")),
                "schema": openapi_type(
                    meta.get("type", "string"),
                    "date-time" if meta.get("type", "string") == "datetime" else None,
                ),
            }
            for name, meta in c.input_fields.items()
        ]
    return endpoint, method, op


class OpenApiGenerator:
    target = "openapi"
    category = "wire"

    def generate(self, bundle: Bundle) -> dict[str, str]:
        schemas: dict[str, dict] = {}
        for c in [*bundle.commands, *bundle.queries]:
            if c.input_fields:
                schemas[f"{c.name}Input"] = _schema_from_fields(c.input_fields)
            if c.output_fields:
                schemas[f"{c.name}Output"] = _schema_from_fields(c.output_fields)
        for c in bundle.events:
            schemas[f"{c.name}Event"] = _schema_from_fields(c.payload_fields)

        paths: dict[str, dict] = {}
        for c in [*bundle.commands, *bundle.queries]:
            endpoint, method, op = _path_item(c)
            paths.setdefault(endpoint, {})[method] = op

        # Health is always present
        paths[bundle.exposure.health_path] = {
            "get": {
                "operationId": "health",
                "summary": "Liveness probe",
                "tags": ["health"],
                "responses": {"200": {"description": "ok"}},
            }
        }

        doc = {
            "openapi": "3.1.0",
            "info": {
                "title": bundle.name,
                "version": bundle.version,
                "description": bundle.description,
            },
            "servers": [{"url": f"http://localhost:{bundle.exposure.port}"}],
            "paths": paths,
            "components": {"schemas": schemas},
            "tags": [
                {"name": "commands", "description": "Write-side operations"},
                {"name": "queries", "description": "Read-side operations"},
                {"name": "health", "description": "Liveness / readiness"},
            ],
        }

        return {"openapi.json": json.dumps(doc, indent=2, ensure_ascii=False) + "\n"}

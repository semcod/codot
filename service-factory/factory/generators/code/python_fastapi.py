"""python-fastapi generator.

Takes a Bundle and emits a complete FastAPI service: main.py with one route
per command/query, a Pydantic model per input/output, and placeholder handlers
that log the invocation and raise NotImplementedError.

The generated handlers are stubs by design — the factory produces runnable
skeletons, not business logic. The business logic comes from the handler
referenced in the contract's `layers.handler`, which is imported if present.
"""
from __future__ import annotations

from textwrap import dedent

from ...ir import Bundle, Contract
from ..types import py_type


def _snake(name: str) -> str:
    # CreateDevice -> create_device
    out = []
    for i, c in enumerate(name):
        if c.isupper() and i > 0:
            out.append("_")
        out.append(c.lower())
    return "".join(out)


def _model_field_line(field_name: str, meta: dict) -> str:
    required = meta.get("required", True)
    t = py_type(meta.get("type", "string"), required)
    default = "" if required else " = None"
    desc = meta.get("description", "").replace('"', '\\"')
    if desc:
        return f'    {field_name}: {t}{default}  # {desc}'
    return f"    {field_name}: {t}{default}"


def _pydantic_model(name: str, fields: dict[str, dict]) -> str:
    lines = [f"class {name}(BaseModel):"]
    if not fields:
        lines.append("    pass")
        return "\n".join(lines)
    for field_name, meta in fields.items():
        lines.append(_model_field_line(field_name, meta))
    return "\n".join(lines)


def _command_route(c: Contract) -> str:
    op = _snake(c.name)
    method = c.http_method.lower()
    endpoint = c.http_endpoint or f"/api/v1/{op}"

    input_model = f"{c.name}Input" if c.input_fields else "None"
    output_model = f"{c.name}Output" if c.output_fields else "dict"
    arg = f"body: {input_model}" if c.input_fields else ""

    return dedent(f'''
        @app.{method}("{endpoint}", response_model={output_model}, tags=["commands"])
        async def {op}({arg}) -> {output_model}:
            """{c.description or c.name}"""
            log.info("command.{c.name} invoked")
            # TODO: delegate to {c.raw.get("layers", {}).get("handler", "<handler>")}
            raise HTTPException(status_code=501, detail="not implemented")
    ''').strip()


def _query_params(fields: dict[str, dict]) -> str:
    params = []
    for name, meta in fields.items():
        required = meta.get("required", False)
        t = py_type(meta.get("type", "string"), required)
        default = "" if required else " = None"
        params.append(f"{name}: {t}{default}")
    return ", ".join(params)


def _query_route(c: Contract) -> str:
    op = _snake(c.name)
    method = c.http_method.lower() or "get"
    endpoint = c.http_endpoint or f"/api/v1/{op}"

    output_model = f"{c.name}Output" if c.output_fields else "dict"
    sig = _query_params(c.input_fields)

    return dedent(f'''
        @app.{method}("{endpoint}", response_model={output_model}, tags=["queries"])
        async def {op}({sig}) -> {output_model}:
            """{c.description or c.name}"""
            log.info("query.{c.name} invoked")
            raise HTTPException(status_code=501, detail="not implemented")
    ''').strip()


def _event_model(c: Contract) -> str:
    return _pydantic_model(f"{c.name}Event", c.payload_fields)


class PythonFastApiGenerator:
    target = "python-fastapi"
    category = "code"

    def generate(self, bundle: Bundle) -> dict[str, str]:
        files: dict[str, str] = {}
        files["requirements.txt"] = self._requirements()
        files["models.py"] = self._models(bundle)
        files["events.py"] = self._events(bundle)
        files["main.py"] = self._main(bundle)
        return files

    # ----- file bodies -------------------------------------------------------

    def _requirements(self) -> str:
        return dedent("""\
            fastapi>=0.115.0
            uvicorn[standard]>=0.32.0
            pydantic>=2.9.0
        """)

    def _models(self, bundle: Bundle) -> str:
        parts = [
            '"""Auto-generated request/response models.',
            "",
            'Do not edit — regenerate from contracts.',
            '"""',
            "from __future__ import annotations",
            "",
            "from datetime import datetime  # noqa: F401",
            "from typing import Any  # noqa: F401",
            "",
            "from pydantic import BaseModel",
            "",
            "",
        ]
        for c in [*bundle.commands, *bundle.queries]:
            if c.input_fields:
                parts.append(_pydantic_model(f"{c.name}Input", c.input_fields))
                parts.append("\n")
            if c.output_fields:
                parts.append(_pydantic_model(f"{c.name}Output", c.output_fields))
                parts.append("\n")
        return "\n".join(parts)

    def _events(self, bundle: Bundle) -> str:
        parts = [
            '"""Auto-generated event payloads. Do not edit."""',
            "from __future__ import annotations",
            "",
            "from typing import Any  # noqa: F401",
            "",
            "from pydantic import BaseModel",
            "",
            "",
        ]
        for c in bundle.events:
            parts.append(_event_model(c))
            parts.append("\n")
        return "\n".join(parts)

    def _main(self, bundle: Bundle) -> str:
        # Build the file as a flat list of already-unindented lines.
        # This deliberately avoids dedent() on f-strings whose interpolated
        # values don't share the template's common leading whitespace.
        lines: list[str] = [
            '"""Auto-generated FastAPI service. Do not edit — regenerate from bundle."""',
            "from __future__ import annotations",
            "",
            "import logging",
            "",
            "from fastapi import FastAPI, HTTPException",
            "",
        ]

        if bundle.commands or bundle.queries:
            lines.append("from models import (")
            for c in [*bundle.commands, *bundle.queries]:
                if c.input_fields:
                    lines.append(f"    {c.name}Input,")
                if c.output_fields:
                    lines.append(f"    {c.name}Output,")
            lines.append(")")
            lines.append("")

        lines += [
            "logging.basicConfig(level=logging.INFO)",
            f'log = logging.getLogger("{bundle.name}")',
            "",
            "app = FastAPI(",
            f'    title="{bundle.name}",',
            f'    version="{bundle.version}",',
            f'    description="""{bundle.description or ""}""",',
            ")",
            "",
            "",
            f'@app.get("{bundle.exposure.health_path}", tags=["health"])',
            "async def health() -> dict:",
            f'    return {{"status": "ok", "service": "{bundle.name}", "version": "{bundle.version}"}}',
            "",
            "",
        ]

        for c in bundle.commands:
            lines.append(_command_route(c))
            lines.append("")
            lines.append("")
        for c in bundle.queries:
            lines.append(_query_route(c))
            lines.append("")
            lines.append("")

        return "\n".join(lines)

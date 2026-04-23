"""node-fastify generator.

Parallel to python-fastapi: same bundle, different runtime. Demonstrates
that the IR is language-agnostic.
"""
from __future__ import annotations

from ...ir import Bundle, Contract
from ..types import ts_type


def _camel(name: str) -> str:
    # CreateDevice -> createDevice
    return name[0].lower() + name[1:] if name else name


def _schema_property_line(name: str, meta: dict, pad: str) -> str:
    t = meta.get("type", "string")
    if t == "datetime":
        return f'{pad}{name}: {{ type: "string", format: "date-time" }}'
    if t == "array":
        return f'{pad}{name}: {{ type: "array", items: {{}} }}'
    json_t = {"integer": "integer", "number": "number"}.get(t, t)
    return f'{pad}{name}: {{ type: "{json_t}" }}'


def _schema_object(fields: dict[str, dict], indent: int = 4) -> str:
    """Emit a JSON-Schema literal as JS. indent is the column where the opening
    brace sits; nested keys go deeper by 2-space steps."""
    if not fields:
        return "{}"
    pad = " " * indent
    inner = " " * (indent + 2)
    props_pad = " " * (indent + 4)

    required = [name for name, meta in fields.items() if meta.get("required")]
    props_lines = [_schema_property_line(name, meta, props_pad) for name, meta in fields.items()]

    lines = [
        "{",
        f'{inner}type: "object",',
        f"{inner}properties: {{",
        ",\n".join(props_lines),
        f"{inner}}}",
    ]
    if required:
        req_items = ", ".join(f'"{r}"' for r in required)
        lines[-1] = f"{inner}}},"
        lines.append(f"{inner}required: [{req_items}]")
    lines.append(f"{pad}}}")
    return "\n".join(lines)


def _command_route_lines(c: Contract) -> list[str]:
    method = c.http_method.lower()
    endpoint = c.http_endpoint or f"/api/v1/{_camel(c.name)}"
    body_schema = _schema_object(c.input_fields, indent=4)
    response_schema = _schema_object(c.output_fields, indent=6)
    return [
        f'fastify.{method}("{endpoint}", {{',
        "  schema: {",
        f"    body: {body_schema},",
        f"    response: {{ 200: {response_schema} }}",
        "  }",
        "}, async (request, reply) => {",
        f'  request.log.info({{ cmd: "{c.name}" }}, "command invoked");',
        "  // TODO: delegate to handler",
        '  return reply.code(501).send({ error: "not implemented" });',
        "});",
        "",
    ]


def _query_route_lines(c: Contract) -> list[str]:
    method = c.http_method.lower() or "get"
    endpoint = c.http_endpoint or f"/api/v1/{_camel(c.name)}"
    return [
        f'fastify.{method}("{endpoint}", async (request, reply) => {{',
        f'  request.log.info({{ q: "{c.name}" }}, "query invoked");',
        '  return reply.code(501).send({ error: "not implemented" });',
        "});",
        "",
    ]


class NodeFastifyGenerator:
    target = "node-fastify"
    category = "code"

    def generate(self, bundle: Bundle) -> dict[str, str]:
        return {
            "package.json": self._package_json(bundle),
            "server.js": self._server(bundle),
            "types.d.ts": self._types(bundle),
        }

    def _package_json(self, bundle: Bundle) -> str:
        return (
            "{\n"
            f'  "name": "{bundle.name}",\n'
            f'  "version": "{bundle.version}",\n'
            f'  "description": "{bundle.description}",\n'
            '  "type": "module",\n'
            '  "scripts": {\n'
            '    "start": "node server.js"\n'
            "  },\n"
            '  "dependencies": {\n'
            '    "fastify": "^4.28.0"\n'
            "  }\n"
            "}\n"
        )

    def _server(self, bundle: Bundle) -> str:
        lines: list[str] = [
            "// Auto-generated Fastify server. Do not edit — regenerate from bundle.",
            'import Fastify from "fastify";',
            "",
            "const fastify = Fastify({ logger: true });",
            "",
            f'fastify.get("{bundle.exposure.health_path}", async () => ({{',
            '  status: "ok",',
            f'  service: "{bundle.name}",',
            f'  version: "{bundle.version}"',
            "}));",
            "",
        ]

        for c in bundle.commands:
            lines.extend(_command_route_lines(c))
        for c in bundle.queries:
            lines.extend(_query_route_lines(c))

        lines += [
            f"const port = Number(process.env.PORT || {bundle.exposure.port});",
            'fastify.listen({ port, host: "0.0.0.0" }).catch((err) => {',
            "  fastify.log.error(err);",
            "  process.exit(1);",
            "});",
            "",
        ]
        return "\n".join(lines)

    def _types(self, bundle: Bundle) -> str:
        parts = ["// Auto-generated TS types for the service contracts.", ""]
        for c in [*bundle.commands, *bundle.queries]:
            if c.input_fields:
                parts.append(self._ts_interface(f"{c.name}Input", c.input_fields))
            if c.output_fields:
                parts.append(self._ts_interface(f"{c.name}Output", c.output_fields))
        for c in bundle.events:
            parts.append(self._ts_interface(f"{c.name}Event", c.payload_fields))
        return "\n".join(parts)

    def _ts_interface(self, name: str, fields: dict[str, dict]) -> str:
        lines = [f"export interface {name} {{"]
        for fname, meta in fields.items():
            required = meta.get("required", True)
            t = ts_type(meta.get("type", "string"), required)
            opt = "" if required else "?"
            lines.append(f"  {fname}{opt}: {t};")
        lines.append("}")
        lines.append("")
        return "\n".join(lines)

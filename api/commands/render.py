from __future__ import annotations

import base64
import json

from jinja2 import Environment, BaseLoader, select_autoescape

from models import CommandRequest, CommandResponse
from protocols import get_registry
from . import Command


_DEFAULT_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{{ title or 'View' }}</title>
  <style>
    body{font-family:system-ui,sans-serif;max-width:880px;margin:2rem auto;padding:0 1rem;color:#222}
    table{border-collapse:collapse;width:100%}
    th,td{border:1px solid #ddd;padding:.4rem .6rem;text-align:left}
    th{background:#f5f5f5}
    pre{background:#f5f5f5;padding:.8rem;overflow:auto}
  </style>
</head>
<body>
  <h1>{{ title or 'View' }}</h1>
  {% if data is mapping and 'rows' in data %}
    <table>
      <thead><tr>{% for k in data.fields or (data.rows[0].keys() if data.rows else []) %}<th>{{ k }}</th>{% endfor %}</tr></thead>
      <tbody>
        {% for r in data.rows %}
          <tr>{% for k in data.fields or r.keys() %}<td>{{ r[k] }}</td>{% endfor %}</tr>
        {% endfor %}
      </tbody>
    </table>
  {% elif data is sequence and data and (data[0] is mapping) %}
    <table>
      <thead><tr>{% for k in data[0].keys() %}<th>{{ k }}</th>{% endfor %}</tr></thead>
      <tbody>
        {% for r in data %}<tr>{% for k in data[0].keys() %}<td>{{ r[k] }}</td>{% endfor %}</tr>{% endfor %}
      </tbody>
    </table>
  {% else %}
    <pre>{{ data | tojson(indent=2) }}</pre>
  {% endif %}
</body>
</html>
"""


class RenderCommand(Command):
    name = "render"
    description = (
        "Render a Jinja2 template into HTML. Template source can come from "
        "meta.template (inline string) or template_uri (fetched). Data comes "
        "from input_uri (JSON) or meta.data."
    )
    input_hint = {
        "input_uri": "optional - JSON data source",
        "meta.template_uri": "optional - URI of a Jinja2 template",
        "meta.template": "optional - inline Jinja2 template string",
        "meta.title": "optional page title",
        "meta.data": "inline data (used if input_uri not given)",
    }

    async def execute(self, request: CommandRequest) -> CommandResponse:
        meta = request.meta or {}
        # Resolve template
        template_src = meta.get("template")
        if not template_src and meta.get("template_uri"):
            t = await get_registry().fetch(meta["template_uri"])
            template_src = t.content.decode("utf-8")
        if not template_src:
            template_src = _DEFAULT_TEMPLATE

        # Resolve data
        if request.input_uri:
            d = await get_registry().fetch(request.input_uri)
            data = json.loads(d.content.decode("utf-8"))
        else:
            data = meta.get("data", {})

        env = Environment(loader=BaseLoader(), autoescape=select_autoescape(["html", "xml"]))
        template = env.from_string(template_src)
        html = template.render(data=data, title=meta.get("title", "View"), meta=meta)

        payload_bytes = html.encode("utf-8")
        return CommandResponse(
            payload_b64=base64.b64encode(payload_bytes).decode("ascii"),
            mime="text/html",
            meta={
                "source_uri": request.input_uri,
                "template_uri": meta.get("template_uri"),
                "bytes": len(payload_bytes),
            },
        )

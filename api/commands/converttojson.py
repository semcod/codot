from __future__ import annotations

import base64
import csv
import io
import json

from models import CommandRequest, CommandResponse
from protocols import get_registry
from validators import validate_against_schema_uri, SchemaValidationError
from . import Command


class ConvertToJsonCommand(Command):
    name = "converttojson"
    description = (
        "Fetch a resource by URI and convert it to JSON. "
        "Supports CSV, plain text, already-JSON content, and XML. "
        "If schema_uri is provided the resulting JSON is validated against it."
    )
    input_hint = {
        "input_uri": "URI of source data (csv/text/json/xml)",
        "schema_uri": "optional JSON Schema URI for result validation",
        "meta.mode": "'lines' | 'csv' | 'xml' | 'json' | 'auto' (default: auto)",
    }

    async def execute(self, request: CommandRequest) -> CommandResponse:
        if not request.input_uri:
            raise ValueError("converttojson requires input_uri")

        fetched = await get_registry().fetch(request.input_uri)
        mode = (request.meta or {}).get("mode", "auto")
        mime = (fetched.mime or "").split(";")[0].strip().lower()
        text = fetched.content.decode("utf-8", errors="replace")

        if mode == "auto":
            if "csv" in mime or request.input_uri.endswith(".csv"):
                mode = "csv"
            elif "json" in mime or request.input_uri.endswith(".json"):
                mode = "json"
            elif "xml" in mime or request.input_uri.endswith(".xml"):
                mode = "xml"
            else:
                mode = "lines"

        result: dict | list
        if mode == "lines":
            result = {
                "lines": [ln for ln in text.splitlines() if ln.strip()],
            }
        elif mode == "csv":
            reader = csv.DictReader(io.StringIO(text))
            result = {"rows": list(reader), "fields": reader.fieldnames or []}
        elif mode == "json":
            result = json.loads(text)
        elif mode == "xml":
            import xmltodict
            result = xmltodict.parse(text)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        # optional schema validation on the produced JSON
        if request.schema_uri:
            try:
                await validate_against_schema_uri(result, request.schema_uri)
            except SchemaValidationError as e:
                raise ValueError(f"Schema validation failed: {e}; {e.errors}")

        payload_bytes = json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")
        return CommandResponse(
            payload_b64=base64.b64encode(payload_bytes).decode("ascii"),
            mime="application/json",
            meta={
                "source_uri": request.input_uri,
                "source_mime": fetched.mime,
                "mode": mode,
                "bytes": len(payload_bytes),
            },
        )

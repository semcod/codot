from __future__ import annotations

import base64
import csv
import io
import json

import xmltodict

from models import CommandRequest, CommandResponse
from protocols import get_registry
from . import Command


class ConvertToXmlCommand(Command):
    name = "converttoxml"
    description = "Fetch a resource (JSON/CSV/text) and convert it to XML."
    input_hint = {
        "input_uri": "URI of source data",
        "meta.root": "root element name (default: 'root')",
    }

    async def execute(self, request: CommandRequest) -> CommandResponse:
        if not request.input_uri:
            raise ValueError("converttoxml requires input_uri")

        fetched = await get_registry().fetch(request.input_uri)
        root = (request.meta or {}).get("root", "root")
        mime = (fetched.mime or "").split(";")[0].strip().lower()
        text = fetched.content.decode("utf-8", errors="replace")

        if "json" in mime or request.input_uri.endswith(".json"):
            data = json.loads(text)
        elif "csv" in mime or request.input_uri.endswith(".csv"):
            reader = csv.DictReader(io.StringIO(text))
            data = {"row": list(reader)}
        else:
            data = {"text": text}

        # xmltodict.unparse rejects top-level lists ("document with multiple
        # roots"). Wrap a bare list so the items become repeated <item> tags.
        if isinstance(data, list):
            data = {"item": data}

        xml = xmltodict.unparse({root: data}, pretty=True)
        payload_bytes = xml.encode("utf-8")
        return CommandResponse(
            payload_b64=base64.b64encode(payload_bytes).decode("ascii"),
            mime="application/xml",
            meta={
                "source_uri": request.input_uri,
                "root": root,
                "bytes": len(payload_bytes),
            },
        )

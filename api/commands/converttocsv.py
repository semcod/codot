from __future__ import annotations

import base64
import csv
import io
import json

from models import CommandRequest, CommandResponse
from protocols import get_registry
from . import Command


class ConvertToCsvCommand(Command):
    name = "converttocsv"
    description = "Fetch a JSON resource (list of objects) and emit CSV."
    input_hint = {
        "input_uri": "URI pointing to JSON list-of-objects",
        "meta.columns": "optional list of column names to include (default: union of keys)",
    }

    async def execute(self, request: CommandRequest) -> CommandResponse:
        if not request.input_uri:
            raise ValueError("converttocsv requires input_uri")

        fetched = await get_registry().fetch(request.input_uri)
        data = json.loads(fetched.content.decode("utf-8"))

        if isinstance(data, dict) and "rows" in data:
            rows = data["rows"]
        elif isinstance(data, list):
            rows = data
        else:
            raise ValueError("Source JSON must be a list of objects or {rows: [...]}")

        if not rows:
            columns: list[str] = []
        else:
            requested = (request.meta or {}).get("columns")
            if requested:
                columns = list(requested)
            else:
                seen: list[str] = []
                for r in rows:
                    for k in r.keys():
                        if k not in seen:
                            seen.append(k)
                columns = seen

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in columns})

        payload_bytes = buf.getvalue().encode("utf-8")
        return CommandResponse(
            payload_b64=base64.b64encode(payload_bytes).decode("ascii"),
            mime="text/csv",
            meta={
                "source_uri": request.input_uri,
                "rows": len(rows),
                "columns": columns,
            },
        )

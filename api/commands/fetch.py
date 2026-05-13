from __future__ import annotations

import base64

from models import CommandRequest, CommandResponse
from protocols import get_registry
from . import Command


class FetchCommand(Command):
    name = "fetch"
    description = (
        "Fetch a resource from any supported protocol and return its raw bytes."
    )
    input_hint = {"input_uri": "http://... | https://... | file:///data/... | data:..."}

    async def execute(self, request: CommandRequest) -> CommandResponse:
        if not request.input_uri:
            raise ValueError("fetch requires input_uri")
        result = await get_registry().fetch(request.input_uri)
        return CommandResponse(
            payload_b64=base64.b64encode(result.content).decode("ascii"),
            mime=result.mime,
            meta={
                "source_uri": result.source_uri,
                "size": len(result.content),
                **result.extra,
            },
        )

from __future__ import annotations

import base64

from models import CommandRequest, CommandResponse
from protocols import get_registry
from . import Command


class ConvertToBase64Command(Command):
    name = "converttobase64"
    description = "Fetch a resource and return it base64-encoded (useful for binaries like PDFs or images)."
    input_hint = {"input_uri": "URI of the resource to encode"}

    async def execute(self, request: CommandRequest) -> CommandResponse:
        if not request.input_uri:
            raise ValueError("converttobase64 requires input_uri")

        fetched = await get_registry().fetch(request.input_uri)
        encoded = base64.b64encode(fetched.content).decode("ascii")
        # We return the base64 string *as a text payload* so callers can read it
        # without having to decode a base64-wrapped base64. The bytes here are
        # the ASCII of the base64 text.
        payload_bytes = encoded.encode("ascii")
        return CommandResponse(
            payload_b64=base64.b64encode(payload_bytes).decode("ascii"),
            mime="text/plain",
            meta={
                "source_uri": request.input_uri,
                "original_mime": fetched.mime,
                "original_size": len(fetched.content),
                "encoding": "base64",
            },
        )

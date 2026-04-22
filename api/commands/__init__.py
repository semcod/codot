"""Command registry.

Each Command is a self-contained unit with:
- a unique name (URL segment: PUT /commands/<name>)
- optional metadata describing its schema
- an execute() coroutine that returns a CommandResponse

Adding a new command means: (1) write a class, (2) register it at import time.
No proto regeneration, no DTOs, nothing else changes.
"""
from __future__ import annotations

import abc
from typing import Any

from models import CommandRequest, CommandResponse


class Command(abc.ABC):
    name: str = ""
    description: str = ""
    # Human-readable hint about what meta/input_uri should look like
    input_hint: dict[str, Any] = {}

    @abc.abstractmethod
    async def execute(self, request: CommandRequest) -> CommandResponse: ...


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        if not command.name:
            raise ValueError("Command must have a name")
        self._commands[command.name] = command

    def get(self, name: str) -> Command:
        if name not in self._commands:
            raise KeyError(f"Unknown command: {name}")
        return self._commands[name]

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": c.name,
                "description": c.description,
                "input_hint": c.input_hint,
            }
            for c in self._commands.values()
        ]


_registry = CommandRegistry()


def get_registry() -> CommandRegistry:
    return _registry


def register_default_commands() -> None:
    from .fetch import FetchCommand
    from .converttojson import ConvertToJsonCommand
    from .converttoxml import ConvertToXmlCommand
    from .converttobase64 import ConvertToBase64Command
    from .converttocsv import ConvertToCsvCommand
    from .render import RenderCommand
    from .pipeline import PipelineCommand

    reg = get_registry()
    reg.register(FetchCommand())
    reg.register(ConvertToJsonCommand())
    reg.register(ConvertToXmlCommand())
    reg.register(ConvertToBase64Command())
    reg.register(ConvertToCsvCommand())
    reg.register(RenderCommand())
    reg.register(PipelineCommand())


register_default_commands()

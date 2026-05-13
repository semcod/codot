"""Dynamic schema validation - schema fetched at runtime from a URI."""

from __future__ import annotations

import json
import logging
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

from protocols import get_registry

logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    def __init__(self, message: str, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors


async def _fetch_schema(schema_uri: str) -> dict:
    try:
        result = await get_registry().fetch(schema_uri)
    except Exception as e:
        raise SchemaValidationError(
            f"Failed to fetch schema from {schema_uri}: {e}", []
        ) from e
    try:
        return json.loads(result.content.decode("utf-8"))
    except Exception as e:
        raise SchemaValidationError(f"Schema is not valid JSON: {e}", []) from e


def _format_validation_errors(errors: list[ValidationError]) -> list[str]:
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in errors
    ]


async def validate_against_schema_uri(instance: Any, schema_uri: str) -> None:
    """Fetch a JSON Schema from the given URI and validate the instance.

    The URI is resolved via the protocol registry, so it can live on HTTP,
    in a local file, or inline as data:.
    """
    schema = await _fetch_schema(schema_uri)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        messages = _format_validation_errors(errors)
        raise SchemaValidationError(
            f"Instance does not match schema {schema_uri}", messages
        )

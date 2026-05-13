"""Cross-target type mapping.

Contract JSON uses a small set of type names: string, integer, boolean,
object, array, datetime. Each generator maps these to its own target.
"""

from __future__ import annotations


PYTHON_TYPES = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "object": "dict[str, Any]",
    "array": "list[Any]",
    "datetime": "datetime",
}

TYPESCRIPT_TYPES = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "object": "Record<string, unknown>",
    "array": "unknown[]",
    "datetime": "string",
}

OPENAPI_TYPES = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "number": {"type": "number"},
    "boolean": {"type": "boolean"},
    "object": {"type": "object"},
    "array": {"type": "array", "items": {}},
    "datetime": {"type": "string", "format": "date-time"},
}


def _map_type(
    t: str, mapping: dict[str, str], fallback: str, none_suffix: str, required: bool
) -> str:
    base = mapping.get(t, fallback)
    return base if required else f"{base} | {none_suffix}"


def py_type(t: str, required: bool = True) -> str:
    return _map_type(t, PYTHON_TYPES, "Any", "None", required)


def ts_type(t: str, required: bool = True) -> str:
    return _map_type(t, TYPESCRIPT_TYPES, "unknown", "null", required)


def openapi_type(t: str, fmt: str | None = None) -> dict:
    spec = dict(OPENAPI_TYPES.get(t, {"type": "string"}))
    if fmt:
        spec["format"] = fmt
    return spec

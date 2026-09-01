"""Mock API used for local bundle development."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI

mock_app = FastAPI(title="Godot Mock API", version="1.0.0")


@mock_app.get("/health")
async def mock_health() -> dict[str, Any]:
    return {"status": "ok", "service": "mock-api"}


@mock_app.get("/api/v1/devices")
async def mock_devices() -> dict[str, Any]:
    return {
        "items": [
            {"id": "device-1", "name": "temperature-sensor", "status": "online"},
            {"id": "device-2", "name": "humidity-sensor", "status": "offline"},
            {"id": "device-3", "name": "pressure-sensor", "status": "online"},
        ]
    }


@mock_app.get("/api/v1/protocols/{protocol_id}")
async def mock_protocol(protocol_id: str) -> dict[str, Any]:
    return {
        "protocol_id": protocol_id,
        "status": "active",
        "owner": "ops",
        "devices": ["device-1", "device-2"],
    }


@mock_app.get("/api/v1/posts")
async def mock_posts() -> dict[str, Any]:
    return {
        "items": [
            {"id": 1, "title": "Hello from Godot", "body": "mock post payload"},
            {"id": 2, "title": "Second post", "body": "more generated data"},
        ]
    }


@mock_app.get("/api/v1/catalog")
async def mock_catalog() -> dict[str, Any]:
    return {
        "service": "mock-api",
        "endpoints": [
            "/health",
            "/api/v1/devices",
            "/api/v1/protocols/{protocol_id}",
            "/api/v1/posts",
        ],
    }

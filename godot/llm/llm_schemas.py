"""Request models and shared application state."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field

from llm_acl import ACLPolicy
from llm_settings import Settings

BundleKind = Literal[
    "SERVICE_BUNDLE",
    "VIEW_BUNDLE",
    "WORKFLOW_BUNDLE",
    "APPLICATION_BUNDLE",
]
TargetKind = Literal["desktop", "mobile", "web", "pwa", "service", "cli"]


class FetchRequest(BaseModel):
    uri: str
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None


class FetchManyRequest(BaseModel):
    uris: list[str] = Field(default_factory=list)


class GenerateBundleRequest(BaseModel):
    prompt: str
    bundle_name: str | None = None
    bundle_kind: BundleKind | None = None
    targets: list[TargetKind] = Field(default_factory=list)
    source_uris: list[str] = Field(default_factory=list)
    runner: str | None = None
    output_format: str | None = None
    write_file: bool = True
    include_context: bool = False


@dataclass(frozen=True)
class AppState:
    settings: Settings
    acl: ACLPolicy
    validator: Draft202012Validator


def build_state() -> AppState:
    settings = Settings()
    schema = json.loads(settings.schema_file.read_text())
    validator = Draft202012Validator(schema)
    acl = ACLPolicy.from_file(settings.acl_file)
    return AppState(settings=settings, acl=acl, validator=validator)


STATE = build_state()

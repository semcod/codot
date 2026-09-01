"""Runtime settings for the Godot LLM bundle service."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from llm_paths import DEFAULT_ACL_FILE, DEFAULT_OUTPUT_DIR, DEFAULT_SCHEMA_FILE
from llm_util import env_bool, env_float, env_int


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("LLM_MODEL", "openrouter/qwen/qwen3-coder-next")
    api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    api_base: str = os.getenv("LLM_API_BASE", "")
    offline: bool = env_bool("LLM_OFFLINE", True)
    schema_file: Path = Path(os.getenv("BUNDLE_SCHEMA_FILE", str(DEFAULT_SCHEMA_FILE)))
    schema_uri: str = os.getenv("BUNDLE_SCHEMA_URI", "file:///app/bundle.schema.json")
    output_dir: Path = Path(os.getenv("BUNDLE_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR)))
    acl_file: Path = Path(os.getenv("LLM_ACL_FILE", str(DEFAULT_ACL_FILE)))
    fetch_timeout_sec: float = env_float("LLM_FETCH_TIMEOUT_SEC", 10.0)
    max_fetch_bytes: int = env_int("LLM_MAX_FETCH_BYTES", 2_000_000)
    default_runner: str = os.getenv("LLM_DEFAULT_RUNNER", "go_temporal")
    default_runtime_lang: str = os.getenv("LLM_DEFAULT_RUNTIME_LANG", "go")
    default_application_targets: list[str] = field(
        default_factory=lambda: ["web", "pwa"]
    )

"""Filesystem paths for the Godot LLM bundle service."""
from __future__ import annotations

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT
DEFAULT_SCHEMA_FILE = REPO_ROOT / "bundle.schema.json"
DEFAULT_ACL_FILE = APP_ROOT / "acl.yaml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "bundles" / "generated"

#!/usr/bin/env python3
"""Convert Godot Bundle JSON -> DOQL app.doql.css

Usage:
    python3 scripts/bundle-to-doql.py bundles/weather-europe-view.json > build/doql/app.doql.css
"""

import json
import sys
from pathlib import Path


def bundle_to_doql(bundle_path: str) -> str:
    with open(bundle_path) as f:
        b = json.load(f)

    name = b["bundle"]
    kind = b["kind"]
    desc = b.get("description", name)
    sources = b.get("sources", [])
    output = b.get("output", {})
    runtime = output.get("runtime", {})
    port = runtime.get("port", 8080)
    lang = runtime.get("lang", "python")
    targets = b.get("targets", [])

    # Map bundle kind -> DOQL target
    kind_target_map = {
        "SERVICE_BUNDLE": "api",
        "VIEW_BUNDLE": "web",
        "WORKFLOW_BUNDLE": "infra",
        "APPLICATION_BUNDLE": "desktop",
    }
    target = kind_target_map.get(kind, "api")

    # If APPLICATION_BUNDLE has explicit targets, pick first
    if kind == "APPLICATION_BUNDLE" and targets:
        t = targets[0]
        if t in ("web", "pwa"):
            target = "web"
        elif t == "desktop":
            target = "desktop"
        elif t == "mobile":
            target = "mobile"

    lines = []
    lines.append(f"// Auto-generated from Godot Bundle: {name}")
    lines.append(f"// Source: {bundle_path}")
    lines.append("")
    lines.append("app {")
    lines.append(f"  name: {name};")
    lines.append(f"  version: {b.get('version', '1.0.0')};")
    lines.append(f'  description: "{desc}";')
    lines.append("}")
    lines.append("")

    # Interfaces
    lines.append(f'interface[type="{target}"] ' + "{")
    if target == "api":
        lines.append("  type: rest;")
        lines.append("  framework: fastapi;")
    elif target == "web":
        lines.append("  type: spa;")
        lines.append("  framework: react;")
    elif target == "desktop":
        lines.append("  type: desktop;")
        lines.append("  framework: tauri;")
    elif target == "mobile":
        lines.append("  type: mobile;")
        lines.append("  framework: expo;")
    lines.append("}")
    lines.append("")

    # Workflows — one per source
    for src in sources:
        src_name = src["name"]
        uri = src.get("uri", "")
        refresh = src.get("refresh_sec", 60)
        lines.append(f'workflow[name="fetch-{src_name}"] ' + "{")
        lines.append(f"  trigger: interval {refresh}s;")
        lines.append(f'  step-1: run cmd=curl -fsS "{uri}" | tee /tmp/{src_name}.json;')
        lines.append("}")
        lines.append("")

    # Database if storage declared
    storage = b.get("storage")
    if storage:
        lines.append("database {")
        lines.append(f"  driver: {storage};")
        lines.append("}")
        lines.append("")

    # Runtime
    lines.append("runtime {")
    lines.append(f"  port: {port};")
    lines.append(f"  language: {lang};")
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: bundle-to-doql.py <bundle.json>", file=sys.stderr)
        sys.exit(1)
    print(bundle_to_doql(sys.argv[1]))

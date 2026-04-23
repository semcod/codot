#!/usr/bin/env python3
"""Verify that practical bundle descriptions map to correct kinds via LLM inference.

This tests the same infer_* logic used by the LLM service without needing a running server.
Usage:
    python3 scripts/test-practical-bundles.py
"""

import json
import sys
from pathlib import Path


def infer_kind(prompt: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    lower = prompt.lower()
    if any(token in lower for token in ["workflow", "pipeline", "orchestrate", "dag"]):
        return "WORKFLOW_BUNDLE"
    if any(token in lower for token in ["dashboard", "view", "ui", "frontend", "panel", "stream", "live"]):
        return "VIEW_BUNDLE"
    if any(token in lower for token in ["desktop", "mobile", "web", "pwa", "application", "app ", "app\n"]):
        return "APPLICATION_BUNDLE"
    return "SERVICE_BUNDLE"


def infer_targets(prompt: str, explicit: list[str], kind: str) -> list[str]:
    if explicit:
        return list(dict.fromkeys(explicit))
    lower = prompt.lower()
    detected: list[str] = []
    for target in ["desktop", "mobile", "web", "pwa", "service", "cli"]:
        if target in lower:
            detected.append(target)
    if kind == "APPLICATION_BUNDLE" and not detected:
        return ["web", "pwa"]
    return list(dict.fromkeys(detected))


def infer_runner(kind: str, targets: list[str], explicit: str | None = None) -> str:
    if explicit:
        return explicit
    if kind == "APPLICATION_BUNDLE":
        return "go_temporal"
    if kind == "SERVICE_BUNDLE":
        return "python_fastapi"
    if kind == "VIEW_BUNDLE":
        return "go_temporal"
    if kind == "WORKFLOW_BUNDLE":
        return "go_temporal"
    return "go_temporal"


FIXTURES = [
    {
        "file": "bundles/weather-europe-view.json",
        "expected_kind": "VIEW_BUNDLE",
        "expected_runner": "go_temporal",
        "prompt": "Live weather dashboard for Europe with auto refresh",
    },
    {
        "file": "bundles/nbp-currency-service.json",
        "expected_kind": "SERVICE_BUNDLE",
        "expected_runner": "python_fastapi",
        "prompt": "REST service for currency exchange rates from NBP API",
    },
    {
        "file": "bundles/news-aggregator-service.json",
        "expected_kind": "SERVICE_BUNDLE",
        "expected_runner": "python_fastapi",
        "prompt": "RSS feed aggregation service with multiple sources",
    },
    {
        "file": "bundles/news-aggregator-view.json",
        "expected_kind": "VIEW_BUNDLE",
        "expected_runner": "go_temporal",
        "prompt": "Dashboard rendering aggregated news headlines",
    },
    {
        "file": "bundles/internet-data-report.json",
        "expected_kind": "VIEW_BUNDLE",
        "expected_runner": "go_temporal",
        "prompt": "Combined report view from weather and currency data",
    },
    {
        "file": "bundles/combined-weather-news-report.json",
        "expected_kind": "VIEW_BUNDLE",
        "expected_runner": "go_temporal",
        "prompt": "Merged dashboard showing weather and news side by side",
    },
]


def main() -> int:
    base = Path(__file__).parent.parent
    failed = 0

    for fx in FIXTURES:
        path = base / fx["file"]
        with open(path) as f:
            bundle = json.load(f)

        kind = bundle["kind"]
        runner = bundle["runner"]
        targets = bundle.get("targets", [])

        inferred_kind = infer_kind(fx["prompt"])
        inferred_targets = infer_targets(fx["prompt"], targets, inferred_kind)
        inferred_runner = infer_runner(inferred_kind, inferred_targets)

        ok = True
        if inferred_kind != fx["expected_kind"]:
            print(f"✗ {fx['file']}: kind mismatch: got {inferred_kind}, want {fx['expected_kind']}")
            ok = False
        if inferred_runner != fx["expected_runner"]:
            print(f"✗ {fx['file']}: runner mismatch: got {inferred_runner}, want {fx['expected_runner']}")
            ok = False

        if ok:
            print(f"✓ {fx['file']}: {kind} / {runner}")
        else:
            failed += 1

    print("")
    if failed == 0:
        print("=== All practical bundle inference tests passed ===")
        return 0
    else:
        print(f"=== {failed} practical bundle inference test(s) failed ===")
        return 1


if __name__ == "__main__":
    sys.exit(main())

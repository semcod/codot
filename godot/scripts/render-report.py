#!/usr/bin/env python3
"""Render a bundle with output.format=report into a static HTML report.

Usage:
    python3 scripts/render-report.py bundles/internet-data-report.json > generated/report.html
"""

import json
import sys
import urllib.request
from pathlib import Path
from datetime import datetime


CACHE_DIR = Path.home() / ".cache" / "godot-bundle"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(uri: str) -> Path:
    import hashlib

    key = hashlib.sha256(uri.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{key}.json"


def fetch_source(uri: str, ttl_sec: int = 0) -> dict:
    cp = _cache_path(uri)
    if cp.exists() and ttl_sec > 0:
        age = datetime.now().timestamp() - cp.stat().st_mtime
        if age < ttl_sec:
            return json.loads(cp.read_text(encoding="utf-8"))

    try:
        with urllib.request.urlopen(uri, timeout=15) as resp:
            data = resp.read().decode("utf-8")
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                payload = {"raw": data[:2000]}
    except Exception as e:
        payload = {"error": str(e)}

    cp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def render_html(bundle: dict, source_data: dict) -> str:
    title = bundle.get("description", bundle["bundle"])
    now = datetime.now().astimezone().isoformat()

    rows = []
    for name, data in source_data.items():
        rows.append(f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #ddd;font-weight:bold">{name}</td>
          <td style="padding:8px;border-bottom:1px solid #ddd">
            <pre style="margin:0;white-space:pre-wrap;word-break:break-word">{json.dumps(data, indent=2, ensure_ascii=False)[:2000]}</pre>
          </td>
        </tr>
        """)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 40px auto; padding: 20px; }}
    h1 {{ color: #333; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th {{ text-align: left; padding: 8px; border-bottom: 2px solid #333; }}
    tr:hover {{ background: #f5f5f5; }}
    .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
    .badge {{ display:inline-block; padding:2px 8px; border-radius:4px; background:#007acc; color:#fff; font-size:0.8em; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="meta">
    <span class="badge">{bundle["kind"]}</span>
    <span>Bundle: <code>{bundle["bundle"]}</code></span>
    <span> | Generated: {now}</span>
  </div>
  <table>
    <thead>
      <tr><th>Source</th><th>Data</th></tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
  </table>
</body>
</html>"""
    return html


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: render-report.py <bundle.json> [output.html]", file=sys.stderr)
        return 1

    bundle_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None

    with open(bundle_path) as f:
        bundle = json.load(f)

    sources = bundle.get("sources", [])
    source_data = {}
    for src in sources:
        name = src["name"]
        uri = src["uri"]
        ttl = src.get("refresh_sec", 300)
        print(f"Fetching {name} (ttl={ttl}s) ...", file=sys.stderr)
        source_data[name] = fetch_source(uri, ttl)

    html = render_html(bundle, source_data)

    if out_path:
        Path(out_path).write_text(html, encoding="utf-8")
        print(f"Report written to {out_path}")
    else:
        print(html)

    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

from html import escape

from ...ir import AnyBundle, ViewBundle
from ._shared import refresh_to_ms


def _py_string(value: str) -> str:
    return repr(value)


class FastApiSseViewGenerator:
    target = "view/fastapi-sse"
    category = "view"

    def generate(self, bundle: AnyBundle) -> dict[str, str]:
        if not isinstance(bundle, ViewBundle):
            raise TypeError(
                f"{self.target} expects a ViewBundle, got {type(bundle).__name__}"
            )
        return {
            "requirements.txt": self._requirements(),
            "main.py": self._main(bundle),
            "README.md": self._readme(bundle),
        }

    def _requirements(self) -> str:
        return "\n".join(
            [
                "fastapi>=0.115.0",
                "uvicorn[standard]>=0.32.0",
                "httpx>=0.28.0",
                "",
            ]
        )

    def _main(self, bundle: ViewBundle) -> str:
        min_refresh_ms = min(refresh_to_ms(s.refresh) for s in bundle.sources)
        sources_literal = repr(
            [
                {
                    "name": s.name,
                    "uri": s.uri,
                    "method": s.method or "GET",
                    "headers": dict(s.headers),
                    "refresh_ms": refresh_to_ms(s.refresh),
                    "depends_on": list(s.depends_on),
                }
                for s in bundle.sources
            ]
        )
        index_html = "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '  <meta charset="utf-8">',
                f"  <title>{escape(bundle.name)}</title>",
                "  <style>",
                "    :root { color-scheme: light dark; }",
                "    body { font: 14px/1.4 system-ui, sans-serif; margin: 0; padding: 1rem 1.25rem; }",
                "    header { border-bottom: 1px solid #8884; padding-bottom: .5rem; margin-bottom: 1rem; }",
                "    main { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); }",
                "    section { border: 1px solid #8884; border-radius: 6px; padding: .75rem; }",
                "    pre { margin: 0; white-space: pre-wrap; word-break: break-word; max-height: 24rem; overflow: auto; background: #8881; padding: .5rem; border-radius: 4px; }",
                "  </style>",
                "</head>",
                "<body>",
                "  <header>",
                f"    <h1>{escape(bundle.name)} <small>v{escape(bundle.version)}</small></h1>",
                f"    <p>{escape(bundle.description)}</p>",
                "    <small>transport: sse</small>",
                "  </header>",
                '  <main id="content"></main>',
                "  <script>",
                "    function esc(s) { return String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll(\"\\\"\", '&quot;').replaceAll(\"'\", '&#39;'); }",
                "    function render(payload) {",
                '      const root = document.getElementById("content");',
                "      root.innerHTML = Object.entries(payload.sources).map(([name, result]) => {",
                '        const body = result.ok ? JSON.stringify(result.data ?? result.raw, null, 2) : `ERROR: ${result.error || "unknown"}`;',
                "        return `<section><h2>${esc(name)}</h2><pre>${esc(body)}</pre></section>`;",
                '      }).join("");',
                "    }",
                '    const es = new EventSource("/events");',
                '    es.addEventListener("snapshot", (ev) => render(JSON.parse(ev.data)));',
                "  </script>",
                "</body>",
                "</html>",
            ]
        )
        lines = [
            "from __future__ import annotations",
            "",
            "import asyncio",
            "import json",
            "from datetime import datetime, timezone",
            "",
            "import httpx",
            "from fastapi import FastAPI, Request",
            "from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse",
            "",
            f"BUNDLE_NAME = {_py_string(bundle.name)}",
            f"BUNDLE_VERSION = {_py_string(bundle.version)}",
            f"BUNDLE_DESCRIPTION = {_py_string(bundle.description)}",
            f"MIN_REFRESH_MS = {min_refresh_ms}",
            f"SOURCES = {sources_literal}",
            f"INDEX_HTML = {index_html!r}",
            "",
            "app = FastAPI(",
            f"    title={_py_string(bundle.name)},",
            f"    version={_py_string(bundle.version)},",
            f"    description={_py_string(bundle.description)},",
            ")",
            "",
            "async def fetch_source(client: httpx.AsyncClient, src: dict) -> dict:",
            "    try:",
            '        response = await client.request(src["method"], src["uri"], headers=src.get("headers", {}))',
            '        content_type = response.headers.get("content-type", "")',
            '        if "application/json" in content_type:',
            "            payload = response.json()",
            "            raw = None",
            "        else:",
            "            payload = None",
            "            raw = response.text",
            "        if response.is_success:",
            '            return {"ok": True, "status": response.status_code, "data": payload, "raw": raw}',
            '        return {"ok": False, "status": response.status_code, "data": payload, "raw": raw, "error": response.text[:500]}',
            "    except Exception as exc:",
            '        return {"ok": False, "error": str(exc), "uri": src["uri"]}',
            "",
            "async def aggregate_all() -> dict:",
            "    async with httpx.AsyncClient(timeout=10.0) as client:",
            "        results = await asyncio.gather(*[fetch_source(client, src) for src in SOURCES])",
            "    return {",
            '        "timestamp": datetime.now(timezone.utc).isoformat(),',
            '        "sources": {src["name"]: result for src, result in zip(SOURCES, results)},',
            "    }",
            "",
            f"@app.get({_py_string(bundle.exposure.health_path)})",
            "async def health() -> dict:",
            '    return {"status": "ok", "service": BUNDLE_NAME, "version": BUNDLE_VERSION}',
            "",
            '@app.get("/snapshot")',
            "async def snapshot() -> JSONResponse:",
            "    return JSONResponse(await aggregate_all())",
            "",
            '@app.get("/", response_class=HTMLResponse)',
            "async def index() -> HTMLResponse:",
            "    return HTMLResponse(INDEX_HTML)",
            "",
            "async def event_stream(request: Request):",
            "    while True:",
            "        if await request.is_disconnected():",
            "            break",
            "        payload = await aggregate_all()",
            '        yield f"event: snapshot\\ndata: {json.dumps(payload, ensure_ascii=False)}\\n\\n"',
            "        await asyncio.sleep(MIN_REFRESH_MS / 1000)",
            "",
            '@app.get("/events")',
            "async def events(request: Request) -> StreamingResponse:",
            '    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}',
            '    return StreamingResponse(event_stream(request), media_type="text/event-stream", headers=headers)',
            "",
            'if __name__ == "__main__":',
            "    import uvicorn",
            f'    uvicorn.run(app, host="0.0.0.0", port={bundle.exposure.port})',
            "",
        ]
        return "\n".join(lines)

    def _readme(self, bundle: ViewBundle) -> str:
        source_list = "\n".join(
            f"- **{s.name}** — `{s.method} {s.uri}` (refresh: {s.refresh})"
            for s in bundle.sources
        )
        lines = [
            f"# {bundle.name}",
            "",
            bundle.description or "Auto-generated SSE aggregation view.",
            "",
            "Generated by the **view/fastapi-sse** target of Service Factory.",
            f"Bundle hash: `{bundle.contract_hash()}`.",
            "",
            "## Run",
            "",
            "```bash",
            "python3 -m pip install -r requirements.txt",
            "python3 main.py",
            "```",
            "",
            f"The service listens on port `{bundle.exposure.port}` and exposes `/`, `/snapshot`, `/events`, and `{bundle.exposure.health_path}`.",
            "",
            "## Sources",
            "",
            source_list,
            "",
        ]
        return "\n".join(lines)

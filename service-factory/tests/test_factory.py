"""Unit tests — run with `cd service-factory && pytest tests/`."""
from __future__ import annotations

import ast
import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from factory import get_registry, register_default_generators
from factory.ir import Bundle, BundleLoader, Contract, Runtime, Source, ViewBundle


@pytest.fixture(scope="module", autouse=True)
def _register():
    register_default_generators()


@pytest.fixture
def bundle() -> Bundle:
    loader = BundleLoader(ROOT / "contracts")
    return loader.load(ROOT / "bundles" / "connect-test-service.bundle.json")


# ---------- IR -------------------------------------------------------------

def test_bundle_loads_with_contracts(bundle: Bundle):
    assert bundle.name == "connect-test-service"
    assert len(bundle.contracts) == 4
    assert len(bundle.commands) == 2
    assert len(bundle.events) == 2
    assert len(bundle.queries) == 0


def test_hash_is_deterministic(bundle: Bundle):
    h1 = bundle.contract_hash()
    loader = BundleLoader(ROOT / "contracts")
    again = loader.load(ROOT / "bundles" / "connect-test-service.bundle.json")
    assert again.contract_hash() == h1
    assert len(h1) == 16


def test_hash_changes_when_runtime_changes(bundle: Bundle):
    original_hash = bundle.contract_hash()
    bundle.runtime = Runtime(language="node", version="20", framework="fastify")
    assert bundle.contract_hash() != original_hash


def test_contract_accessors():
    raw = {
        "command": "CreateDevice",
        "kind": "CQRS_COMMAND",
        "version": "1.0.0",
        "input": {"name": {"type": "string", "required": True}},
        "output": {"id": {"type": "string"}},
        "transport": {"http": {"method": "POST", "endpoint": "/api/v3/devices"}},
    }
    c = Contract(raw=raw, source_file="x.json")
    assert c.name == "CreateDevice"
    assert c.is_command
    assert not c.is_query
    assert not c.is_event
    assert c.http_method == "POST"
    assert c.http_endpoint == "/api/v3/devices"


def test_missing_contract_raises_clear_error():
    loader = BundleLoader(ROOT / "contracts")
    bad = {
        "bundle": "bad",
        "contracts": ["DoesNotExist.command.json"],
    }
    bad_path = ROOT / "tests" / "_tmp_bad_bundle.json"
    bad_path.write_text(json.dumps(bad))
    try:
        with pytest.raises(FileNotFoundError, match="DoesNotExist"):
            loader.load(bad_path)
    finally:
        bad_path.unlink()


# ---------- Generators: structural checks ----------------------------------

def test_all_generators_registered():
    reg = get_registry()
    targets = {e["target"] for e in reg.list()}
    assert {"python-fastapi", "node-fastify", "docker", "kubernetes", "openapi"} <= targets


def test_python_fastapi_generates_valid_python(bundle: Bundle, tmp_path: Path):
    gen = get_registry().get("python-fastapi")
    files = gen.generate(bundle)
    assert set(files.keys()) == {"requirements.txt", "models.py", "events.py", "main.py"}

    # Each .py file must compile
    import py_compile
    for name in ("models.py", "events.py", "main.py"):
        p = tmp_path / name
        p.write_text(files[name])
        py_compile.compile(str(p), doraise=True)


def test_python_fastapi_routes_match_contracts(bundle: Bundle):
    gen = get_registry().get("python-fastapi")
    main_py = gen.generate(bundle)["main.py"]
    for c in bundle.commands:
        assert c.http_endpoint in main_py, f"missing endpoint {c.http_endpoint}"
        assert c.name in main_py, f"missing class {c.name}"


def test_node_fastify_generates_valid_json(bundle: Bundle):
    gen = get_registry().get("node-fastify")
    files = gen.generate(bundle)
    assert set(files.keys()) == {"package.json", "server.js", "types.d.ts"}
    # package.json must be valid JSON
    json.loads(files["package.json"])


def test_docker_generates_valid_yaml(bundle: Bundle):
    import yaml
    gen = get_registry().get("docker")
    files = gen.generate(bundle)
    assert set(files.keys()) == {"Dockerfile", "docker-compose.yml", ".dockerignore"}
    parsed = yaml.safe_load(files["docker-compose.yml"])
    assert "services" in parsed
    assert bundle.name in parsed["services"]
    # companion and storage made it in
    assert "llm-proxy" in parsed["services"]
    assert "postgres" in parsed["services"]
    # main service has env vars + port + healthcheck-adjacent settings
    main = parsed["services"][bundle.name]
    assert main["ports"] == [f"{bundle.exposure.port}:{bundle.exposure.port}"]
    env = main["environment"]
    assert any("SERVICE_NAME=connect-test-service" in e for e in env)


def test_docker_dockerfile_has_healthcheck(bundle: Bundle):
    gen = get_registry().get("docker")
    dockerfile = gen.generate(bundle)["Dockerfile"]
    assert "HEALTHCHECK" in dockerfile
    assert f"EXPOSE {bundle.exposure.port}" in dockerfile


def test_kubernetes_generates_valid_yaml(bundle: Bundle):
    import yaml
    gen = get_registry().get("kubernetes")
    files = gen.generate(bundle)
    assert set(files.keys()) == {
        "k8s/deployment.yaml",
        "k8s/service.yaml",
        "k8s/kustomization.yaml",
    }
    dep = yaml.safe_load(files["k8s/deployment.yaml"])
    assert dep["kind"] == "Deployment"
    assert dep["metadata"]["labels"]["bundle-hash"] == bundle.contract_hash()
    # resources honored
    container = dep["spec"]["template"]["spec"]["containers"][0]
    assert container["resources"]["limits"]["cpu"] == bundle.resources.cpu


def test_openapi_generates_valid_json(bundle: Bundle):
    gen = get_registry().get("openapi")
    doc = json.loads(gen.generate(bundle)["openapi.json"])
    assert doc["openapi"].startswith("3.")
    assert doc["info"]["title"] == bundle.name
    # every command contract should produce a path entry
    for c in bundle.commands:
        assert c.http_endpoint in doc["paths"]
    # schemas include inputs, outputs, events
    schemas = doc["components"]["schemas"]
    assert "CompleteProtocolInput" in schemas
    assert "CompleteProtocolOutput" in schemas
    assert "DeviceCreatedEvent" in schemas


# ---------- Cross-target consistency --------------------------------------

def test_same_bundle_compiles_to_different_languages(bundle: Bundle):
    """Same IR, two code generators → both produce a valid result."""
    py_files = get_registry().get("python-fastapi").generate(bundle)
    node_files = get_registry().get("node-fastify").generate(bundle)
    # the IR didn't change; both agree on what commands exist
    assert "CompleteProtocol" in py_files["main.py"]
    assert "CompleteProtocol" in node_files["server.js"]


def test_same_bundle_compiles_to_different_infra(bundle: Bundle):
    docker_files = get_registry().get("docker").generate(bundle)
    k8s_files = get_registry().get("kubernetes").generate(bundle)
    assert bundle.name in docker_files["docker-compose.yml"]
    assert bundle.name in k8s_files["k8s/deployment.yaml"]
    # hash appears in both for cache-keying
    assert bundle.contract_hash() in docker_files["docker-compose.yml"]
    assert bundle.contract_hash() in k8s_files["k8s/deployment.yaml"]


# ---------- View Bundle: IR ------------------------------------------------

VIEW_BUNDLE_PATH = ROOT / "bundles" / "device-status-dashboard.view.json"


@pytest.fixture
def view_bundle() -> ViewBundle:
    loader = BundleLoader(ROOT / "contracts")
    b = loader.load(VIEW_BUNDLE_PATH)
    assert isinstance(b, ViewBundle), "loader must return ViewBundle for VIEW_BUNDLE kind"
    return b


def test_view_bundle_loads_with_sources(view_bundle: ViewBundle):
    assert view_bundle.name == "device-status-dashboard"
    assert len(view_bundle.sources) == 2
    assert {s.name for s in view_bundle.sources} == {"catalog", "health"}
    assert view_bundle.transport == "polling"
    assert view_bundle.exposure.port == 8090


def test_view_bundle_hash_is_deterministic(view_bundle: ViewBundle):
    h1 = view_bundle.contract_hash()
    loader = BundleLoader(ROOT / "contracts")
    again = loader.load(VIEW_BUNDLE_PATH)
    assert again.contract_hash() == h1
    assert len(h1) == 16


def test_view_bundle_hash_changes_when_source_changes(view_bundle: ViewBundle):
    original = view_bundle.contract_hash()
    view_bundle.sources = [*view_bundle.sources, Source(name="extra", uri="http://x/")]
    assert view_bundle.contract_hash() != original


def test_view_bundle_rejects_missing_sources(tmp_path: Path):
    bad = {"bundle": "empty-view", "kind": "VIEW_BUNDLE", "sources": []}
    p = tmp_path / "bad.view.json"
    p.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="non-empty list"):
        BundleLoader(tmp_path).load(p)


def test_view_bundle_rejects_unknown_transport(tmp_path: Path):
    bad = {
        "bundle": "weird-view",
        "kind": "VIEW_BUNDLE",
        "sources": [{"name": "a", "uri": "http://x"}],
        "transport": "carrier-pigeon",
    }
    p = tmp_path / "bad.view.json"
    p.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="transport must be one of"):
        BundleLoader(tmp_path).load(p)


def test_service_bundle_still_loads_as_bundle():
    """Regression: adding VIEW_BUNDLE must not break SERVICE_BUNDLE loading."""
    loader = BundleLoader(ROOT / "contracts")
    b = loader.load(ROOT / "bundles" / "connect-test-service.bundle.json")
    assert isinstance(b, Bundle)


# ---------- View Bundle: generator -----------------------------------------

def test_php_standalone_registered():
    reg = get_registry()
    targets = {e["target"] for e in reg.list()}
    assert "view/php-standalone" in targets
    assert {"category": "view", "target": "view/php-standalone"} in reg.list()


def test_php_standalone_rejects_service_bundle(bundle: Bundle):
    gen = get_registry().get("view/php-standalone")
    with pytest.raises(TypeError, match="ViewBundle"):
        gen.generate(bundle)


def test_php_standalone_emits_expected_files(view_bundle: ViewBundle):
    gen = get_registry().get("view/php-standalone")
    files = gen.generate(view_bundle)
    assert set(files.keys()) == {"index.php", "README.md"}
    php = files["index.php"]
    # Every source URI must be reachable from the generated file.
    for s in view_bundle.sources:
        assert s.uri in php, f"source {s.name!r} uri missing from index.php"
    # Aggregator + routing contract
    assert "aggregate_all" in php
    assert "/health" in php
    assert "?format=json" in files["index.php"] or "format" in php
    # Hash is recorded for cache-keying / debugging
    assert view_bundle.contract_hash() in php
    # README spells out how to run it
    readme = files["README.md"]
    assert f"php -S 0.0.0.0:{view_bundle.exposure.port}" in readme


@pytest.mark.skipif(shutil.which("php") is None, reason="php CLI not installed")
def test_php_standalone_passes_php_lint(view_bundle: ViewBundle, tmp_path: Path):
    gen = get_registry().get("view/php-standalone")
    files = gen.generate(view_bundle)
    php_path = tmp_path / "index.php"
    php_path.write_text(files["index.php"])
    result = subprocess.run(
        ["php", "-l", str(php_path)], capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0, (
        f"php -l failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


# ---------- View Bundle: fastapi-sse generator -----------------------------

def test_fastapi_sse_registered():
    reg = get_registry()
    targets = {e["target"] for e in reg.list()}
    assert "view/fastapi-sse" in targets
    assert {"category": "view", "target": "view/fastapi-sse"} in reg.list()


def test_fastapi_sse_rejects_service_bundle(bundle: Bundle):
    gen = get_registry().get("view/fastapi-sse")
    with pytest.raises(TypeError, match="ViewBundle"):
        gen.generate(bundle)


def test_fastapi_sse_emits_expected_files(view_bundle: ViewBundle):
    files = get_registry().get("view/fastapi-sse").generate(view_bundle)
    assert set(files.keys()) == {"requirements.txt", "main.py", "README.md"}
    main_py = files["main.py"]
    assert "StreamingResponse" in main_py
    assert "text/event-stream" in main_py
    assert "@app.get(\"/events\")" in main_py
    assert "@app.get(\"/snapshot\")" in main_py
    for s in view_bundle.sources:
        assert s.uri in main_py
    assert view_bundle.contract_hash() in files["README.md"]


def test_fastapi_sse_generates_valid_python(view_bundle: ViewBundle, tmp_path: Path):
    import py_compile

    files = get_registry().get("view/fastapi-sse").generate(view_bundle)
    for name in ("main.py",):
        p = tmp_path / name
        p.write_text(files[name])
        py_compile.compile(str(p), doraise=True)


def test_fastapi_sse_readme_mentions_events(view_bundle: ViewBundle):
    readme = get_registry().get("view/fastapi-sse").generate(view_bundle)["README.md"]
    assert "/events" in readme
    assert "/snapshot" in readme
    assert f"port `{view_bundle.exposure.port}`" in readme


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_fastapi_sse_inline_js_is_valid(view_bundle: ViewBundle, tmp_path: Path):
    import re as _re

    main_py = get_registry().get("view/fastapi-sse").generate(view_bundle)["main.py"]
    m = _re.search(r"INDEX_HTML = ('.*?')\n\napp = FastAPI\(", main_py, _re.DOTALL)
    assert m, "generated main.py has no INDEX_HTML literal"
    html_doc = ast.literal_eval(m.group(1))
    s = _re.search(r"<script>(.*?)</script>", html_doc, _re.DOTALL)
    assert s, "generated INDEX_HTML has no <script> block"
    js_path = tmp_path / "inline.mjs"
    js_path.write_text(s.group(1))
    result = subprocess.run(
        ["node", "--check", str(js_path)], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, (
        f"node --check failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def _python_has(*modules: str) -> bool:
    import importlib.util

    return all(importlib.util.find_spec(m) is not None for m in modules)


@pytest.mark.skipif(not _python_has("fastapi", "uvicorn", "httpx"), reason="FastAPI runtime deps not installed")
def test_fastapi_sse_runtime_emits_snapshot_events(tmp_path: Path):
    import textwrap

    stub_port = _pick_free_port()
    view_port = _pick_free_port()

    stub_code = textwrap.dedent(
        f"""
        from http.server import BaseHTTPRequestHandler, HTTPServer
        import json

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/catalog':
                    body = json.dumps({{"items": [{{"id": 1, "name": "demo"}}]}}).encode('utf-8')
                elif self.path == '/health':
                    body = json.dumps({{"status": "ok", "upstream": True}}).encode('utf-8')
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args, **kwargs):
                return

        HTTPServer(('127.0.0.1', {stub_port}), Handler).serve_forever()
        """
    )
    stub_proc = subprocess.Popen(
        [sys.executable, "-c", stub_code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_for_http(f"http://127.0.0.1:{stub_port}/health", timeout=5.0)

        runtime_bundle = ViewBundle(
            name="runtime-sse-view",
            version="1.0.0",
            description="runtime test",
            sources=[
                Source(name="catalog", uri=f"http://127.0.0.1:{stub_port}/catalog", refresh="200ms"),
                Source(name="health", uri=f"http://127.0.0.1:{stub_port}/health", refresh="200ms"),
            ],
            transport="sse",
        )
        runtime_bundle.exposure.port = view_port

        files = get_registry().get("view/fastapi-sse").generate(runtime_bundle)
        for name, content in files.items():
            (tmp_path / name).write_text(content)

        view_proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=tmp_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            _wait_for_http(f"http://127.0.0.1:{view_port}/health", timeout=8.0)

            with urllib.request.urlopen(f"http://127.0.0.1:{view_port}/snapshot", timeout=3.0) as resp:
                snapshot = json.loads(resp.read().decode("utf-8"))
            assert set(snapshot["sources"].keys()) == {"catalog", "health"}
            assert snapshot["sources"]["catalog"]["ok"] is True
            assert snapshot["sources"]["health"]["ok"] is True

            with urllib.request.urlopen(f"http://127.0.0.1:{view_port}/events", timeout=5.0) as resp:
                event_line = resp.readline().decode("utf-8").strip()
                data_line = resp.readline().decode("utf-8").strip()
            assert event_line == "event: snapshot"
            assert data_line.startswith("data: ")
            payload = json.loads(data_line[len("data: "):])
            assert set(payload["sources"].keys()) == {"catalog", "health"}
            assert payload["sources"]["catalog"]["ok"] is True
        finally:
            view_proc.terminate()
            try:
                view_proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                view_proc.kill()
    finally:
        stub_proc.terminate()
        try:
            stub_proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            stub_proc.kill()


def _pick_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_http(url: str, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, ConnectionResetError, OSError) as e:
            last_err = e
            time.sleep(0.1)
    raise TimeoutError(f"{url} never became ready ({last_err})")


# ---------- View Bundle: static-html generator ----------------------------

def test_static_html_registered():
    reg = get_registry()
    targets = {e["target"] for e in reg.list()}
    assert "view/static-html" in targets
    assert {"category": "view", "target": "view/static-html"} in reg.list()


def test_static_html_rejects_service_bundle(bundle: Bundle):
    gen = get_registry().get("view/static-html")
    with pytest.raises(TypeError, match="ViewBundle"):
        gen.generate(bundle)


def test_static_html_emits_expected_files(view_bundle: ViewBundle):
    gen = get_registry().get("view/static-html")
    files = gen.generate(view_bundle)
    assert set(files.keys()) == {"index.html", "README.md"}


def test_static_html_embeds_every_source_uri(view_bundle: ViewBundle):
    html_doc = get_registry().get("view/static-html").generate(view_bundle)["index.html"]
    for s in view_bundle.sources:
        assert s.uri in html_doc, f"source {s.name!r} uri missing from index.html"
        # refreshMs must surface for every source (per-source polling contract)
        assert s.name in html_doc
    # hash is embedded as a meta tag for cache-busting / debugging
    assert f'content="{view_bundle.contract_hash()}"' in html_doc


def test_static_html_parses_as_valid_html(view_bundle: ViewBundle):
    """Parse the generated document with html.parser and assert structure."""
    from html.parser import HTMLParser

    html_doc = get_registry().get("view/static-html").generate(view_bundle)["index.html"]

    class Collector(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.tags: list[str] = []
            self.script_bodies: list[str] = []
            self._in_script = False

        def handle_starttag(self, tag, attrs):
            self.tags.append(tag)
            if tag == "script":
                self._in_script = True

        def handle_endtag(self, tag):
            if tag == "script":
                self._in_script = False

        def handle_data(self, data):
            if self._in_script and data.strip():
                self.script_bodies.append(data)

    parser = Collector()
    parser.feed(html_doc)
    # doctype + structural tags present
    assert "html" in parser.tags
    assert "head" in parser.tags
    assert "body" in parser.tags
    assert "main" in parser.tags
    # one <section> per source
    assert parser.tags.count("section") == len(view_bundle.sources)
    # inline script carries the SOURCES literal
    assert any("SOURCES" in b for b in parser.script_bodies)
    assert any("fetchOnce" in b for b in parser.script_bodies)


def test_static_html_readme_mentions_cors_and_serve(view_bundle: ViewBundle):
    readme = get_registry().get("view/static-html").generate(view_bundle)["README.md"]
    port = view_bundle.exposure.port
    assert f"python3 -m http.server {port}" in readme
    assert "CORS" in readme
    assert "file://" in readme


def test_static_html_script_is_syntactically_valid(view_bundle: ViewBundle):
    """Best-effort syntax check: the embedded JSON literal must parse as JSON,
    and every source name from the bundle must appear in the SOURCES array."""
    html_doc = get_registry().get("view/static-html").generate(view_bundle)["index.html"]
    start = html_doc.index("const SOURCES = ") + len("const SOURCES = ")
    end = html_doc.index(";", start)
    raw = html_doc[start:end].strip()
    data = json.loads(raw)
    assert isinstance(data, list) and len(data) == len(view_bundle.sources)
    got_names = {s["name"] for s in data}
    want_names = {s.name for s in view_bundle.sources}
    assert got_names == want_names


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_static_html_inline_js_is_valid(view_bundle: ViewBundle, tmp_path: Path):
    """Extract the single <script> block and run `node --check` on it."""
    import re as _re
    html_doc = get_registry().get("view/static-html").generate(view_bundle)["index.html"]
    m = _re.search(r"<script>(.*?)</script>", html_doc, _re.DOTALL)
    assert m, "generated HTML has no <script> block"
    js_path = tmp_path / "inline.mjs"
    js_path.write_text(m.group(1))
    result = subprocess.run(
        ["node", "--check", str(js_path)], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, (
        f"node --check failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def test_view_bundle_compiles_to_multiple_targets(view_bundle: ViewBundle):
    """Same IR, two view generators → both produce a valid artefact set."""
    php_files = get_registry().get("view/php-standalone").generate(view_bundle)
    html_files = get_registry().get("view/static-html").generate(view_bundle)
    # Each uses its own canonical filename
    assert "index.php" in php_files and "index.html" in html_files
    # The bundle hash is identical across generators — it is a property of the IR
    # not the target.
    assert view_bundle.contract_hash() in php_files["index.php"]
    assert view_bundle.contract_hash() in html_files["index.html"]


@pytest.mark.skipif(shutil.which("php") is None, reason="php CLI not installed")
def test_php_standalone_health_endpoint_runs(view_bundle: ViewBundle, tmp_path: Path):
    gen = get_registry().get("view/php-standalone")
    files = gen.generate(view_bundle)
    (tmp_path / "index.php").write_text(files["index.php"])

    port = _pick_free_port()
    proc = subprocess.Popen(
        ["php", "-S", f"127.0.0.1:{port}", "index.php"],
        cwd=tmp_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_http(f"http://127.0.0.1:{port}/health", timeout=5.0)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2.0) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        assert body == {
            "status": "ok",
            "service": view_bundle.name,
            "version": view_bundle.version,
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()

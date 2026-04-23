"""Unit tests — run with `cd service-factory && pytest tests/`."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from factory import get_registry, register_default_generators
from factory.ir import Bundle, BundleLoader, Contract, Runtime


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

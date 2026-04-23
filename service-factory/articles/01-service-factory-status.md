---
title: "Service Factory — compiling CQRS contracts into runnable services"
status: publish
categories: [Architecture, Projects]
tags: [cqrs, codegen, docker, kubernetes, openapi]
author: Softreck
date: 2026-04-22
---

## What this project is

The **Service Factory** takes a Service Bundle — a JSON document that aggregates existing CQRS contracts (`*.command.json`, `*.query.json`, `*.event.json`) plus a small number of runtime and infrastructure decisions — and compiles it into a deployable service across three independent axes: **code** (Python/FastAPI or Node/Fastify), **infrastructure** (Docker Compose or Kubernetes manifests), and **wire format** (OpenAPI, and soon AsyncAPI and Proto).

The same bundle compiles to any combination. Swap `--targets python-fastapi,docker,openapi` for `--targets node-fastify,kubernetes` and you get a completely different stack implementing the same contracts, without changing the bundle itself. That's the headline: **the bundle is the IR**, generators are pure functions over it, and nothing in the system encodes the language choice or the infrastructure choice anywhere except in the bundle itself.

## Status — April 2026

All 15 unit tests pass, and the end-to-end CLI compile completes in well under a second for the demo bundle. What's shipped:

- **IR layer** — `Bundle`, `Contract`, `BundleLoader`, stable 16-hex hash over the canonical form of the bundle's inputs. Two bundles with identical input produce identical hashes, which is the primitive the future runtime layer needs for image caching.
- **Five generators across three axes**: `python-fastapi` and `node-fastify` (code), `docker` and `kubernetes` (infra), `openapi` (wire).
- **CLI** with `compile`, `list`, and `hash` subcommands.
- **Two example bundles**, both using real CQRS contracts lifted from the existing ecosystem (`CompleteProtocol`, `DemoLogin`, `DeviceCreated`, `DeviceUpdated`) — one targeting Python+Postgres+LiteLLM+Docker, one targeting Node with no storage on k8s.
- **Tests** that verify: hashes are deterministic, generated Python actually compiles (via `py_compile`), generated docker-compose and k8s YAML parses (via `yaml.safe_load`), generated OpenAPI JSON is structurally valid, and the same bundle produces consistent output across language and infra targets.

What's not yet in:

- **Runtime module** — this factory emits artifacts; it does not run them. The next module, which consumes the artifacts and manages lifecycle (TTL, scale-to-zero, hash-keyed image cache), is the subject of a separate project kickoff.
- **More generators** — Go/Chi, Rust/Actix, AsyncAPI (for events/WS), Proto (for gRPC). Each is a single file following the pattern already established; we're holding off until a real use case asks for them.
- **Business logic wiring.** Generated handlers are stubs that raise HTTP 501. The contracts already declare `layers.handler` pointing at the real implementation; we haven't decided yet whether the factory should try to import those or leave the integration to the deployment step.

## What we learned

Three non-obvious things worth documenting:

1. **Your existing contracts are already an IR.** When we first sketched this module, the instinct was to define a new "service description format". It took reading through the existing `contracts/` directory to realise every field we'd need is already there — HTTP transport, input/output schemas, events, storage mapping. All that was missing was a way to group contracts into a deployable unit, and that's just a bundle.json with a list of filenames. The moment we stopped treating bundle.json as "another DSL" and started treating it as "a small configuration header over existing contracts", the architecture got substantially smaller.

2. **Pure functions are the right shape for generators.** Every generator is a method on a class with exactly one behaviour: `generate(bundle) -> {path: content}`. No I/O, no global state, no ordering requirements, no dependencies on other generators. Consequence: the Docker generator doesn't know Python exists. The Python generator doesn't know about k8s. Adding Go tomorrow doesn't touch any existing file except `__init__.py`. This is the same lesson as the Protocol Registry in the main platform — decoupling pays disproportionately whenever there's a registry involved.

3. **Avoid `dedent(f""")` with interpolated multi-line values.** This bit us three times while building the generators. If an f-string has a triple-quoted block with common indentation, and one of the interpolations is a multi-line string that doesn't match that indentation, `textwrap.dedent` gets confused about the common prefix and strips nothing. The fix is to build file output as a flat `list[str]` of already-unindented lines and `"\n".join` at the end. Less clever, more robust. Every generator now follows this pattern.

## Risks

The main risk is **generator drift** — two generators producing inconsistent views of the same bundle. Today the tests catch obvious cases (both the Python and Node generators mention every command name; both Docker and k8s include the bundle hash). We don't have contract tests that say "the OpenAPI routes exactly match the FastAPI routes". For now that's acceptable because all generators read the same Contract accessor methods, so they can't disagree unless the accessors are wrong. If we add a generator that bypasses those accessors for any reason, we'll need cross-generator consistency tests.

A secondary risk: **bundle format evolution**. Right now we tolerate unknown fields silently (they just don't influence anything). If we add a required field later, older bundles will break. The right move before this hits real deployments is to version the bundle format (`"kind": "SERVICE_BUNDLE", "spec_version": "1"`) and write migrators.

## How you extend it

Adding a Go generator tomorrow looks like this:

```python
class GoChiGenerator:
    target = "go-chi"
    category = "code"

    def generate(self, bundle: Bundle) -> dict[str, str]:
        return {"main.go": self._main(bundle), "go.mod": self._gomod(bundle)}
```

Register it in `factory/__init__.py::register_default_generators`. Write three lines of test using `ast`-like structural checks (`"package main" in files["main.go"]`). Done. The CLI picks it up automatically; the help message grows; no other file changes.

## Integration with the rest of the ecosystem

The factory is deliberately a **build tool**, not a runtime service. It has no dependency on the main CQRS-URL API and doesn't need to run inside your cluster. The obvious glue point is a command wrapper:

```
PUT /commands/compile-service
  { bundle_uri, targets } → { artifacts_uri }
```

That's a 20-line wrapper around the CLI. We haven't written it yet because it belongs to the forthcoming Service Runtime module, not to the factory. The factory stands alone, does one thing, and does it well.

## Try it

```bash
cd service-factory
python -m factory.cli compile bundles/connect-test-service.bundle.json \
    --contracts contracts \
    --targets python-fastapi,docker,openapi \
    --out ./dist
```

Peek at `dist/main.py`, `dist/Dockerfile`, `dist/openapi.json`. Run the tests with `pytest tests/` — 15 green in under a second.

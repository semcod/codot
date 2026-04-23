"""Generator registry and base protocol.

Every generator is a pure function Bundle -> {path: content}.
No I/O, no global state, no ordering requirements between generators.
The CLI (or runtime) picks which generators to run per target and merges
their outputs into a single output directory.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .ir import AnyBundle


@runtime_checkable
class Generator(Protocol):
    target: str          # "python-fastapi", "docker", "openapi", "view/php-standalone", ...
    category: str        # "code" | "infra" | "wire" | "view"

    def generate(self, bundle: AnyBundle) -> dict[str, str]:
        """Return a map of {relative_path: file_content}.

        Paths are POSIX-style and rooted at the bundle's output directory.
        Content is always text (UTF-8). Binary artifacts are out of scope
        for this layer; they live in templates/ and are copied by the CLI.

        Individual generators declare which bundle kind they accept; passing
        a mismatched kind (e.g. a :class:`ViewBundle` into python-fastapi)
        is a caller error and should raise ``TypeError``.
        """


class GeneratorRegistry:
    def __init__(self) -> None:
        self._gens: dict[str, Generator] = {}

    def register(self, gen: Generator) -> None:
        if gen.target in self._gens:
            raise ValueError(f"Duplicate generator for target: {gen.target}")
        self._gens[gen.target] = gen

    def get(self, target: str) -> Generator:
        if target not in self._gens:
            raise KeyError(
                f"Unknown target {target!r}. Available: {sorted(self._gens.keys())}"
            )
        return self._gens[target]

    def by_category(self, category: str) -> list[Generator]:
        return [g for g in self._gens.values() if g.category == category]

    def list(self) -> list[dict[str, str]]:
        return [{"target": g.target, "category": g.category} for g in self._gens.values()]


_registry = GeneratorRegistry()


def get_registry() -> GeneratorRegistry:
    return _registry


def register_default_generators() -> None:
    """Wire up built-in generators. Keep this small — one import per gen."""
    from .generators.code.python_fastapi import PythonFastApiGenerator
    from .generators.code.node_fastify import NodeFastifyGenerator
    from .generators.infra.docker import DockerGenerator
    from .generators.infra.kubernetes import KubernetesGenerator
    from .generators.wire.openapi import OpenApiGenerator
    from .generators.view.php_standalone import PhpStandaloneViewGenerator
    from .generators.view.fastapi_sse import FastApiSseViewGenerator
    from .generators.view.static_html import StaticHtmlViewGenerator

    reg = get_registry()
    if "python-fastapi" in {e["target"] for e in reg.list()}:
        return  # idempotent: already registered
    reg.register(PythonFastApiGenerator())
    reg.register(NodeFastifyGenerator())
    reg.register(DockerGenerator())
    reg.register(KubernetesGenerator())
    reg.register(OpenApiGenerator())
    reg.register(PhpStandaloneViewGenerator())
    reg.register(FastApiSseViewGenerator())
    reg.register(StaticHtmlViewGenerator())

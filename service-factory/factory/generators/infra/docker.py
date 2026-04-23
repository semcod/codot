"""docker generator.

Produces a Dockerfile tailored to the bundle's runtime, plus a
docker-compose.yml that wires the service with its companions. No reverse
proxy — each service exposes a single host port directly.
"""
from __future__ import annotations

from textwrap import dedent

from ...ir import Bundle, Companion


_COMPANION_DEFAULTS = {
    "litellm": {"image": "ghcr.io/berriai/litellm:main-latest", "port": 4000},
    "mcp":     {"image": "node:20-alpine", "port": 3000},
    "redis":   {"image": "redis:7-alpine", "port": 6379},
    "postgres":{"image": "postgres:16-alpine", "port": 5432},
}


def _indent_block(block: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + ln if ln else ln for ln in block.splitlines())


class DockerGenerator:
    target = "docker"
    category = "infra"

    def generate(self, bundle: Bundle) -> dict[str, str]:
        return {
            "Dockerfile": self._dockerfile(bundle),
            "docker-compose.yml": self._compose(bundle),
            ".dockerignore": self._dockerignore(),
        }

    def _dockerfile(self, bundle: Bundle) -> str:
        if bundle.runtime.language == "python":
            return self._python_dockerfile(bundle)
        if bundle.runtime.language == "node":
            return self._node_dockerfile(bundle)
        raise ValueError(f"Unsupported runtime language: {bundle.runtime.language}")

    def _python_dockerfile(self, bundle: Bundle) -> str:
        port = bundle.exposure.port
        hp = bundle.exposure.health_path
        return dedent(f"""\
            # Auto-generated Dockerfile for {bundle.name}
            FROM python:{bundle.runtime.version}-slim

            ENV PYTHONDONTWRITEBYTECODE=1 \\
                PYTHONUNBUFFERED=1 \\
                PIP_NO_CACHE_DIR=1

            WORKDIR /app

            COPY requirements.txt .
            RUN pip install --no-cache-dir -r requirements.txt

            COPY . .

            EXPOSE {port}

            HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
                CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{port}{hp}')"

            CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
        """)

    def _node_dockerfile(self, bundle: Bundle) -> str:
        port = bundle.exposure.port
        hp = bundle.exposure.health_path
        return dedent(f"""\
            # Auto-generated Dockerfile for {bundle.name}
            FROM node:{bundle.runtime.version}-alpine

            WORKDIR /app

            COPY package.json ./
            RUN npm install --production

            COPY . .

            EXPOSE {port}

            HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
                CMD wget -qO- http://localhost:{port}{hp} || exit 1

            CMD ["node", "server.js"]
        """)

    def _dockerignore(self) -> str:
        return "\n".join([
            "__pycache__",
            "*.pyc",
            ".venv",
            "node_modules",
            ".git",
            "*.md",
            "tests/",
            "",
        ])

    def _compose(self, bundle: Bundle) -> str:
        port = bundle.exposure.port
        host_port = port

        lines: list[str] = [
            f"# Auto-generated docker-compose for {bundle.name} (hash: {bundle.contract_hash()})",
            "services:",
        ]

        main_block = self._main_service_block(bundle, port, host_port)
        lines.append(_indent_block(main_block, 2))
        lines.append("")

        for comp in bundle.companions:
            comp_block = self._companion_block(comp)
            lines.append(_indent_block(comp_block, 2))
            lines.append("")

        storage_block = self._storage_block(bundle)
        if storage_block:
            lines.append(_indent_block(storage_block, 2))
            lines.append("")

        lines += [
            "networks:",
            "  default:",
            f"    name: svc-{bundle.name}",
            "",
        ]
        return "\n".join(lines)

    def _main_service_block(self, bundle: Bundle, port: int, host_port: int) -> str:
        block: list[str] = [
            f"{bundle.name}:",
            "  build:",
            "    context: .",
            "    dockerfile: Dockerfile",
            f"  container_name: svc-{bundle.name}-{bundle.contract_hash()}",
            "  ports:",
            f'    - "{host_port}:{port}"',
            "  environment:",
            f"    - SERVICE_NAME={bundle.name}",
            f"    - SERVICE_VERSION={bundle.version}",
            f"    - SERVICE_TTL={bundle.ttl}",
        ]
        for comp in bundle.companions:
            defaults = _COMPANION_DEFAULTS.get(comp.kind, {})
            cport = defaults.get("port", 8080)
            env_var = f"{comp.kind.upper()}_URL"
            block.append(f"    - {env_var}=http://{comp.name}:{cport}")

        block += [
            "  deploy:",
            "    resources:",
            "      limits:",
            f"        cpus: '{self._cpu_to_docker(bundle.resources.cpu)}'",
            f"        memory: {self._mem_to_docker(bundle.resources.memory)}",
            "  restart: unless-stopped",
        ]
        return "\n".join(block)

    def _companion_block(self, comp: Companion) -> str:
        defaults = _COMPANION_DEFAULTS.get(comp.kind, {})
        image = comp.image or defaults.get("image")
        if not image:
            raise ValueError(
                f"Companion {comp.name!r} has unknown kind {comp.kind!r} and no explicit image"
            )
        port = defaults.get("port", 8080)
        block = [
            f"{comp.name}:",
            f"  image: {image}",
            f"  container_name: svc-{comp.name}",
            "  expose:",
            f'    - "{port}"',
            "  restart: unless-stopped",
        ]
        return "\n".join(block)

    def _storage_block(self, bundle: Bundle) -> str:
        if bundle.storage.kind in ("none", ""):
            return ""
        defaults = _COMPANION_DEFAULTS.get(bundle.storage.kind, {})
        image = defaults.get("image")
        if not image:
            return ""
        block = [
            f"{bundle.storage.kind}:",
            f"  image: {image}",
            f"  container_name: svc-{bundle.name}-{bundle.storage.kind}",
            "  restart: unless-stopped",
        ]
        return "\n".join(block)

    @staticmethod
    def _cpu_to_docker(cpu: str) -> str:
        if cpu.endswith("m"):
            return str(int(cpu[:-1]) / 1000)
        return cpu

    @staticmethod
    def _mem_to_docker(mem: str) -> str:
        return mem.replace("Mi", "M").replace("Gi", "G")

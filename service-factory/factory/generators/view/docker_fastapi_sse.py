from __future__ import annotations

from ...ir import AnyBundle, ViewBundle
from ._shared import uses_host_local_sources


class DockerFastApiSseViewGenerator:
    target = "view/docker-fastapi-sse"
    category = "view"

    def generate(self, bundle: AnyBundle) -> dict[str, str]:
        if not isinstance(bundle, ViewBundle):
            raise TypeError(
                f"{self.target} expects a ViewBundle, got {type(bundle).__name__}"
            )
        return {
            "Dockerfile": self._dockerfile(bundle),
            "docker-compose.yml": self._compose(bundle),
            ".dockerignore": self._dockerignore(),
        }

    def _dockerfile(self, bundle: ViewBundle) -> str:
        port = bundle.exposure.port
        hp = bundle.exposure.health_path
        return "\n".join([
            f"FROM python:3.12-slim",
            "",
            "ENV PYTHONDONTWRITEBYTECODE=1 \\",
            "    PYTHONUNBUFFERED=1 \\",
            "    PIP_NO_CACHE_DIR=1",
            "",
            "WORKDIR /app",
            "",
            "COPY requirements.txt .",
            "RUN pip install --no-cache-dir -r requirements.txt",
            "",
            "COPY . .",
            "",
            f"EXPOSE {port}",
            "",
            "HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\",
            f"    CMD python -c \"import urllib.request; urllib.request.urlopen('http://localhost:{port}{hp}')\"",
            "",
            f'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]',
            "",
        ])

    def _compose(self, bundle: ViewBundle) -> str:
        port = bundle.exposure.port
        host_local = uses_host_local_sources(bundle)
        lines = [
            f"# Auto-generated docker-compose for {bundle.name} (hash: {bundle.contract_hash()})",
            "services:",
            f"  {bundle.name}:",
            "    build:",
            "      context: .",
            "      dockerfile: Dockerfile",
            f"    container_name: svc-{bundle.name}-{bundle.contract_hash()}",
            "    environment:",
            f"      - SERVICE_NAME={bundle.name}",
            f"      - SERVICE_VERSION={bundle.version}",
            "      - VIEW_TRANSPORT=sse",
            "    restart: unless-stopped",
        ]
        if host_local:
            lines += [
                "    network_mode: host",
            ]
        else:
            lines += [
                "    ports:",
                f'      - "{port}:{port}"',
                "networks:",
                "  default:",
                f"    name: view-{bundle.name}",
            ]
        lines.append("")
        return "\n".join(lines)

    def _dockerignore(self) -> str:
        return "\n".join([
            "__pycache__",
            "*.pyc",
            ".venv",
            ".git",
            "*.md",
            "tests/",
            "",
        ])

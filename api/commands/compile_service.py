"""Command that wraps the service-factory generator."""
from __future__ import annotations

import base64
import io
import json
import sys
import tarfile
from pathlib import Path

from models import CommandRequest, CommandResponse

from . import Command


class CompileServiceCommand(Command):
    name = "compile_service"
    description = (
        "Compile a SERVICE_BUNDLE or VIEW_BUNDLE JSON into generated artifacts. "
        "Uses the service-factory generator registry. "
        "Returns a base64-encoded tar.gz of the output files."
    )
    input_hint = {
        "input_uri": "URI of the bundle JSON (file:// or http://)",
        "meta": {
            "targets": "comma-separated generator targets, e.g. python-fastapi,docker",
        },
    }

    async def execute(self, request: CommandRequest) -> CommandResponse:
        import httpx

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "service-factory"))
        from factory import register_default_generators, get_registry
        from factory.ir import BundleLoader

        # Load bundle
        raw_text = await self._load_bundle_text(request.input_uri)
        raw = json.loads(raw_text)
        kind = raw.get("kind", "SERVICE_BUNDLE")

        # Determine targets
        meta = request.meta or {}
        targets_str = meta.get("targets", "")
        if not targets_str:
            targets = ["python-fastapi", "docker"]
        else:
            targets = [t.strip() for t in targets_str.split(",") if t.strip()]

        # Resolve contracts dir (for SERVICE_BUNDLE)
        bundle_path = Path(request.input_uri.replace("file://", "")) if request.input_uri and request.input_uri.startswith("file://") else Path.cwd() / "bundle.json"
        contracts_dir = Path(meta.get("contracts_dir", bundle_path.parent))

        # Generate
        register_default_generators()
        reg = get_registry()
        loader = BundleLoader(contracts_dir=contracts_dir)
        bundle = loader.load_from_dict(raw, bundle_path)

        all_files: dict[str, str] = {}
        for target in targets:
            gen = reg.get(target)
            files = gen.generate(bundle)
            for rel_path, content in files.items():
                all_files[f"{target}/{rel_path}"] = content

        # Pack into tar.gz base64
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            for rel_path, content in all_files.items():
                data = content.encode("utf-8")
                info = tarfile.TarInfo(name=rel_path)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))

        payload_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        return CommandResponse(
            ok=True,
            payload_b64=payload_b64,
            mime="application/gzip",
            meta={
                "targets": targets,
                "kind": kind,
                "files": list(all_files.keys()),
            },
        )

    async def _load_bundle_text(self, input_uri: str | None) -> str:
        if not input_uri:
            raise ValueError("compile_service requires input_uri pointing to bundle JSON")
        if input_uri.startswith("file://"):
            path = Path(input_uri.replace("file://", ""))
            if not path.exists():
                raise FileNotFoundError(f"Bundle not found: {path}")
            return path.read_text()
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(input_uri)
            resp.raise_for_status()
            return resp.text

from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import urlparse, unquote

from config import settings
from . import FetchResult


class FileProtocol:
    """Access local files. Only paths under ALLOWED_LOCAL_ROOTS are permitted
    (by default /data and /schemas inside the container).

    This prevents arbitrary filesystem reads even if the policy engine is
    permissive or misconfigured.
    """

    scheme = "file"

    def _resolve(self, uri: str) -> Path:
        parsed = urlparse(uri)
        # support file:///abs/path and file:/abs/path
        raw = unquote(parsed.path or "")
        if not raw:
            raise ValueError(f"Empty path in file URI: {uri}")

        path = Path(raw).resolve()
        allowed = [Path(r).resolve() for r in settings.allowed_local_roots]
        if not any(str(path).startswith(str(root) + "/") or path == root for root in allowed):
            raise PermissionError(
                f"Path {path} is outside allowed roots {[str(r) for r in allowed]}"
            )
        if not path.exists():
            raise FileNotFoundError(f"No such file: {path}")
        if not path.is_file():
            raise IsADirectoryError(f"Not a regular file: {path}")
        return path

    async def fetch(self, uri: str) -> FetchResult:
        path = self._resolve(uri)
        content = path.read_bytes()
        if len(content) > settings.fetch_max_bytes:
            raise ValueError(f"File too large: {len(content)} bytes")
        mime, _ = mimetypes.guess_type(str(path))
        return FetchResult(
            content=content,
            mime=mime or "application/octet-stream",
            source_uri=uri,
            extra={"path": str(path), "size": len(content)},
        )

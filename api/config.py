"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    policy_rules_path: str
    allowed_local_roots: tuple[str, ...]
    log_level: str
    fetch_timeout_seconds: float
    fetch_max_bytes: int


def load_settings() -> Settings:
    roots = os.environ.get("ALLOWED_LOCAL_ROOTS", "/data,/schemas")
    return Settings(
        jwt_secret=os.environ.get("JWT_SECRET", "dev-secret-change-me-xyz"),
        jwt_algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(
            os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        ),
        policy_rules_path=os.environ.get("POLICY_RULES_PATH", "/app/policy/rules.yaml"),
        allowed_local_roots=tuple(p.strip() for p in roots.split(",") if p.strip()),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        fetch_timeout_seconds=float(os.environ.get("FETCH_TIMEOUT_SECONDS", "15")),
        fetch_max_bytes=int(os.environ.get("FETCH_MAX_BYTES", str(50 * 1024 * 1024))),
    )


settings = load_settings()

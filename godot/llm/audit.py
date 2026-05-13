"""Postgres audit logger for LLM decisions."""

import os
from contextlib import contextmanager
from typing import Any

import psycopg2
from psycopg2.extras import Json


@contextmanager
def _get_conn():
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5433")),
        user=os.environ.get("POSTGRES_USER", "temporal"),
        password=os.environ.get("POSTGRES_PASSWORD", "temporal"),
        dbname=os.environ.get("POSTGRES_DB", "temporal"),
    )
    try:
        yield conn
    finally:
        conn.close()


def ensure_table() -> None:
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id          SERIAL PRIMARY KEY,
                ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                endpoint    TEXT NOT NULL,
                prompt      TEXT,
                kind        TEXT,
                runner      TEXT,
                targets     TEXT[],
                generated_bundle JSONB,
                acl_allowed BOOLEAN,
                error       TEXT,
                client_ip   TEXT,
                duration_ms NUMERIC(10,2)
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);
            CREATE INDEX IF NOT EXISTS idx_audit_endpoint ON audit_log(endpoint);
            CREATE INDEX IF NOT EXISTS idx_audit_kind ON audit_log(kind);
        """)
        conn.commit()


def log_generation(
    endpoint: str,
    prompt: str,
    kind: str,
    runner: str,
    targets: list[str],
    generated_bundle: dict[str, Any] | None,
    acl_allowed: bool,
    error: str | None,
    client_ip: str | None,
    duration_ms: float,
) -> None:
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_log (
                endpoint, prompt, kind, runner, targets,
                generated_bundle, acl_allowed, error, client_ip, duration_ms
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                endpoint,
                prompt,
                kind,
                runner,
                targets,
                Json(generated_bundle) if generated_bundle else None,
                acl_allowed,
                error,
                client_ip,
                duration_ms,
            ),
        )
        conn.commit()

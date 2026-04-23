-- Init script for audit logging (auto-mounted into postgres initdb)
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

CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);
CREATE INDEX IF NOT EXISTS idx_audit_endpoint ON audit_log(endpoint);
CREATE INDEX IF NOT EXISTS idx_audit_kind ON audit_log(kind);

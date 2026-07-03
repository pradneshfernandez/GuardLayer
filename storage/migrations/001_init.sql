CREATE TABLE IF NOT EXISTS verification_log (
    id              SERIAL PRIMARY KEY,
    entity_name     TEXT NOT NULL,
    address         TEXT NOT NULL,
    existence_status TEXT NOT NULL,
    open_closed_status TEXT NOT NULL,
    verdict         TEXT NOT NULL,
    confidence      FLOAT NOT NULL,
    needs_enrichment BOOLEAN NOT NULL DEFAULT false,
    cache_hit       BOOLEAN NOT NULL DEFAULT false,
    source_llm      TEXT,
    verified_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_verification_log_verified_at
    ON verification_log (verified_at DESC);
CREATE INDEX IF NOT EXISTS idx_verification_log_verdict
    ON verification_log (verdict);

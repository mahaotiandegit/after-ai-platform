CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS health_check (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO health_check(name)
VALUES ('after-ai-platform');

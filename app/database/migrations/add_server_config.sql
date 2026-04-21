-- ============================================================
-- Migration: Add server_ip, port, updated_at to activation_keys
-- ============================================================
-- Run this ONCE on existing PostgreSQL databases.
-- New databases created via SQLAlchemy create_all() don't need it.
--
-- Safe to run multiple times (uses ADD COLUMN IF NOT EXISTS).
--
-- Usage:
--   psql -U weighbridge_user -d weighbridge_db -f add_server_config.sql
-- ============================================================

BEGIN;

-- LAN server IP (e.g. "192.168.1.10")
-- Set by admin during license creation; returned to device on activation.
ALTER TABLE activation_keys
    ADD COLUMN IF NOT EXISTS server_ip VARCHAR;

-- Backend port (default 8000; must be in 1024–65535)
ALTER TABLE activation_keys
    ADD COLUMN IF NOT EXISTS port INTEGER DEFAULT 8000;

-- updated_at timestamp for concurrency tracking
ALTER TABLE activation_keys
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

-- Backfill updated_at for existing rows
UPDATE activation_keys
SET updated_at = created_at
WHERE updated_at IS NULL;

COMMIT;

-- Verify
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'activation_keys'
  AND column_name IN ('server_ip', 'port', 'updated_at')
ORDER BY column_name;

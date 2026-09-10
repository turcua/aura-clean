-- Aura Financial Tracker - Secure Database Schema
-- Sprint 18: Data Import Expansion (OFX + QIF)
--
-- Security/correctness properties (contrast with vulnerable-version's Sprint 18 schema):
-- - external_id stores OFX's FITID for import deduplication
-- - UNIQUE (account_id, external_id) — MySQL treats NULL as distinct per
--   column in a composite key, so regular transactions (external_id IS NULL,
--   whether linked to an account or not) never collide with each other;
--   only two OFX-imported rows sharing the same account + FITID would.

USE aura_secure;

ALTER TABLE transactions
    ADD COLUMN external_id VARCHAR(64) NULL;

ALTER TABLE transactions
    ADD CONSTRAINT uq_account_external_id UNIQUE (account_id, external_id);

SELECT 'Secure Sprint 18 schema created successfully!' AS status;

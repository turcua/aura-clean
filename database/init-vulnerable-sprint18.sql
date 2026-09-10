-- Aura Financial Tracker - Vulnerable Database Schema
-- Sprint 18: Data Import Expansion (OFX + QIF)
-- Intentional vulnerabilities preserved by design

USE aura_vulnerable;

-- VULNERABILITY: no UNIQUE constraint on (account_id, external_id) — unlike
-- secure-version, duplicate-safe re-import isn't enforced at the DB level,
-- only (imperfectly) checked in application code — see VULN-068/VULN-069
-- for how the import endpoint itself stays exploitable regardless.
ALTER TABLE transactions
    ADD COLUMN external_id VARCHAR(64) NULL;

SELECT 'Vulnerable Sprint 18 schema created successfully!' AS status;

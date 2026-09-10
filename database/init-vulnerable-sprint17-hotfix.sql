-- Aura Financial Tracker - Vulnerable Database Schema
-- Sprint 17 hotfix: VULN-065 removed per explicit user request (2026-07-25)
--
-- VULN-065 was "SQL Injection - Exchange Rate CRUD", specifically the
-- combination of no UNIQUE constraint on currency_code + update_rate()
-- always INSERTing — editing an existing rate created a duplicate row
-- instead of updating it. The user explicitly asked for this behavior to
-- be removed (not just worked around), understanding it was intentional.
-- VULN-064 (no rate bounds check) and VULN-066 (free-text currency_code,
-- stored XSS) are untouched and remain intentional.
--
-- Dedupes any existing duplicate currency_code rows first (keeps the most
-- recently updated row per code), since UNIQUE would otherwise fail to
-- apply against data already containing duplicates.

USE aura_vulnerable;

DELETE er1 FROM exchange_rates er1
INNER JOIN exchange_rates er2
    ON er1.currency_code = er2.currency_code
    AND (er1.updated_at < er2.updated_at OR (er1.updated_at = er2.updated_at AND er1.id < er2.id));

ALTER TABLE exchange_rates
    ADD CONSTRAINT uq_vuln_currency_code UNIQUE (currency_code);

SELECT 'Vulnerable Sprint 17 hotfix (VULN-065 removed) applied successfully!' AS status;

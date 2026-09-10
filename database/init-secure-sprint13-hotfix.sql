-- Aura Financial Tracker - Secure Database Schema
-- Sprint 13 hotfix: missing is_transfer column on transactions
--
-- Discovered during Sprint 17 manual testing (2026-07-25) — Transfer.create()
-- has referenced transactions.is_transfer since Sprint 13 shipped, but the
-- Sprint 13 migration (init-secure-sprint13.sql) never actually added that
-- column to transactions (only vulnerable-version's equivalent Sprint 3
-- migration did), so every transfer has failed since Sprint 13 with
-- "Unknown column 'is_transfer' in 'field list'".

USE aura_secure;

ALTER TABLE transactions
    ADD COLUMN is_transfer BOOLEAN NOT NULL DEFAULT FALSE;

SELECT 'Secure Sprint 13 hotfix applied successfully!' AS status;

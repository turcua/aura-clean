-- Aura Financial Tracker - Vulnerable Version
-- Sprint 53 (UI-01): custom account display order
ALTER TABLE accounts ADD COLUMN display_order INT NOT NULL DEFAULT 0;

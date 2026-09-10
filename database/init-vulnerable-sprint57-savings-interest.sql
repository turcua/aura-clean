-- Aura Financial Tracker - Vulnerable Version
-- Sprint 57 (ENH-11): savings account interest. Same schema as
-- secure-version's equivalent migration.
ALTER TABLE accounts
    ADD COLUMN interest_rate_annual DECIMAL(6, 3) DEFAULT NULL,
    ADD COLUMN interest_accrual_frequency ENUM('daily', 'monthly') DEFAULT NULL,
    ADD COLUMN last_interest_accrued_date DATE DEFAULT NULL;

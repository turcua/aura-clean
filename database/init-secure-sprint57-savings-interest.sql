-- Aura Financial Tracker - Secure Version
-- Sprint 57 (ENH-11): savings account interest.
-- interest_rate_annual: user-entered annual rate (%), NULL = interest not
--   configured for this account (most accounts, including all non-savings
--   ones, stay NULL forever).
-- interest_accrual_frequency: 'daily' or 'monthly', selectable per account.
-- last_interest_accrued_date: when this account was last credited — how
--   the scheduler job knows whether a 'monthly' account is due again yet
--   (a 'daily' account just checks this isn't already today).
ALTER TABLE accounts
    ADD COLUMN interest_rate_annual DECIMAL(6, 3) DEFAULT NULL,
    ADD COLUMN interest_accrual_frequency ENUM('daily', 'monthly') DEFAULT NULL,
    ADD COLUMN last_interest_accrued_date DATE DEFAULT NULL;

-- Aura Financial Tracker - Secure Database Schema
-- Sprint 17 follow-up: dynamic currency list (explicit user request, 2026-07-25)
--
-- Replaces the fixed ENUM('RON','EUR','USD','IDR') on accounts.currency and
-- exchange_rates.currency_code with a `currencies` reference table plus
-- FOREIGN KEY constraints — a new currency can now be added via a validated
-- INSERT (see models/currency.py) instead of a schema migration every time,
-- while staying just as strictly validated at the DB level as the ENUMs were.

USE aura_secure;

CREATE TABLE IF NOT EXISTS currencies (
    code VARCHAR(3) PRIMARY KEY,
    is_base BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_currency_code_format CHECK (code REGEXP '^[A-Z]{3}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO currencies (code, is_base) VALUES
    ('RON', TRUE),
    ('EUR', FALSE),
    ('USD', FALSE),
    ('IDR', FALSE);

-- accounts.currency: ENUM -> VARCHAR(3) + FK. MySQL converts existing ENUM
-- values to their string labels automatically when the column type changes,
-- so no data migration step is needed beyond the ALTER itself.
ALTER TABLE accounts
    MODIFY COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'RON';
ALTER TABLE accounts
    ADD CONSTRAINT fk_accounts_currency FOREIGN KEY (currency) REFERENCES currencies(code);

-- exchange_rates.currency_code: ENUM -> VARCHAR(3) + FK. UNIQUE and the
-- rate_to_base CHECK are untouched. RON is excluded here too — it's the
-- implicit base and never gets its own rate row.
ALTER TABLE exchange_rates
    MODIFY COLUMN currency_code VARCHAR(3) NOT NULL;
ALTER TABLE exchange_rates
    ADD CONSTRAINT fk_rates_currency FOREIGN KEY (currency_code) REFERENCES currencies(code),
    ADD CONSTRAINT chk_rate_currency_not_base CHECK (currency_code != 'RON');

SELECT 'Secure Sprint 17 currencies table + FK migration applied successfully!' AS status;

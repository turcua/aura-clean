-- Aura Financial Tracker - Vulnerable Database Schema
-- Sprint 17: Multi-Currency (static rates) - Insect Breathing: Butterfly Dance – Caprice
-- Intentional vulnerabilities preserved by design
--
-- Base currency is RON — not stored as a row in exchange_rates, implicitly 1.0.
-- Rates are stored as "X -> RON" so converting between any two non-base
-- currencies goes through RON as an intermediate step.

USE aura_vulnerable;

-- VULNERABILITY: currency stored as free-text VARCHAR, not an ENUM — no
-- server-side restriction to RON/EUR/USD/IDR (sets up VULN-066 stored XSS)
ALTER TABLE accounts
    ADD COLUMN currency VARCHAR(10) NOT NULL DEFAULT 'RON';

-- VULNERABILITY: no CHECK on rate_to_base > 0 — negative/zero/absurd rates
-- accepted (VULN-064). No UNIQUE on currency_code — duplicate/conflicting
-- rows possible, whichever is read first "wins" unpredictably.
CREATE TABLE IF NOT EXISTS exchange_rates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    currency_code VARCHAR(10) NOT NULL,
    rate_to_base DECIMAL(12, 6) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    -- VULN: No UNIQUE on currency_code
    -- VULN: No CHECK on rate_to_base > 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Placeholder rates — updated manually via the rate-management UI (MC-002)
INSERT INTO exchange_rates (currency_code, rate_to_base) VALUES
    ('EUR', 5.07),
    ('USD', 4.65),
    ('IDR', 0.00029);

SELECT 'Vulnerable Sprint 17 schema created successfully!' AS status;

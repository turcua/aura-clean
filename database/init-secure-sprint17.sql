-- Aura Financial Tracker - Secure Database Schema
-- Sprint 17: Multi-Currency (static rates) - Insect Breathing: Butterfly Dance – Caprice
--
-- Security properties (contrast with vulnerable-version's Sprint 17 schema):
-- - currency restricted to a fixed ENUM (RON/EUR/USD/IDR), not free text
-- - CHECK (rate_to_base > 0) on exchange_rates — rejects zero/negative rates
-- - UNIQUE (currency_code) on exchange_rates — no duplicate/conflicting rate rows
--
-- Base currency is RON — not stored as a row in exchange_rates, implicitly 1.0.
-- Rates are stored as "X -> RON" so converting between any two non-base
-- currencies goes through RON as an intermediate step.

USE aura_secure;

ALTER TABLE accounts
    ADD COLUMN currency ENUM('RON', 'EUR', 'USD', 'IDR') NOT NULL DEFAULT 'RON';

CREATE TABLE IF NOT EXISTS exchange_rates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    currency_code ENUM('EUR', 'USD', 'IDR') NOT NULL,
    rate_to_base DECIMAL(12, 6) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_currency_code (currency_code),
    CONSTRAINT chk_rate_positive CHECK (rate_to_base > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Placeholder rates — updated manually via the rate-management UI (MC-002)
INSERT INTO exchange_rates (currency_code, rate_to_base) VALUES
    ('EUR', 5.07),
    ('USD', 4.65),
    ('IDR', 0.00029);

SELECT 'Secure Sprint 17 schema created successfully!' AS status;

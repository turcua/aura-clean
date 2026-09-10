-- Aura Financial Tracker - Vulnerable Database Schema
-- Sprint 3: Recurring Transactions + Accounts Foundation
-- Intentional vulnerabilities preserved by design

USE aura_vulnerable;

-- ============================================================================
-- ACCOUNTS TABLE
-- Foundation for Sprint 3 recurring transactions and Sprint 4 multi-account
-- ============================================================================
-- VULNERABILITIES (intentional):
-- - No FOREIGN KEY on user_id (orphaned accounts possible)
-- - No UNIQUE constraint on (user_id, name) (duplicate account names allowed)
-- - No CHECK on current_balance (can go negative without restriction)
-- - Mass assignment: user_id accepted from API payload without validation

CREATE TABLE IF NOT EXISTS accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    type ENUM('checking', 'savings', 'credit_card', 'investment', 'cash') NOT NULL DEFAULT 'checking',
    initial_balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    current_balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    include_in_budget BOOLEAN DEFAULT TRUE,
    description VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

    -- VULN: No FOREIGN KEY on user_id
    -- VULN: No UNIQUE on (user_id, name)
    -- VULN: No CHECK on current_balance >= 0

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- ALTER TRANSACTIONS TABLE
-- Add account linkage, transfer flag, and recurring origin tracking
-- ============================================================================
-- VULNERABILITIES (intentional):
-- - account_id nullable and unvalidated (transactions can float without account)
-- - No FOREIGN KEY on account_id or recurring_transaction_id
-- - is_transfer flag is user-controlled (no server-side enforcement)

ALTER TABLE transactions
    ADD COLUMN account_id INT DEFAULT NULL,
    ADD COLUMN is_transfer BOOLEAN DEFAULT FALSE,
    ADD COLUMN recurring_transaction_id INT DEFAULT NULL;

-- ============================================================================
-- RECURRING TRANSACTIONS TABLE
-- ============================================================================
-- VULNERABILITIES (intentional):
-- - No FOREIGN KEY on user_id, account_id, to_account_id, category_id
-- - No CHECK on amount > 0 (negative recurring amounts accepted)
-- - No CHECK on end_date > start_date (inverted date ranges accepted)
-- - No CHECK on next_run_date >= start_date
-- - IDOR: recurring transaction id directly exposed in all API endpoints
-- - SQL injection in all CRUD operations (string concatenation in model)
-- - Mass assignment: user_id accepted from request payload
-- - No auth check on auto-generate endpoint (any user can trigger generation)

CREATE TABLE IF NOT EXISTS recurring_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    account_id INT NOT NULL,
    to_account_id INT DEFAULT NULL,        -- Only set for transfer type
    category_id INT DEFAULT NULL,          -- NULL for transfer type
    type ENUM('income', 'expense', 'transfer') NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    description VARCHAR(255),
    frequency ENUM('daily', 'weekly', 'monthly', 'yearly') NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE DEFAULT NULL,            -- NULL means no end date
    next_run_date DATE NOT NULL,
    last_run_date DATE DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

    -- VULN: No FOREIGN KEY constraints on any column
    -- VULN: No CHECK on amount > 0
    -- VULN: No CHECK on end_date > start_date

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SEED DATA: Accounts
-- testuser = user_id 1 | admin = user_id 2
-- ============================================================================

INSERT INTO accounts (user_id, name, type, initial_balance, current_balance, include_in_budget, description) VALUES
-- testuser accounts
(1, 'Main Checking',        'checking',    2500.00,  2500.00,  TRUE,  'Primary daily use account'),
(1, 'Savings Account',      'savings',     10000.00, 10000.00, TRUE,  'Emergency fund'),
(1, 'Credit Card',          'credit_card', -500.00,  -500.00,  FALSE, 'Monthly credit card - excluded from budget'),

-- admin accounts
(2, 'Admin Checking',       'checking',    5000.00,  5000.00,  TRUE,  'Admin primary account'),
(2, 'Investment Portfolio', 'investment',  25000.00, 25000.00, FALSE, 'Stock and ETF portfolio');

-- ============================================================================
-- SEED DATA: Recurring Transactions
-- References testuser categories:
--   id=1 Salary (income), id=5 Groceries (expense), id=8 Utilities (expense)
-- References testuser accounts:
--   id=1 Main Checking, id=2 Savings Account
-- ============================================================================

INSERT INTO recurring_transactions (user_id, account_id, to_account_id, category_id, type, amount, description, frequency, start_date, end_date, next_run_date, is_active) VALUES
-- Income: salary credited to checking
(1, 1, NULL, 1, 'income',   3500.00, 'Monthly Salary',         'monthly', '2026-01-01', NULL, '2026-07-01', TRUE),
-- Expense: groceries deducted from checking
(1, 1, NULL, 5, 'expense',   250.00, 'Weekly Groceries',       'weekly',  '2026-01-05', NULL, '2026-06-22', TRUE),
-- Expense: utilities deducted from checking
(1, 1, NULL, 8, 'expense',   150.00, 'Utility Bills',          'monthly', '2026-01-07', NULL, '2026-07-07', TRUE),
-- Transfer: automatic monthly savings from checking to savings
(1, 1, 2,    NULL, 'transfer', 500.00, 'Monthly Savings Transfer', 'monthly', '2026-01-01', NULL, '2026-07-01', TRUE);

SELECT 'Sprint 3 database schema created successfully!' AS status;

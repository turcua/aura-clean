-- Aura Financial Tracker - Vulnerable Database Schema
-- Sprint 4: Multi-Account, Transfers, Budgets, Savings Goals
-- Intentional vulnerabilities preserved by design

USE aura_vulnerable;

-- ============================================================================
-- TRANSFERS TABLE
-- Links two transactions that represent opposite sides of a transfer
-- ============================================================================
-- VULNERABILITIES (intentional):
-- - No FOREIGN KEY constraints on any column
-- - No CHECK that from_account_id != to_account_id (self-transfer allowed)
-- - No CHECK on amount > 0
-- - No validation that both accounts belong to the same user (cross-user transfer)
-- - IDOR: transfer id directly exposed in API responses
-- - SQL injection in all CRUD operations

CREATE TABLE IF NOT EXISTS transfers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    from_account_id INT NOT NULL,
    to_account_id INT NOT NULL,
    from_transaction_id INT NOT NULL,      -- Transaction record for debit side
    to_transaction_id INT NOT NULL,        -- Transaction record for credit side
    amount DECIMAL(10,2) NOT NULL,
    description VARCHAR(255),
    transfer_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    -- VULN: No FOREIGN KEY on any column
    -- VULN: No CHECK that from_account_id != to_account_id
    -- VULN: No CHECK that accounts belong to user_id
    -- VULN: No CHECK on amount > 0

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- BUDGETS TABLE
-- Monthly, yearly, or custom-range spending plans
-- ============================================================================
-- VULNERABILITIES (intentional):
-- - No FOREIGN KEY on user_id
-- - No CHECK on total_limit > 0 (zero or negative budgets accepted)
-- - No CHECK on end_date > start_date (inverted ranges accepted)
-- - No UNIQUE on (user_id, name) (duplicate budget names allowed)
-- - IDOR: budget id directly exposed in API
-- - SQL injection in all CRUD operations

CREATE TABLE IF NOT EXISTS budgets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    period_type ENUM('monthly', 'yearly', 'custom') NOT NULL DEFAULT 'monthly',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_limit DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

    -- VULN: No FOREIGN KEY on user_id
    -- VULN: No CHECK on total_limit > 0
    -- VULN: No CHECK on end_date > start_date

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- BUDGET_CATEGORIES TABLE
-- Per-category spending limits within a budget
-- ============================================================================
-- VULNERABILITIES (intentional):
-- - No FOREIGN KEY on budget_id or category_id
-- - No UNIQUE on (budget_id, category_id) → duplicate entries allowed (BUG-005)
-- - No CHECK on limit_amount > 0
-- - IDOR: category limits accessible by budget_id without ownership check

CREATE TABLE IF NOT EXISTS budget_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    budget_id INT NOT NULL,
    category_id INT NOT NULL,
    limit_amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    -- VULN: No FOREIGN KEY on budget_id or category_id
    -- VULN: No UNIQUE on (budget_id, category_id) → BUG-005 source
    -- VULN: No CHECK on limit_amount > 0

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SAVINGS_GOALS TABLE
-- Target-based savings tracking with dual-mode timeline calculator
-- ============================================================================
-- VULNERABILITIES (intentional):
-- - No FOREIGN KEY on user_id or account_id
-- - No CHECK on target_amount > 0
-- - No CHECK on current_amount <= target_amount
-- - status not auto-updated when current_amount >= target_amount (BUG-008)
-- - account_id nullable and unvalidated (goal can reference any user's account)
-- - IDOR: goal id directly exposed in all API endpoints
-- - SQL injection in all CRUD operations

CREATE TABLE IF NOT EXISTS savings_goals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    account_id INT DEFAULT NULL,           -- Optional linked account
    name VARCHAR(100) NOT NULL,
    target_amount DECIMAL(10,2) NOT NULL,
    current_amount DECIMAL(10,2) DEFAULT 0.00,
    target_date DATE DEFAULT NULL,         -- Mode A: fixed deadline
    monthly_target DECIMAL(10,2) DEFAULT NULL, -- Mode B: fixed monthly contribution
    status ENUM('active', 'achieved', 'paused') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

    -- VULN: No FOREIGN KEY on user_id or account_id
    -- VULN: No CHECK on target_amount > 0
    -- VULN: No CHECK on current_amount <= target_amount
    -- VULN: status not auto-updated at 100% → BUG-008 source

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SEED DATA: Budgets
-- testuser = user_id 1
-- ============================================================================

INSERT INTO budgets (user_id, name, period_type, start_date, end_date, total_limit, is_active) VALUES
(1, 'June 2026 Budget', 'monthly', '2026-06-01', '2026-06-30', 2000.00, TRUE),
(1, '2026 Annual Budget', 'yearly', '2026-01-01', '2026-12-31', 24000.00, TRUE);

-- ============================================================================
-- SEED DATA: Budget Category Limits
-- June budget (budget_id=1), testuser categories:
--   id=5 Groceries | id=6 Transport | id=7 Entertainment | id=8 Utilities
-- ============================================================================

INSERT INTO budget_categories (budget_id, category_id, limit_amount) VALUES
(1, 5, 400.00),
(1, 6, 200.00),
(1, 7, 150.00),
(1, 8, 200.00);

-- ============================================================================
-- SEED DATA: Savings Goals
-- testuser savings account = account_id 2 (from Sprint 3 seed)
-- ============================================================================

INSERT INTO savings_goals (user_id, account_id, name, target_amount, current_amount, target_date, monthly_target, status) VALUES
(1, 2, 'Emergency Fund',  15000.00, 10000.00, '2026-12-31', 500.00,  'active'),
(1, NULL, 'New Laptop',    2000.00,   350.00, '2026-09-01', 275.00,  'active'),
(1, 2,   'Vacation Fund',  5000.00,   800.00, '2027-03-01', 200.00,  'active');

SELECT 'Sprint 4 database schema created successfully!' AS status;

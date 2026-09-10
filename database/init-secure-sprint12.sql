-- Aura Financial Tracker - Secure Database Schema
-- Sprint 12: Accounts + Recurring Transactions
--
-- Security properties (contrast with vulnerable-version's Sprint 3 schema):
-- - FOREIGN KEY constraints throughout (accounts.user_id, recurring_transactions.*)
-- - UNIQUE (user_id, name) on accounts — no duplicate account names
-- - CHECK (amount > 0) and CHECK (end_date > start_date) on recurring_transactions
-- - is_template built in from day one (no later ALTER TABLE needed)
-- - 'transfer' recurring type intentionally NOT included yet — the Transfer model
--   itself lands in Sprint 13; adding the enum value now without the model behind
--   it would let a transfer-type row exist with nothing to execute it

USE aura_secure;

CREATE TABLE IF NOT EXISTS accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    type ENUM('checking', 'savings', 'credit_card', 'investment', 'cash') NOT NULL DEFAULT 'checking',
    initial_balance DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    current_balance DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    include_in_budget BOOLEAN NOT NULL DEFAULT TRUE,
    description VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_account_name (user_id, name),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE transactions
    ADD COLUMN account_id INT DEFAULT NULL,
    ADD COLUMN recurring_transaction_id INT DEFAULT NULL,
    ADD FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS recurring_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    account_id INT NOT NULL,
    category_id INT DEFAULT NULL,
    type ENUM('income', 'expense') NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    description VARCHAR(255),
    frequency ENUM('daily', 'weekly', 'monthly', 'yearly') NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE DEFAULT NULL,
    next_run_date DATE NOT NULL,
    last_run_date DATE DEFAULT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_template BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    CONSTRAINT chk_recurring_amount_positive CHECK (amount > 0),
    CONSTRAINT chk_recurring_date_range CHECK (end_date IS NULL OR end_date > start_date),
    INDEX idx_user_id (user_id),
    INDEX idx_next_run_date (next_run_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Now that recurring_transaction_id exists, add the FK (transactions table already exists from Sprint 11)
ALTER TABLE transactions
    ADD FOREIGN KEY (recurring_transaction_id) REFERENCES recurring_transactions(id) ON DELETE SET NULL;

SELECT 'Secure Sprint 12 schema created successfully!' AS status;

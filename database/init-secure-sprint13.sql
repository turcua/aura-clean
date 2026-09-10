-- Aura Financial Tracker - Secure Database Schema
-- Sprint 13: Transfers + Budgets + Savings Goals
--
-- Security properties (contrast with vulnerable-version's Sprint 4 schema):
-- - FOREIGN KEY constraints throughout
-- - CHECK (amount > 0) and CHECK (from_account_id != to_account_id) on transfers
-- - CHECK (total_limit > 0), CHECK (end_date > start_date), UNIQUE (user_id, name) on budgets
-- - UNIQUE (budget_id, category_id) on budget_categories — the DELETE-then-INSERT
--   dance the vulnerable version needs (BUG-005) isn't needed here; the model
--   uses a single atomic INSERT ... ON DUPLICATE KEY UPDATE instead
-- - CHECK (target_amount > 0) on savings_goals

USE aura_secure;

CREATE TABLE IF NOT EXISTS transfers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    from_account_id INT NOT NULL,
    to_account_id INT NOT NULL,
    from_transaction_id INT NOT NULL,
    to_transaction_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    description VARCHAR(255),
    transfer_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (from_account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (to_account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (from_transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    FOREIGN KEY (to_transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    CONSTRAINT chk_transfer_amount_positive CHECK (amount > 0),
    CONSTRAINT chk_transfer_different_accounts CHECK (from_account_id != to_account_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS budgets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    period_type ENUM('monthly', 'yearly', 'custom') NOT NULL DEFAULT 'monthly',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_limit DECIMAL(10, 2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_budget_name (user_id, name),
    CONSTRAINT chk_budget_limit_positive CHECK (total_limit > 0),
    CONSTRAINT chk_budget_date_range CHECK (end_date > start_date),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS budget_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    budget_id INT NOT NULL,
    category_id INT NOT NULL,
    limit_amount DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE KEY uq_budget_category (budget_id, category_id),
    CONSTRAINT chk_limit_amount_positive CHECK (limit_amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS savings_goals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    account_id INT DEFAULT NULL,
    name VARCHAR(100) NOT NULL,
    target_amount DECIMAL(10, 2) NOT NULL,
    current_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    target_date DATE DEFAULT NULL,
    monthly_target DECIMAL(10, 2) DEFAULT NULL,
    status ENUM('active', 'achieved', 'paused') NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    CONSTRAINT chk_goal_target_positive CHECK (target_amount > 0),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT 'Secure Sprint 13 schema created successfully!' AS status;

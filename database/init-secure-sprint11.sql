-- Aura Financial Tracker - Secure Database Schema
-- Sprint 11: Core Financial Tracking (Categories + Transactions)
--
-- Security properties (contrast with vulnerable-version's Sprint 2 schema):
-- - FOREIGN KEY constraints on user_id and category_id (referential integrity)
-- - CHECK constraint on amount >= 0
-- - UNIQUE constraint on (user_id, name, type) — no duplicate categories per user
-- - is_default / nullable user_id built in from day one (no later ALTER TABLE needed)
-- - ON DELETE SET NULL for category_id — deleting a category never orphans a transaction

USE aura_secure;

CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,                              -- NULL = system-wide default category
    name VARCHAR(100) NOT NULL,
    type ENUM('income', 'expense') NOT NULL,
    color VARCHAR(7) NOT NULL DEFAULT '#6c757d',
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_name_type (user_id, name, type),
    INDEX idx_user_id (user_id),
    INDEX idx_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT NULL,
    type ENUM('income', 'expense') NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    description VARCHAR(255),
    transaction_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    CONSTRAINT chk_amount_non_negative CHECK (amount >= 0),
    INDEX idx_user_id (user_id),
    INDEX idx_category_id (category_id),
    INDEX idx_type (type),
    INDEX idx_transaction_date (transaction_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Global default categories, available to every user (user_id IS NULL, is_default = TRUE)
INSERT INTO categories (user_id, name, type, color, is_default) VALUES
(NULL, 'Salary',         'income',  '#28a745', TRUE),
(NULL, 'Freelance',      'income',  '#20c997', TRUE),
(NULL, 'Investments',    'income',  '#17a2b8', TRUE),
(NULL, 'Other Income',   'income',  '#6c757d', TRUE),
(NULL, 'Groceries',      'expense', '#dc3545', TRUE),
(NULL, 'Transport',      'expense', '#fd7e14', TRUE),
(NULL, 'Entertainment',  'expense', '#6f42c1', TRUE),
(NULL, 'Utilities',      'expense', '#ffc107', TRUE),
(NULL, 'Healthcare',     'expense', '#e83e8c', TRUE),
(NULL, 'Other Expenses', 'expense', '#6c757d', TRUE);

SELECT 'Secure Sprint 11 schema created successfully!' AS status;

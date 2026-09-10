-- Aura Financial Tracker - Vulnerable Database Schema
-- Sprint 2: Thunder Breathing - Second Form
-- Additional tables for transaction management

USE aura_vulnerable;

-- ============================================================================
-- CATEGORIES TABLE
-- ============================================================================
-- VULNERABILITIES:
-- - No foreign key constraint on user_id (orphaned categories possible)
-- - No unique constraint (duplicate category names allowed)
-- - No validation on color/icon fields

DROP TABLE IF EXISTS categories;

CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    type ENUM('income', 'expense') NOT NULL,
    color VARCHAR(7) DEFAULT '#6c757d',      -- Hex color code (e.g., #FF5733)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- VULN: No foreign key constraint
    -- VULN: No unique constraint on (user_id, name, type)
    
    INDEX idx_user_id (user_id),
    INDEX idx_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TRANSACTIONS TABLE
-- ============================================================================
-- VULNERABILITIES:
-- - No foreign key constraints (user_id, category_id)
-- - No CHECK constraint on amount (negative amounts allowed)
-- - No CHECK constraint on transaction_date (future dates allowed)
-- - No validation on description field (XSS possible)

DROP TABLE IF EXISTS transactions;

CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT,                         -- Can be NULL (uncategorized)
    type ENUM('income', 'expense') NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,          -- Supports up to 99,999,999.99
    description TEXT,                        -- VULN: No length limit, XSS possible
    transaction_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- VULNERABILITIES (intentional):
    -- VULN: No FOREIGN KEY on user_id (orphaned transactions)
    -- VULN: No FOREIGN KEY on category_id (orphaned references)
    -- VULN: No CHECK on amount >= 0 (negative amounts allowed)
    -- VULN: No CHECK on transaction_date (future dates allowed)
    
    INDEX idx_user_id (user_id),
    INDEX idx_category_id (category_id),
    INDEX idx_type (type),
    INDEX idx_transaction_date (transaction_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SEED DATA - Default Categories
-- ============================================================================
-- Insert default categories for existing users (testuser = user_id 1, admin = user_id 2)

INSERT INTO categories (user_id, name, type, color) VALUES
-- Income categories
(1, 'Salary', 'income', '#28a745'),
(1, 'Freelance', 'income', '#20c997'),
(1, 'Investments', 'income', '#17a2b8'),
(1, 'Other Income', 'income', '#6c757d'),

-- Expense categories
(1, 'Groceries', 'expense', '#dc3545'),
(1, 'Transport', 'expense', '#fd7e14'),
(1, 'Entertainment', 'expense', '#6f42c1'),
(1, 'Utilities', 'expense', '#ffc107'),
(1, 'Healthcare', 'expense', '#e83e8c'),
(1, 'Other Expenses', 'expense', '#6c757d'),

-- Categories for admin user (user_id 2)
(2, 'Salary', 'income', '#28a745'),
(2, 'Food', 'expense', '#dc3545');

-- ============================================================================
-- SEED DATA - Sample Transactions
-- ============================================================================
-- Insert sample transactions for testing

INSERT INTO transactions (user_id, category_id, type, amount, description, transaction_date) VALUES
-- testuser (user_id 1) transactions
(1, 1, 'income', 3500.00, 'Monthly salary - February', '2026-02-01'),
(1, 2, 'income', 500.00, 'Website project payment', '2026-02-05'),
(1, 5, 'expense', 250.50, 'Weekly groceries at supermarket', '2026-02-03'),
(1, 6, 'expense', 45.00, 'Gas station fill-up', '2026-02-04'),
(1, 7, 'expense', 60.00, 'Movie tickets and popcorn', '2026-02-06'),
(1, 8, 'expense', 150.00, 'Electricity and water bills', '2026-02-07'),
(1, 5, 'expense', 180.00, 'Groceries - meal prep', '2026-02-08'),

-- admin (user_id 2) transactions
(2, 11, 'income', 5000.00, 'Admin salary', '2026-02-01'),
(2, 12, 'expense', 100.00, 'Lunch expenses', '2026-02-07');

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Uncomment to verify data after running script

-- SELECT 'Categories created:' AS status;
-- SELECT COUNT(*) as category_count FROM categories;
-- SELECT * FROM categories ORDER BY user_id, type, name;

-- SELECT 'Transactions created:' AS status;
-- SELECT COUNT(*) as transaction_count FROM transactions;
-- SELECT * FROM transactions ORDER BY user_id, transaction_date DESC;

-- Summary by user
-- SELECT 
--     u.username,
--     COUNT(DISTINCT c.id) as categories,
--     COUNT(DISTINCT t.id) as transactions,
--     SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END) as total_income,
--     SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END) as total_expenses
-- FROM users u
-- LEFT JOIN categories c ON u.id = c.user_id
-- LEFT JOIN transactions t ON u.id = t.user_id
-- GROUP BY u.id, u.username;

SELECT 'Sprint 2 database schema created successfully!' AS status;

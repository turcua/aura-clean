-- Aura Financial Tracker - Vulnerable Database Schema
-- Sprint 6: Shadow Evolution - Core Enhancements
-- Intentional vulnerabilities preserved by design

USE aura_vulnerable;

-- ============================================================================
-- ENH-007: Global Default Categories
-- Add is_default flag to categories table
-- VULNERABILITY: No access control on is_default — any user can set it via SQL injection
-- VULNERABILITY: Default categories can be deleted by any user (IDOR preserved)
-- ============================================================================

ALTER TABLE categories ADD COLUMN is_default BOOLEAN DEFAULT FALSE;

-- ============================================================================
-- ENH-002: Recurring Transaction Templates
-- Add is_template flag to recurring_transactions
-- VULNERABILITY: Templates are not isolated per-user (IDOR on template_id)
-- ============================================================================

ALTER TABLE recurring_transactions ADD COLUMN is_template BOOLEAN DEFAULT FALSE;

-- ============================================================================
-- Default Expense Categories (user_id = NULL = system-wide)
-- ============================================================================

-- Drop icon column if it exists (from older schema versions)
ALTER TABLE categories DROP COLUMN IF EXISTS icon;

-- Allow NULL user_id so system-wide defaults (user_id = NULL) can be inserted
ALTER TABLE categories MODIFY COLUMN user_id INT NULL;

INSERT IGNORE INTO categories (user_id, name, type, color, is_default)
VALUES
    (NULL, 'Food & Dining',   'expense', '#e74c3c', TRUE),
    (NULL, 'Transport',       'expense', '#e67e22', TRUE),
    (NULL, 'Housing',         'expense', '#3498db', TRUE),
    (NULL, 'Healthcare',      'expense', '#2ecc71', TRUE),
    (NULL, 'Entertainment',   'expense', '#9b59b6', TRUE),
    (NULL, 'Shopping',        'expense', '#1abc9c', TRUE),
    (NULL, 'Education',       'expense', '#f39c12', TRUE),
    (NULL, 'Utilities',       'expense', '#95a5a6', TRUE),
    (NULL, 'Travel',          'expense', '#2980b9', TRUE),
    (NULL, 'Fitness',         'expense', '#e91e63', TRUE),
    -- Default Income Categories
    (NULL, 'Salary',          'income',  '#27ae60', TRUE),
    (NULL, 'Freelance',       'income',  '#2980b9', TRUE),
    (NULL, 'Investment',      'income',  '#16a085', TRUE),
    (NULL, 'Gift',            'income',  '#d35400', TRUE),
    (NULL, 'Bonus',           'income',  '#8e44ad', TRUE);

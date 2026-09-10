-- Aura Financial Tracker - Vulnerable Database Schema
-- Sprint 1: User Authentication Tables (WITH INTENTIONAL VULNERABILITIES)

-- Drop tables if they exist (for clean initialization)
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS user_sessions;

-- Users Table (Vulnerable Version)
-- VULNERABILITY: Stores passwords in plaintext (or weak MD5)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,  -- VULN: Plaintext password storage
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL
    -- VULN: No unique constraints (allows duplicate usernames/emails)
    -- VULN: No indexes (performance issue, information disclosure via timing)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User Sessions Table (Vulnerable Version)
-- VULNERABILITY: Predictable session tokens, no expiration enforcement
CREATE TABLE user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_token VARCHAR(255) NOT NULL,  -- VULN: No uniqueness constraint
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN DEFAULT TRUE
    -- VULN: No foreign key constraint (orphaned sessions possible)
    -- VULN: No expiration mechanism
    -- VULN: No indexes
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert a test user (password stored in plaintext: VulnPass123)
INSERT INTO users (username, email, password) 
VALUES ('testuser', 'test@aura.local', 'VulnPass123');

-- Insert another test user with weak password
INSERT INTO users (username, email, password) 
VALUES ('admin', 'admin@aura.local', '123456');

-- Log initialization
SELECT 'Vulnerable database initialized successfully!' AS status;

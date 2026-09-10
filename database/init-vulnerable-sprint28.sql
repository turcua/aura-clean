USE aura_vulnerable;

-- Same shape as secure-version — the vulnerability here isn't in the schema,
-- it's in how the app queries/authorizes access to these rows (see
-- models/loan.py and routes/api/loans.py: f-string SQL, user_id from
-- request, no ownership check — VULN-080).
CREATE TABLE IF NOT EXISTS loans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    principal DECIMAL(12,2) NOT NULL,
    margin_pct DECIMAL(5,3) NOT NULL,
    initial_base_index_pct DECIMAL(5,3) NOT NULL,
    start_date DATE NOT NULL,
    original_term_months INT NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'RON',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    refinanced_from_loan_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (refinanced_from_loan_id) REFERENCES loans(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS loan_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loan_id INT NOT NULL,
    event_type VARCHAR(30) NOT NULL,
    effective_date DATE NOT NULL,
    payload JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE,
    INDEX idx_loan_date (loan_id, effective_date)
);

ALTER TABLE transactions ADD COLUMN loan_id INT NULL,
    ADD FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE SET NULL;

ALTER TABLE recurring_transactions ADD COLUMN loan_id INT NULL,
    ADD FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE SET NULL;

SELECT 'Vulnerable Sprint 28 schema created successfully!' AS status;

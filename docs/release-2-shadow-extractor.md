# ⚔️ Release 2: "Shadow Extractor" — Full Documentation

**Project**: Aura Financial Tracker  
**Release**: 2 of 5  
**Codename**: Shadow Extractor  
**Status**: ✅ COMPLETE  
**Date Completed**: 2026-06-17  
**Scope**: Vulnerable version only (secure version deferred to Release 5)

---

## 📋 Full Project Roadmap

### Overview

| Release | Codename | Sprints | Points | Status |
|---------|----------|---------|--------|--------|
| 1 | Hashira Foundation | 1–2 | 54 | ✅ Complete |
| 2 | Shadow Extractor | 3–5 | 91 | ✅ Complete |
| 3 | Shadow Evolution | 6–7 | 86 | 📋 Planned |
| 4 | Supreme Shadow Monarch | 8–9 | 61 | 📋 Planned |
| 5 | Fortress of Security | 10 | 82 | 📋 Planned |
| **Total** | | **10** | **374** | **30% done** |

---

### Release 1: "Hashira Foundation" ✅

**Goal**: Core infrastructure and authentication system  
**Sprints**: 1–2 | **Points**: 54/54

#### Sprint 1: Water Breathing — First Form (28 pts) ✅
- User registration (vulnerable: SQL injection, plaintext passwords)
- User login / logout (vulnerable: login bypass, no rate limiting)
- Session management (predictable tokens, no expiration, fixation)
- Profile management (IDOR on user_id param)
- Admin panel (no authentication required)
- Docker + MySQL setup, Blueprint architecture

#### Sprint 2: Thunder Breathing — Second Form (26 pts) ✅
- Manual transaction entry (CRUD via AJAX modals)
- Expense & income category management (create/edit/delete)
- Dashboard with Chart.js (bar chart by month, pie chart by category)
- Transaction filtering (date range, type, category)
- Stored XSS in transaction description and category name
- IDOR on all transaction and category endpoints

**Release 1 Vulnerabilities**: 27 (VULN-001 through VULN-027)

---

### Release 2: "Shadow Extractor" ✅

**Goal**: Multi-account management, recurring transactions, budgets, savings goals, export/import  
**Sprints**: 3–5 | **Points**: 91/91

*(Full detail in sections below)*

**Release 2 Vulnerabilities**: 18 new (VULN-028 through VULN-045)  
**Total cumulative**: 45 vulnerabilities

---

### Release 3: "Shadow Evolution" 📋 PLANNED

**Goal**: Core enhancements and major UI/UX redesign  
**Sprints**: 6–7 | **Points**: 86

#### Sprint 6: Core Enhancements (23 pts)
- ENH-004: Auto goal progress via account transfers (8 pts)
  - When money is transferred to a linked account → savings goal progress updates automatically
- ENH-007: Global default categories (7 pts)
  - System-wide default income & expense categories
  - User-isolated custom categories for better onboarding
- ENH-001: Category icons & colors customization (3 pts)
  - Full emoji support (groundwork laid in Sprint 5 BUG-001 fix)
- ENH-002: Recurring transaction templates (5 pts)
  - Save and reuse transaction patterns

#### Sprint 7: UX & Visual Design (63 pts)
- ENH-003: Budget vs Actual Charts (8 pts)
  - Visual bar/line comparison of planned vs actual spending
- ENH-005: Customizable Dashboard (21 pts)
  - Drag-and-drop widget arrangement
  - Add/remove widgets, save layout preferences
  - Widget library with multiple chart types
- ENH-006: Modern UI/UX Redesign (34 pts)
  - Complete visual redesign with modern design system
  - Dark mode support
  - Responsive mobile-first layout
  - WCAG 2.1 AA accessibility
  - Smooth animations and professional icon set

---

### Release 4: "Supreme Shadow Monarch" 📋 PLANNED

**Goal**: AI/ML powered features  
**Sprints**: 8–9 | **Points**: 61

#### Sprint 8: Core AI Features (46 pts)
- US-029: Spending pattern analysis via ML (8 pts)
- US-030: AI-suggested budget limits from history (8 pts)
- US-031: Anomaly detection — alert on unusual spending (8 pts)
- US-032: Category auto-suggestion for new transactions (5 pts)
- US-033: Financial forecasting — predict future trends (8 pts)
- US-034: Natural language query ("How much did I spend on food?") (5 pts)
- US-035: Smart alerts for budget/goal thresholds (4 pts)

#### Sprint 9: Advanced Features (15 pts)
- US-036: Multi-currency support (5 pts)
- US-037: Receipt scanning via OCR → auto-create transaction (5 pts)
- US-038: Shared budgets for collaborative planning (5 pts)

---

### Release 5: "Fortress of Security" 📋 PLANNED

**Goal**: Harden the secure version by fixing all intentional vulnerabilities  
**Sprint**: 10 | **Points**: 82  
**Scope**: secure-version only

- SEC-001: Fix SQL injection — parameterized queries everywhere (15 pts)
- SEC-002: Fix IDOR — ownership verification on all endpoints (10 pts)
- SEC-003: Fix XSS — input sanitization and output encoding (10 pts)
- SEC-004: CSRF protection — tokens on all forms (8 pts)
- SEC-005: Comprehensive input validation (8 pts)
- SEC-006: Secure password storage — bcrypt (5 pts)
- SEC-007: Rate limiting — prevent brute force (5 pts)
- SEC-008: Audit logging — log all sensitive actions (8 pts)
- SEC-009: API authentication on all endpoints (8 pts)
- SEC-010: Automated security test suite (5 pts)

---

## ⚔️ Release 2 — Full Detail

### Sprint 3: "Stone Breathing — Third Form" ✅
**Goal**: Recurring Transactions + Account Management  
**Points**: 28/28

#### What Was Built

**Account Management**
- Account types: `checking`, `savings`, `credit_card`, `investment`, `cash`
- Each account tracks: `initial_balance`, `current_balance`, `include_in_budget` toggle, `is_active` (soft delete)
- Account page (`/accounts`) with summary cards: Net Worth, Budget Balance, Account Count
- Add/Edit/Delete accounts via AJAX modals
- Transfer modal on accounts page

**Recurring Transactions**
- Recurring transaction model with frequency: `daily`, `weekly`, `monthly`, `yearly`
- Fields: `account_id` (source), `to_account_id` (for transfers), `category_id`, `start_date`, `end_date`, `next_run_date`, `last_run_date`
- Tab-based UI: All / Active / Paused
- Dynamic modal fields: transfer-type shows `to_account`, others show `category`
- Pause/Resume toggle
- "Run Now" manual trigger button

**APScheduler Background Job**
- `BackgroundScheduler` runs every hour inside Flask app context
- Werkzeug reloader guard: only starts once even in debug mode
- For `income`/`expense` recurring: creates a `Transaction` + updates account balance
- For `transfer` recurring: creates a `Transfer` (two linked transactions) + updates both balances
- Calculates `next_run_date` using `python-dateutil relativedelta` (month-end safe)
- Deactivates recurring transaction when `next_run > end_date`

**Transaction model extended**
- Added columns: `account_id`, `is_transfer`, `recurring_transaction_id`
- `create()` lazy-imports `Account` to avoid circular import, updates balance on creation

#### Files Created / Modified — Sprint 3

| File | Action |
|------|--------|
| `models/account.py` | NEW — Account model with balance arithmetic, soft delete |
| `models/recurring_transaction.py` | NEW — RecurringTransaction model, get_due(), mark_executed() |
| `models/transaction.py` | MODIFIED — Added account_id, is_transfer, recurring_transaction_id |
| `scheduler.py` | NEW — APScheduler init with Werkzeug guard |
| `routes/accounts.py` | NEW — UI blueprint for /accounts |
| `routes/recurring.py` | NEW — UI blueprint for /recurring |
| `routes/api/accounts.py` | NEW — JSON API for account CRUD |
| `routes/api/recurring.py` | NEW — JSON API for recurring CRUD + /trigger |
| `templates/accounts/manage.html` | NEW |
| `templates/recurring/manage.html` | NEW |
| `database/init-vulnerable-sprint3.sql` | NEW — accounts, ALTER transactions, recurring_transactions |
| `app.py` | MODIFIED — registered Sprint 3 blueprints, init_scheduler() |
| `templates/base.html` | MODIFIED — added Accounts nav + More dropdown |
| `requirements.txt` | MODIFIED — added APScheduler, python-dateutil |

#### Sprint 3 Vulnerabilities

| ID | Vulnerability | Location |
|----|--------------|----------|
| VULN-028 | SQL Injection — account CRUD | account.py |
| VULN-029 | SQL Injection — recurring transactions | recurring_transaction.py |
| VULN-030 | IDOR — account management (no ownership check) | /api/accounts/* |
| VULN-031 | IDOR — recurring transaction management | /api/recurring/* |
| VULN-032 | Mass assignment — account create/update (user_id from request) | Account API |
| VULN-033 | Mass assignment — recurring create/update | Recurring API |
| VULN-034 | Business logic — get_budget_balance silently excludes non-budget accounts | account.py |
| VULN-035 | Business logic — soft delete leaves orphaned transactions and initial balance | account.py delete() |

---

### Sprint 4: "Flame Breathing — Fourth Form" ✅
**Goal**: Multi-Account Transfers, Budgets, Savings Goals  
**Points**: 30/30

#### What Was Built

**Transfers Between Accounts**
- `Transfer.create()`: atomic operation — debit transaction + credit transaction + transfer record + updates both balances
- `Transfer.delete()`: full reversal — restores both balances, removes both linked transactions + transfer record
- Transfer modal on accounts page (from → to, amount, description, date)
- `is_transfer = TRUE` flag on both linked transactions

**Monthly/Yearly Budgets**
- Budget model: `period_type` = `monthly`, `yearly`, or `custom`
- Budget categories table links a budget to categories with individual spending limits
- `set_category_limit()`: DELETE-then-INSERT to prevent duplicate entries (BUG-005 fix)
- Budget page with per-category progress bars + total budget bar
- Period auto-fill in UI: monthly fills first/last of current month, yearly fills Jan 1/Dec 31
- Dynamic "add category limit" rows in create/edit modals

**Savings Goals**
- Goals model: `target_amount`, `current_amount`, `target_date`, `monthly_target`, `status` (active/achieved/paused)
- Optional account linkage
- `progress_percent` property: `min((current/target)*100, 100)`
- `remaining_amount` property: `max(target - current, 0)`
- Circular progress display on goal cards
- Add Progress modal
- Dual-Mode Timeline Calculator:
  - **Mode A**: Enter deadline → calculates required monthly savings
  - **Mode B**: Enter monthly amount → calculates completion date

#### Files Created / Modified — Sprint 4

| File | Action |
|------|--------|
| `models/transfer.py` | NEW — Transfer model with atomic create/delete |
| `models/budget.py` | NEW — Budget model + budget_categories management |
| `models/savings_goal.py` | NEW — SavingsGoal model with progress properties |
| `routes/budgets.py` | NEW — UI blueprint for /budgets |
| `routes/goals.py` | NEW — UI blueprint for /goals |
| `routes/api/transfers.py` | NEW — JSON API for transfer CRUD |
| `routes/api/budgets.py` | NEW — JSON API for budget + category limits CRUD |
| `routes/api/savings_goals.py` | NEW — JSON API for goals CRUD + add progress |
| `templates/budgets/manage.html` | NEW |
| `templates/goals/manage.html` | NEW |
| `database/init-vulnerable-sprint4.sql` | NEW — transfers, budgets, budget_categories, savings_goals |
| `app.py` | MODIFIED — registered Sprint 4 blueprints |

#### Sprint 4 Vulnerabilities

| ID | Vulnerability | Location |
|----|--------------|----------|
| VULN-036 | SQL Injection — transfer create/delete | transfer.py |
| VULN-037 | SQL Injection — budget all methods | budget.py |
| VULN-038 | SQL Injection — savings goals all methods | savings_goal.py |
| VULN-039 | IDOR — transfer management | /api/transfers/* |
| VULN-040 | IDOR — budget management | /api/budgets/* |
| VULN-041 | IDOR — savings goal management | /api/goals/* |
| VULN-045 | Business logic — goals never auto-achieve at 100% | savings_goal.py add_progress() |

---

### Sprint 5: "Shadow Ledger" ✅
**Goal**: Export / Import / Reports  
**Points**: 33/33

#### What Was Built

**CSV Export** (`/api/export/csv`)
- Filters: user_id, date_from, date_to, type, account_id
- Intentional CSV formula injection: transaction descriptions pass through unescaped

**PDF Export** (`/api/export/pdf`)
- Generated with `reportlab`
- Table-formatted with summary row (total income, expenses, net)

**Excel Export** (`/api/export/excel`)
- Generated with `openpyxl`
- Styled header row, column widths set

**CSV Import** (`/api/export/import/csv` POST)
- File upload accepted
- Rows inserted via raw SQL (intentional SQL injection via CSV values)

**Reports Dashboard** (`/reports`)
- Date + type filter panel
- Chart.js visualizations: pie (by category), bar (by month), horizontal bar (by account)
- Category breakdown table with amount and transaction count
- Export buttons trigger file download via `window.location.href`
- Import file input with AJAX feedback

**Reports API** (`/api/export/reports/summary`)
- Returns aggregated JSON: `by_category`, `by_month`, `by_account`

#### Files Created / Modified — Sprint 5

| File | Action |
|------|--------|
| `routes/api/export.py` | NEW — all export/import/reports endpoints |
| `routes/reports.py` | NEW — UI blueprint for /reports |
| `templates/reports/index.html` | NEW |
| `requirements.txt` | MODIFIED — added reportlab, openpyxl |
| `app.py` | MODIFIED — registered Sprint 5 blueprints |

#### Sprint 5 Vulnerabilities

| ID | Vulnerability | Location |
|----|--------------|----------|
| VULN-042 | CSV injection — formula payloads in export | /api/export/csv |
| VULN-043 | SQL injection via CSV import | /api/export/import/csv |
| VULN-044 | No authentication on export/import endpoints | All /api/export/* |

---

### Bug Fixes (End of Sprint 5)

| ID | Description | Resolution |
|----|-------------|------------|
| BUG-001 | Emoji icons not supported in category field | Updated help text in add/edit modals |
| BUG-002 | Initial balance double-application | Fixed in Account.create() — balance set once |
| BUG-005 | Budget edit duplicates category limits | DELETE-then-INSERT in set_category_limit() |
| BUG-006 | Budget API returns wrong category data | Fixed JOIN in get_spending() query |
| BUG-007 | Goal card missing linked account name | accountsMap + chained loadAccounts(loadGoals) |
| BUG-009 | Goal creation type conversion error | Fixed float/int casting in SavingsGoal.create() |
| BUG-003 | Dashboard vs account balance mismatch | **Intentional** — preserved as VULN-034 |
| BUG-004 | Delete account keeps initial balance | **Intentional** — preserved as VULN-035 |
| BUG-008 | Goal status doesn't auto-achieve at 100% | **Intentional** — preserved as VULN-045 |

---

## 🗂️ Database Schema After Release 2

| Table | Sprint | Purpose |
|-------|--------|---------|
| users | 1 | Authentication |
| sessions | 1 | Session tokens |
| categories | 2 | Income/expense categories |
| transactions | 2 | All financial transactions |
| accounts | 3 | Bank accounts per user |
| recurring_transactions | 3 | Recurring transaction templates |
| transfers | 4 | Transfer records linking debit+credit |
| budgets | 4 | Budget periods |
| budget_categories | 4 | Per-category spending limits within a budget |
| savings_goals | 4 | Savings goal tracking |

---

## 📦 Python Dependencies After Release 2

```
Flask==3.0.0
Flask-MySQLdb==2.0.0
mysqlclient==2.2.0
python-dotenv==1.0.0
Werkzeug==3.0.1
APScheduler==3.10.4
python-dateutil==2.8.2
reportlab==4.1.0
openpyxl==3.1.2
```

---

## 🔢 Release 2 Metrics

| Metric | Value |
|--------|-------|
| Story Points Completed | 91 / 91 (100%) |
| User Stories | 14 |
| New Models | 5 |
| New Blueprints | 11 |
| New Templates | 5 pages |
| New SQL Tables | 6 |
| New API Endpoints | ~20 |
| New Vulnerabilities | 18 |
| Total Vulnerabilities | 45 |
| Bug Fixes | 6 fixed + 3 preserved as intentional |

---

## 🚀 Next: Release 3 "Shadow Evolution"

First sprint up: **Sprint 6 — Core Enhancements**
- Auto goal progress via account transfers
- Global default categories
- Recurring transaction templates
- Category icon/color full customization

Then: **Sprint 7 — UX & Visual Design** (UI redesign, dark mode, drag-and-drop dashboard)

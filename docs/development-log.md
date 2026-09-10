# 📝 Aura - Development Log

Sprint-by-sprint development progress and decisions.

---

## 🎌 Release 1: "Hashira Foundation" (Demon Slayer)

**Goal**: Build core infrastructure and authentication system  
**Status**: 🚧 In Progress

---

## 🌊 Sprint 1: "Water Breathing - First Form"

**Duration**: Week 1  
**Sprint Goal**: Development environment setup + User authentication system (both versions)  
**Status**: ✅ COMPLETE

### 📅 Sprint Timeline

- **Start Date**: Day 1
- **End Date**: Day 2
- **Sprint Length**: 1 week

---

### ✅ Completed User Stories

#### **US-001: Docker and Docker Compose Configuration** ✅
- **Status**: COMPLETE
- **Story Points**: 3
- **Acceptance Criteria**:
  - ✅ Dockerfile created for both versions
  - ✅ docker-compose.yml created
  - ✅ All containers configured to communicate
  - ✅ Different ports for secure (5000) and vulnerable (5001) versions
  - ✅ Separate MySQL databases for each version

**Files Created**:
- `docker-compose.yml`
- `secure-version/Dockerfile`
- `vulnerable-version/Dockerfile`
- `secure-version/requirements.txt`
- `vulnerable-version/requirements.txt`

**Key Decisions**:
- Used separate MySQL containers (ports 3306 and 3307)
- Used separate Flask containers (ports 5000 and 5001)
- Persistent volumes for database data
- Bridge network for container communication

---

#### **US-002: MySQL Database Schema** ✅
- **Status**: COMPLETE
- **Story Points**: 2
- **Acceptance Criteria**:
  - ✅ Database initialization scripts created
  - ✅ Users table structure defined for both versions
  - ✅ Sessions table added for session management
  - ✅ Database tables created automatically on container startup
  - ✅ Test users inserted

**Files Created**:
- `database/init-secure.sql`
- `database/init-vulnerable.sql`

**Schema Design**:

**Secure Version**:
- Users table with proper constraints (UNIQUE, NOT NULL)
- Password stored as bcrypt hash (VARCHAR 255)
- Failed login attempts tracking
- Indexed columns (username, email)
- Foreign key constraints
- Session expiration tracking

**Vulnerable Version**:
- Users table without proper constraints
- Password stored in plaintext
- No unique constraints (duplicate usernames/emails allowed)
- No indexes
- No foreign key constraints
- No session expiration

**Vulnerabilities Introduced**:
- 🔴 Plaintext password storage
- 🔴 No unique constraints
- 🟡 Missing foreign key constraints
- 🟡 No session expiration

---

#### **US-003: Basic Flask Application Structure** ✅
- **Status**: COMPLETE
- **Story Points**: 5
- **Acceptance Criteria**:
  - ✅ app.py created for both versions
  - ✅ routes folder with blueprints
  - ✅ templates folder with HTML files
  - ✅ static folder with CSS/JS
  - ✅ Flask app runs successfully in Docker container

**Files Created**:
- `config.py` (both versions)
- `app.py` (both versions)
- `models/user.py` (both versions)
- `routes/auth.py` (both versions)
- `routes/main.py` (both versions)
- `utils/security.py` (both versions)
- All HTML templates
- CSS and JavaScript files

**Application Structure**:
- Blueprint-based routing (auth, main)
- Model-based architecture
- Template inheritance (base.html)
- Separate configurations for secure/vulnerable

---

#### **US-004: User Registration (Secure Version)** ✅
- **Status**: COMPLETE
- **Story Points**: 5
- **Acceptance Criteria**:
  - ✅ Registration form with validation
  - ✅ Password hashing (bcrypt)
  - ✅ Server-side input validation
  - ✅ SQL parameterized queries (SQL injection protection)
  - ✅ Password strength requirements

**Security Features Implemented**:
- Bcrypt password hashing (12 rounds)
- Input sanitization (XSS protection)
- Username validation (alphanumeric + underscore, 3-20 chars)
- Email validation (regex)
- Password requirements:
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one digit
  - At least one special character
- Password confirmation check
- SQL parameterized queries
- Duplicate username/email check

---

#### **US-005: User Registration (Vulnerable Version)** ✅
- **Status**: COMPLETE
- **Story Points**: 3
- **Acceptance Criteria**:
  - ✅ Registration form without CSRF protection
  - ✅ Plaintext password storage
  - ✅ SQL injection vulnerabilities
  - ✅ No input validation
  - ✅ Weak passwords accepted

**Vulnerabilities Introduced**:
- 🔴 **SQL Injection**: String concatenation in queries
- 🔴 **Plaintext Password Storage**: No hashing
- 🔴 **No Input Validation**: Accepts any input
- 🟡 **No CSRF Protection**: Missing tokens
- 🟢 **Weak Passwords**: Accepts "123", "password", etc.
- 🟡 **XSS**: No input sanitization
- 🟡 **Information Disclosure**: Detailed error messages

**Exploitation Examples**:
```sql
-- SQL Injection in registration
Username: admin' OR '1'='1
Email: test@test.com
Password: anything
```

---

#### **US-006: User Login/Logout (Both Versions)** ✅
- **Status**: COMPLETE
- **Story Points**: 8
- **Acceptance Criteria**:
  - ✅ Login form created
  - ✅ Session management implemented
  - ✅ Logout functionality
  - ✅ Secure version: Rate limiting, secure sessions
  - ✅ Vulnerable version: SQL injection, weak sessions

**Secure Version Features**:
- Bcrypt password verification
- Failed login attempt tracking (max 5 attempts)
- Account lockout after failed attempts
- Secure session tokens (cryptographically secure)
- Session expiration (2 hours)
- HTTPOnly cookies
- Secure cookie flag
- SameSite cookie attribute
- Session validation on each request
- Input sanitization

**Vulnerable Version Features**:
- Plaintext password comparison
- No rate limiting (unlimited attempts)
- Predictable session tokens (user_id + random 4 digits)
- No session expiration (365 days)
- No secure cookie flags
- No session validation
- SQL injection in login query
- Password stored in session
- Debug endpoint exposing session data

**Vulnerabilities Introduced**:
- 🔴 **SQL Injection**: Login bypass with `' OR '1'='1`
- 🔴 **No Rate Limiting**: Brute force attacks possible
- 🟡 **Predictable Session Tokens**: Can be guessed
- 🟡 **Session Fixation**: No token regeneration
- 🟡 **XSS**: Username reflected without sanitization
- 🟡 **Information Disclosure**: Debug endpoint at `/auth/debug/session`

**Exploitation Examples**:
```sql
-- SQL Injection login bypass
Username: admin' OR '1'='1' --
Password: anything

-- Session hijacking
Session Token Pattern: session_[user_id]_[4-digit-random]
Example: session_1_1234, session_1_1235, etc.
```

---

#### **US-007: Documentation** ✅
- **Status**: COMPLETE
- **Story Points**: 2
- **Acceptance Criteria**:
  - ✅ README.md with setup instructions
  - ✅ Setup guide created
  - ✅ Development log created
  - ✅ Another developer can set up the project

**Files Created**:
- `README.md`
- `docs/setup-guide.md`
- `docs/development-log.md`
- Error templates (404.html, 500.html)

---

### 🎯 Sprint Metrics

**Total User Stories**: 7  
**Completed**: 7 (100%)  
**Story Points Completed**: 28  
**Velocity**: 28 points/sprint

**Time Breakdown**:
- Planning: Day 1 (2-3 hours)
- Development: Day 2 (3-4 hours)
- Documentation: Day 2 (1 hour)
- Testing: Day 2 (planned - 1-2 hours)

---

### 🔧 Technical Decisions

#### **Decision 1: Dual Codebase Strategy**
- **Decision**: Maintain separate secure and vulnerable versions
- **Rationale**: 
  - Clearer separation of concerns
  - Easier to compare implementations
  - Better for learning (see differences side-by-side)
  - Safer (no accidental deployment of vulnerable code)
- **Alternative Considered**: Single codebase with feature flags
- **Status**: ✅ Approved

#### **Decision 2: Focus on Vulnerable Version First**
- **Decision**: Complete vulnerable version before secure version
- **Rationale**:
  - More efficient use of resources (fewer tokens)
  - Faster development
  - Can practice pentesting immediately
  - Secure version becomes "remediation" phase
- **Alternative Considered**: Build both simultaneously
- **Status**: ✅ Approved (Day 2)

#### **Decision 3: Docker-based Development**
- **Decision**: Use Docker Compose for local development
- **Rationale**:
  - Consistent environment across systems
  - Easy database management
  - Production-like setup
  - Kubernetes migration path
- **Alternative Considered**: Local Python virtual environment
- **Status**: ✅ Approved

#### **Decision 4: Blueprint Architecture**
- **Decision**: Use Flask blueprints for routing
- **Rationale**:
  - Better code organization
  - Modular design
  - Easier to add features
  - Follows Flask best practices
- **Status**: ✅ Approved

---

### 📚 Lessons Learned

#### What Went Well ✅
1. Clear requirements gathering prevented scope creep
2. Docker setup made environment consistent
3. Dual version approach provides clear learning path
4. SQL injection vulnerabilities easy to implement and test
5. Bootstrap made UI development fast

#### What Could Be Improved 🔄
1. Initially created both versions simultaneously (inefficient)
2. Could have planned vulnerabilities more systematically upfront
3. Some redundant code between secure/vulnerable versions

#### Action Items for Next Sprint 📋
1. Document vulnerabilities as we build features
2. Create pentester guide progressively
3. Add automated testing
4. Consider shared utilities between versions

---

### 🐛 Issues & Resolutions

#### Issue 1: Port Conflicts
- **Problem**: MySQL port 3306 already in use on host
- **Solution**: Used port 3307 for vulnerable MySQL
- **Status**: ✅ Resolved

#### Issue 2: Database Initialization Timing
- **Problem**: Flask app starting before MySQL ready
- **Solution**: Added `depends_on` in docker-compose.yml
- **Status**: ✅ Resolved

---

### 📊 Code Statistics

**Lines of Code** (approximate):
- Python: ~1,200 lines
- HTML: ~800 lines
- CSS: ~400 lines
- JavaScript: ~300 lines
- SQL: ~150 lines
- **Total**: ~2,850 lines

**Files Created**: 45+

---

### 🎯 Sprint Retrospective

#### What We Accomplished
- ✅ Complete authentication system (both versions)
- ✅ Docker environment fully configured
- ✅ Database schemas designed and implemented
- ✅ Multiple vulnerability types introduced
- ✅ Full documentation created
- ✅ Ready for testing

#### Sprint Goal Achievement
**Status**: ✅ **ACHIEVED** - All planned user stories completed

#### Team Satisfaction
**Rating**: 5/5 - Excellent progress, clear goals, good collaboration

---

### 🚀 Next Sprint Preview

**Sprint 2: "Thunder Breathing - Second Form"** (Upcoming)

**Planned Features**:
- Transaction management (manual entry)
- Expense categorization (create/edit/delete)
- Income categorization (create/edit/delete)
- Dashboard with transaction display
- More vulnerabilities (IDOR, XSS in transactions, CSV injection)

**Estimated Story Points**: 30-35 points

---

### 📝 Notes

- Secure version files created but focusing on vulnerable version first
- Pentester guide and vulnerability matrix will be created progressively
- GitHub repository configured and ready for first commit
- Testing session scheduled after documentation completion

---

**Last Updated**: Sprint 1, Day 2  
**Next Update**: Sprint 1 Retrospective (after testing)

---

## 📅 **Sprint 2: "Thunder Breathing - Second Form"** ⚡

**Dates**: Day 4 - Day 7  
**Status**: ✅ **COMPLETE**  
**Story Points**: 26/26 (100%)

### **User Stories Completed:**

1. ✅ **US-008**: Manual Transaction Entry (8 pts)
   - Transaction form with modal
   - AJAX submission
   - Category filtering by type
   - Full CRUD via API

2. ✅ **US-009**: Expense Categorization (5 pts)
   - Category management page
   - Add/Edit/Delete categories
   - Color picker integration

3. ✅ **US-010**: Income Categorization (3 pts)
   - Income categories tab
   - Same CRUD as expenses

4. ✅ **US-011**: Dashboard with Charts (6 pts)
   - Summary cards (Income, Expenses, Balance)
   - Chart.js bar chart (Income vs Expenses by month)
   - Chart.js pie chart (Expenses by category)
   - Filters (date range, category, type)
   - Recent transactions table

5. ✅ **US-012**: Edit/Delete Transactions (4 pts)
   - Edit modal with pre-filled data
   - Delete with SweetAlert2 confirmation
   - AJAX operations

### **Technical Achievements:**

**Backend:**
- 11 new API endpoints (RESTful JSON)
- 2 new models (Transaction, Category)
- 2 new blueprints (transactions, categories)
- Separate `/api/` route structure

**Frontend:**
- 3 new pages (transactions, categories, updated dashboard)
- 4 interactive modals
- Chart.js integration (2 chart types)
- SweetAlert2 notifications throughout
- Color picker implementation
- Dynamic AJAX filtering

**Vulnerabilities Added:**
- 13 new vulnerabilities (4 critical, 6 high/medium, 3 low)
- Total: 27 vulnerabilities across application

### **Testing Results:**
- Functional tests: 25/25 passed ✅
- Vulnerability tests: 20/20 confirmed exploitable ✅
- No critical bugs found
- 1 enhancement logged (category colors in tables)

### **Metrics:**
- Files Created: 25+
- Lines of Code: ~2,500
- API Endpoints: 11
- Modals: 4
- Charts: 2
- Days Ahead of Schedule: 3

### **Lessons Learned:**

**What Went Well:**
- ✅ Finished development 3 days early!
- ✅ All features working on first attempt
- ✅ Clean API architecture
- ✅ Professional UI with good UX
- ✅ All vulnerabilities exploitable
- ✅ Testing process well-organized

**Challenges:**
- Emoji encoding issue (workaround implemented)
- Category color consistency (enhancement for later)

**Decisions Made:**
- Used separate `/api/` routes for cleaner architecture
- Chose SweetAlert2 over native alerts
- Implemented hybrid modal + AJAX approach
- Minimal animations for stability

### **Next Steps:**
- Update pentester guide with new vulnerabilities
- Git commit Sprint 2 work
- Begin Sprint 3 planning

---

## ⚔️ **Release 2: "Shadow Extractor"** — Sprints 3, 4, 5

**Status**: ✅ **COMPLETE**  
**Story Points**: 91/91 (100%)  
**Date Completed**: 2026-06-17

---

## 🔄 **Sprint 3: "Stone Breathing - Third Form" — Recurring Transactions**

**Status**: ✅ **COMPLETE** (28 pts)

### **User Stories Completed:**

1. ✅ **US-014**: Create Recurring Transaction (8 pts)
   - Recurring transaction model with frequency support (daily/weekly/monthly/yearly)
   - Account linking for debit/credit source
   - Transfer-type recurring transactions with to_account_id
   - APScheduler background job fires hourly to auto-generate due transactions

2. ✅ **US-015**: View Recurring Transactions (5 pts)
   - Tab-based UI: All / Active / Paused
   - Table with next_run_date, frequency, amount, type display

3. ✅ **US-016**: Edit/Delete Recurring (5 pts)
   - Edit modal with dynamic fields (transfer shows to_account, others show category)
   - Pause/Resume toggle
   - Delete with confirmation

4. ✅ **US-017**: Auto-Generate from Recurring (10 pts)
   - APScheduler `BackgroundScheduler` with hourly interval
   - Werkzeug reloader guard: only starts if not already running
   - income/expense: creates Transaction + updates account balance
   - transfer: creates Transfer (dual linked transactions) + updates both balances
   - Calculates next_run_date using `python-dateutil relativedelta`
   - Deactivates when next_run exceeds end_date
   - "Run Now" manual trigger via `/api/recurring/trigger`

### **Technical Achievements:**
- `models/account.py`: Account model with soft delete, balance arithmetic
- `models/recurring_transaction.py`: RecurringTransaction model with get_due(), mark_executed()
- `scheduler.py`: APScheduler init with app context binding
- `database/init-vulnerable-sprint3.sql`: accounts table + ALTER transactions table + recurring_transactions table

### **Vulnerabilities Added (Sprint 3):**
- VULN-028: SQL Injection in account.py (all CRUD)
- VULN-029: SQL Injection in recurring_transaction.py
- VULN-030: IDOR — account management (no ownership check)
- VULN-031: IDOR — recurring transaction management
- VULN-032: Mass assignment on account create/update (user_id from request)
- VULN-033: Mass assignment on recurring create/update
- VULN-034: Business logic — get_budget_balance excludes non-budget accounts silently
- VULN-035: Business logic — soft delete leaves orphaned transactions/balances

---

## 💰 **Sprint 4: "Flame Breathing - Fourth Form" — Multi-Account & Budget**

**Status**: ✅ **COMPLETE** (30 pts)

### **User Stories Completed:**

1. ✅ **US-018**: Multiple Bank Accounts (8 pts)
   - Account types: checking, savings, credit_card, investment, cash
   - Include/Exclude from budget toggle
   - Net Worth vs Budget Balance separation
   - Account management page with summary cards

2. ✅ **US-019**: Transfer Between Accounts (6 pts)
   - Creates TWO linked transactions (debit + credit) + one transfer record
   - Updates both account balances atomically
   - Transfer reversal on delete (full balance recovery)

3. ✅ **US-020**: Monthly Budget Planning (7 pts)
   - Budget model: monthly/yearly/custom period types
   - Per-category spending limits via budget_categories table
   - Auto-fill period dates in UI (monthly → first/last of month)

4. ✅ **US-021**: Budget Tracking & Alerts (4 pts)
   - Progress bars per category (actual vs limit)
   - Total budget progress bar
   - Spending data via JOIN across budgets→categories→transactions

5. ✅ **US-022**: Savings Goals with Timeline (5 pts)
   - Savings goal with target_amount, current_amount, target_date
   - Account linkage (optional)
   - Dual-Mode Timeline Calculator:
     - Mode A: Set deadline → Calculate monthly target
     - Mode B: Set monthly amount → Calculate completion date

### **Technical Achievements:**
- `models/transfer.py`: Transfer model with atomic create/delete
- `models/budget.py`: Budget + budget_categories, set_category_limit with dedup
- `models/savings_goal.py`: SavingsGoal with progress_percent / remaining_amount properties
- `database/init-vulnerable-sprint4.sql`: transfers, budgets, budget_categories, savings_goals tables

### **Vulnerabilities Added (Sprint 4):**
- VULN-036: SQL Injection in transfer.py
- VULN-037: SQL Injection in budget.py (all methods)
- VULN-038: SQL Injection in savings_goal.py
- VULN-039: IDOR — transfer management
- VULN-040: IDOR — budget management
- VULN-041: IDOR — savings goal management
- VULN-045: Business logic — savings goals never auto-achieve (intentional)

---

## 📊 **Sprint 5: "Shadow Ledger" — Export / Import / Reports**

**Status**: ✅ **COMPLETE** (33 pts)

### **User Stories Completed:**

1. ✅ **US-023**: Export Transactions to CSV (5 pts)
   - `/api/export/csv` GET with filters (user_id, date_from, date_to, type, account_id)
   - CSV formula injection intentionally preserved (VULN-042)

2. ✅ **US-024**: Export Transactions to PDF (7 pts)
   - `/api/export/pdf` GET using `reportlab`
   - Table-formatted PDF with summary row

3. ✅ **US-025**: Export Transactions to Excel (5 pts)
   - `/api/export/excel` GET using `openpyxl`
   - Styled header row

4. ✅ **US-026**: Import Transactions from CSV (8 pts)
   - `/api/export/import/csv` POST with file upload
   - SQL injection via raw CSV values (VULN-043)

5. ✅ **US-027**: Advanced Filtering & Reports (8 pts)
   - Reports dashboard with Chart.js (pie/bar/horizontal bar)
   - Category breakdown table
   - `/api/export/reports/summary` aggregated JSON endpoint

### **Bug Fixes (End of Sprint 5):**
- ✅ BUG-001: Emoji icons in category field — updated help text
- ✅ BUG-002: Initial balance double-application — fixed in Sprint 3 model
- ✅ BUG-005: Budget edit duplicates category limits — DELETE-then-INSERT
- ✅ BUG-006: Budget API returns wrong category data — fixed in Sprint 4
- ✅ BUG-007: Goal card missing linked account name — accountsMap + chained load
- ✅ BUG-009: Goal creation type conversion error — fixed in Sprint 4 model
- 🔒 BUG-003, BUG-004, BUG-008: Intentional vulnerabilities — preserved

### **Vulnerabilities Added (Sprint 5):**
- VULN-042: CSV injection — formula payloads survive export
- VULN-043: SQL injection via CSV import (file upload)
- VULN-044: No authentication on export/import endpoints

### **Technical Decisions:**
- APScheduler chosen over Flask-APScheduler for direct control
- Werkzeug reloader guard prevents double scheduler start in debug mode
- Lazy import in transaction.py avoids circular import with account.py
- `python-dateutil` relativedelta for month-end-safe date arithmetic

---

### 📊 **Release 2 Metrics**

| Metric | Value |
|--------|-------|
| Story Points | 91 / 91 |
| User Stories | 14 |
| New Models | 5 (account, recurring_transaction, transfer, budget, savings_goal) |
| New Routes | 11 blueprints |
| New Templates | 5 pages |
| New SQL Tables | 6 (accounts, recurring_transactions, transfers, budgets, budget_categories, savings_goals) |
| New Vulnerabilities | 18 |
| Total Vulnerabilities | 45 |
| New API Endpoints | ~20 |
| Bug Fixes | 6 |

**Last Updated**: 2026-06-17  
**Next Release**: Release 3 "Shadow Evolution" (Sprint 6-7)

---

## ⚡ **Release 3: "Crystal Vision"** — Sprints 6, 7, 8

**Status**: 🚧 IN PROGRESS (Sprint 8 testing pending)
**Goal**: UI excellence, UX enhancements, multi-dashboard analytics system
**Scope**: `vulnerable-version/` primary; `secure-version/` UI deferred

---

## 🌿 **Sprint 6: "Shadow Evolution — Core Enhancements"**

**Dates**: 2026-06-17 (same session as Sprint 7 planning)
**Status**: ✅ **COMPLETE** (8 pts)
**Scope**: `vulnerable-version/` DB enhancements only

### **What Was Built:**

1. ✅ **ENH-007**: Global Default Categories (5 pts)
   - Added `is_default BOOLEAN` column to `categories` table
   - Modified `user_id` to allow NULL for system-wide defaults
   - Seeded 15 global default categories (10 expense, 5 income) via `INSERT IGNORE`
   - Updated `category.py` to include `is_default = TRUE AND user_id IS NULL` in queries

2. ✅ **ENH-002**: Recurring Transaction Templates (3 pts)
   - Added `is_template BOOLEAN` column to `recurring_transactions` table
   - `get_templates_by_user` method added to recurring model

### **Files Changed:**
- `database/init-vulnerable-sprint6.sql` — new sprint schema file
- `vulnerable-version/models/category.py` — updated `get_all_by_user`, `get_by_id`
- `vulnerable-version/models/recurring_transaction.py` — updated `_from_row`, `get_all_by_user`, `get_templates_by_user`, `get_due`

### **Known Issue (Fixed in Sprint 7 Session 2):**
- `ADD COLUMN IF NOT EXISTS` is MariaDB syntax, rejected by MySQL 8.0. Both columns failed to be created silently. Fixed by removing `IF NOT EXISTS` and adding Python-level fallback queries.

---

## 🌙 **Sprint 7: "Moon Breathing — Seventh Form" — UI Design System**

**Dates**: 2026-06-17 → 2026-06-18  
**Status**: ✅ **COMPLETE**  
**Story Points**: 38/38 (100%)  
**Scope**: `vulnerable-version/` only

---

### Session 1 — 2026-06-17

#### What Was Built

**New static files (created from scratch):**
- `vulnerable-version/static/css/theme.css` — 5 complete theme token sets using CSS custom properties on `[data-theme]` attribute. Themes: Midnight, Aurora, Lagoon, Ember, Liquid Glass.
- `vulnerable-version/static/css/glass.css` — Full glassmorphism component library: blob layer, glass sidebar, glass cards, spring hover animations (`cubic-bezier(0.34, 1.50, 0.64, 1)`), glass buttons, glass modals, caustic shimmer `::before` animations, progress bars, nav tabs, glass badges, glass spinner, glass divider.
- `vulnerable-version/static/js/theme-switcher.js` — Theme switching (reads/writes `data-theme` on `<html id="app">`), persists in `localStorage`, renders swatch panel, marks active nav links.

**Templates fully rewritten:**
- `base.html` — Blob layer + fixed glass sidebar with grouped nav + `main-content` scroll area. All intentional vulnerabilities (`{{ session.username|safe }}`, `{{ message|safe }}`, debug footer) preserved.
- `dashboard.html` — Stat cards, Chart.js with `cssVar()` helper for theme-aware colors, badge pills for transaction types (no row highlighting).
- `login.html`, `register.html`, `profile.html`, `admin.html`, `index.html`
- `accounts/manage.html`, `budgets/manage.html`, `goals/manage.html`, `recurring/manage.html`, `reports/index.html`, `categories/manage.html`, `transactions/list.html`
- `404.html`, `500.html`

#### Key Design Decisions Made This Session

| Decision | Rationale |
|---|---|
| No solid opaque button fills — all glass tinted | User confirmed: semantic meaning via badge/text only, not button color |
| All border-top use `var(--rim)` uniformly | User confirmed: no per-semantic border colors anywhere |
| Global `color: var(--tp)` override via `body, body *` | User confirmed: all text white across all themes |
| Transaction row coloring removed (`table-success`/`table-danger`) | User confirmed: type indicated via badge pill + amount color only |
| Progress bars keep `bg-danger`/`bg-warning` for over-budget states | These are informational severity levels, not button/UI colors — acceptable |
| Reports charts use `cssVar()` helper on load and on Generate | Ensures charts re-theme when user switches theme mid-session |

#### Issues Resolved

1. **Red "Get Started" button** — Bootstrap `.btn-danger` text color was `var(--dn)`. Fix: `color: var(--tp) !important` on all `.btn-*` overrides.
2. **Colored top borders** — Some modal buttons and alert cards had per-semantic `border-top` colors. Fix: all unified to `var(--rim)`.
3. **Dark text in Liquid Glass** — `--tp` was set to near-black for that theme. Fix: updated to `rgba(255,255,255,0.95)`.
4. **Table row highlights persisting** — Bootstrap `table-success`/`table-danger` applied from JS. Fix: glass.css override strips both `background-color` and `--bs-table-bg-state`.
5. **Orphaned `{% endblock %}` in `categories/manage.html`** — Jinja template bug fixed during rewrite.

#### What Is NOT Done Yet

- **User manual testing** — A full test checklist was provided at the end of the session. Until tested, Sprint 7 is not closed.
- **Secure version** — Identical UI changes deferred until vulnerable version is confirmed working.
- **Icons** — Deferred (SVG vs library decision pending).
- **Color palette discussion** — User indicated they want to discuss additional palette options after the 5 current themes are confirmed working.

---

### 🔜 Next Session Plan

1. User reports any issues found during manual testing
2. Fix any regressions found
3. Confirm Sprint 7 complete (close sprint)
4. Discuss: additional color palettes / icon approach
5. Apply identical UI changes to `secure-version/`

---

### Session 2 — 2026-06-18

#### What Was Completed

**Remaining template rewrites (S7-R9 through S7-R13):**
- `dashboard.html` — glass stat cards, Chart.js with Abyss palette, recent transactions table (S7-R9)
- `transactions/list.html`, `categories/manage.html` — full glass system (S7-R10)
- `accounts/manage.html`, `budgets/manage.html`, `goals/manage.html`, `recurring/manage.html`, `reports/index.html` — `.glass-grid`, `.stat-card`, `.glass-table`, JS card builders using direct `.glass-card` elements (S7-R11)
- `login.html`, `register.html`, `profile.html`, `admin.html`, `index.html` — centered glass layouts, `glass-card no-hover`, glass form inputs (S7-R12)
- `404.html`, `500.html` — centered error pages with glass card (S7-R13)

All intentional vulnerabilities preserved verbatim across every template.

**Database schema fixes:**
- `database/init-vulnerable-sprint6.sql` — replaced both `ADD COLUMN IF NOT EXISTS` statements (MariaDB-only syntax) with plain `ADD COLUMN`. MySQL 8.0 was silently rejecting the MariaDB syntax, halting Sprint 6's entire SQL block and preventing `is_default` and `is_template` columns from ever being created.
- Added `ALTER TABLE categories MODIFY COLUMN user_id INT NULL` before global default category inserts.

**Bug fixes (6 total):**

| ID | File(s) | Fix |
|----|---------|-----|
| BUG-S7-01 | `static/css/glass.css` | Removed `z-index:1` + `mask-image` from `.main-content` — both created CSS stacking contexts trapping Bootstrap modals below the backdrop |
| BUG-S7-02 | `init-vulnerable-sprint6.sql`, `models/category.py` | Fixed `ADD COLUMN IF NOT EXISTS` SQL; added fallback query in `get_all_by_user` |
| BUG-S7-03 | `init-vulnerable-sprint6.sql`, `models/recurring_transaction.py` | Same as BUG-S7-02 for `is_template`; fallbacks added to `get_all_by_user`, `get_templates_by_user`, `get_due` |
| BUG-S7-04 | `models/category.py` | `get_by_id`: `result[5]` (created_at) → `result[7]` (is_default) |
| BUG-S7-05 | `models/recurring_transaction.py` | `_from_row`: `row[15]` (updated_at) → `row[16]` (is_template) |
| BUG-S7-06 | `app.py` | 404/500 handlers: raw f-string → `render_template()` |

#### User Testing Sign-Off

All pages manually tested and confirmed working:
- ✅ Categories — create, list (income + expense tabs)
- ✅ Transactions — create, list, edit, delete
- ✅ Accounts — create, list, transfer
- ✅ Budgets — create, category limits, progress tracking
- ✅ Goals — create, progress tracking, timeline calculator
- ✅ Recurring — create, list, edit, delete, templates
- ✅ Reports — filters, charts, export

#### Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Removed scroll edge mask (`mask-image`) from `.main-content` | The mask creates a CSS stacking context, trapping Bootstrap modals below the backdrop. The visual effect (content fade-in on scroll) was sacrificed to fix modal interactivity. |
| Inner try/except fallback queries in models | Makes the app work against the current running DB (missing columns) without requiring a rebuild. Full functionality restored after next `docker compose down -v && up`. |
| JS card builders: `.glass-card` as direct grid item | Removed the Bootstrap `col-md-X` wrapper div pattern. Cards are now appended directly to `.glass-grid` containers as `.glass-card` elements, matching the CSS grid model. |

---

## 🔥 **Sprint 8: "Flame Breathing — Eighth Form" — Multi-Dashboard System**

**Dates**: 2026-06-19
**Status**: ✅ **COMPLETE**
**Story Points**: 47 pts estimated
**Scope**: `vulnerable-version/` only
**Covers**: ENH-003 (Budget vs Actual Charts) + ENH-005 (Customizable Dashboard)

---

### **Background — Excel Analysis**

Before planning Sprint 8, a real personal budget Excel file (`Personal_Financial_Management.xlsx`, 2022–2026 data) was analysed. Key findings:
- The user tracks 11 expense categories across 4 years
- **Financial Obligations** (mortgage + loans) represent ~50% of total annual expenses
- The user runs explicit goal-based savings (Holiday, Investment, Extra Loan Repayments)
- The Excel dashboard sheets use: Annual Expense Distribution Pie + Income-Expense-Savings Chart
- 7 new dashboard types identified from the data (heatmap, trend lines, savings goals, etc.)

This analysis directly shaped the 4 pre-built dashboards and 12 widgets designed for Sprint 8.

---

### **Design Decisions Made**

| Decision | Choice | Rationale |
|---|---|---|
| Dashboard type | 4 pre-built named dashboards | CRUD creation (ENH-006) deferred — pre-built covers real use cases |
| Widget time filter | Per-widget (Option B) | Different dashboards need different default time windows |
| Widget states | Minimized / Maximized | Simpler than drag-and-drop; minimized shows a key metric |
| Dashboard selector | Tab bar | Clear navigation context |
| Widget customization | Toggle on/off per dashboard | Show/hide without deleting |

---

### **The 4 Pre-Built Dashboards**

| Dashboard | Widgets |
|---|---|
| Monthly Overview | Income vs Expenses bar, Expense donut, Recent transactions |
| Savings & Goals | Savings goals progress, Budget vs Actual, Potential to save |
| Spending Analysis | Category heatmap, Top 5 trend lines, Fixed vs Variable split |
| Loan & Obligations | Obligations monthly bar, Extra repayments YTD, Debt payments metric |

---

### **New Files Created**

| File | Purpose |
|---|---|
| `database/init-vulnerable-sprint8.sql` | `dashboards` + `dashboard_widgets` tables |
| `vulnerable-version/models/dashboard.py` | Dashboard model — `get_all_by_user`, `set_active`, `create_defaults_for_user` |
| `vulnerable-version/models/dashboard_widget.py` | DashboardWidget model — `get_by_dashboard`, `update_state` + WIDGET_REGISTRY |
| `vulnerable-version/routes/api/dashboards.py` | REST API — list dashboards, activate, list/update widgets |
| `vulnerable-version/routes/api/reports_data.py` | 9 data endpoints — all accept `?period=1M/3M/6M/1Y/ALL` |
| `vulnerable-version/static/js/dashboard.js` | Full dashboard JS — tabs, widget shells, 12 renderers, period change, minimize/maximize |

### **Files Modified**

| File | Change |
|---|---|
| `vulnerable-version/app.py` | +2 blueprint registrations (`api_dashboards_bp`, `api_reports_data_bp`) |
| `vulnerable-version/templates/dashboard.html` | Full rewrite — tab bar, widget grid, customize panel |
| `vulnerable-version/static/css/glass.css` | +Widget system CSS — tabs, period-bar, widget-card, minimize-btn, customize-pill |

### **Report Data Endpoints (all under `/api/reports-data/`)**

| Endpoint | Widget(s) |
|---|---|
| `/income-expense?period=` | W1 — grouped bar chart |
| `/expense-distribution?period=` | W2 — donut chart |
| `/category-heatmap?period=` | W7 — heatmap grid |
| `/top-categories?period=` | W8 — multi-line trend |
| `/fixed-variable?period=` | W9 — stacked bar |
| `/obligations?period=` | W10, W11, W12 — obligations data |
| `/potential-to-save?period=` | W6 — net metric + line chart |
| `/savings-goals` | W4 — progress bars |
| `/budget-vs-actual?period=` | W5 — grouped bar vs limits |

### **Vulnerabilities (preserved pattern)**
All new endpoints follow the intentional vulnerability pattern established in earlier sprints:
- SQL Injection via direct f-string formatting (user_id, period, widget_id)
- IDOR — no ownership verification on dashboard_id or widget_id
- No authentication checks on any `/api/` endpoint
- Widget auto-seed triggered without session validation
- `time_period` field not validated against allowed values

### **User Testing Sign-Off**

All 4 dashboards manually tested and confirmed working:
- ✅ Monthly Overview — Income vs Expenses bar, Expense donut, Recent transactions
- ✅ Savings & Goals — Savings goals progress, Budget vs Actual, Potential to save
- ✅ Spending Analysis — Category heatmap, Top 5 trend lines, Fixed vs Variable
- ✅ Loan & Obligations — Obligations monthly, Extra repayments YTD, Debt payments metric
- ✅ Per-widget time period selector (1M / 3M / 6M / 1Y / ALL)
- ✅ Widget minimize / maximize
- ✅ Widget enable / disable via Customize panel

---

## 💨 **Sprint 9: "Wind Breathing — Ninth Form" — Full CRUD Dashboard Creation**

**Date**: 2026-06-19
**Status**: ✅ **COMPLETE**
**Story Points**: 18/18 (100%)
**Scope**: `vulnerable-version/` only
**Covers**: ENH-006 (Full CRUD Dashboard Creation)

---

### **What Was Built**

#### Backend — Dashboard CRUD

| Endpoint | Description |
|---|---|
| `POST /api/dashboards/create` | Create a new named dashboard; auto-activates; deactivates others |
| `PUT /api/dashboards/<id>/update` | Rename dashboard / update description |
| `DELETE /api/dashboards/<id>/delete` | Delete dashboard + CASCADE all its widgets |
| `POST /api/dashboards/<id>/widgets/add` | Add a widget by type; uses default period + next position |
| `DELETE /api/dashboards/<id>/widgets/<wid>/remove` | Permanently remove a widget |

#### Backend — Model Updates

- **`models/dashboard.py`** — added `create()`, `update()`, `delete()` static methods
- **`models/dashboard_widget.py`** — added `add_to_dashboard()`, `remove()` static methods; `WIDGET_DEFAULT_PERIODS` constant for all 12 widget types

#### Frontend

- **Tab bar** — `+` button triggers Create Dashboard modal; ✏ and 🗑 buttons appear on active tab
- **Create/Edit Dashboard Modal** — glass-styled Bootstrap modal; name + description fields; same modal reused for create and edit
- **Delete Dashboard** — SweetAlert2 confirmation showing dashboard name; switches to first remaining dashboard on confirm
- **Customize Panel** — extended with two sections: widget toggle panel (existing) + Add Widget card grid (new); shows all 12 widget types not already on the dashboard with descriptions and "Add" buttons
- **Widget Remove** — × button on each widget header; SweetAlert2 confirm; removes card from DOM immediately

### **Files Changed**

| File | Change |
|---|---|
| `vulnerable-version/models/dashboard.py` | +3 static methods: create, update, delete |
| `vulnerable-version/models/dashboard_widget.py` | +WIDGET_DEFAULT_PERIODS, +add_to_dashboard, +remove |
| `vulnerable-version/routes/api/dashboards.py` | +5 new endpoints: create/update/delete dashboard, add/remove widget |
| `vulnerable-version/templates/dashboard.html` | +tab controls, Create/Edit Dashboard Modal, widget grid refresh |
| `vulnerable-version/static/js/dashboard.js` | +setupDashboardModal, openCreate/EditDashboardModal, saveDashboardModal, confirmDeleteDashboard, refreshCustomizePanel (2-section), addWidgetToDashboard, confirmRemoveWidget |
| `vulnerable-version/static/css/glass.css` | +.tab-add-btn, .tab-ctrl-btn, .widget-remove-btn, .customize-section-title, .add-widget-list, .add-widget-card |
| `docs/vulnerability-matrix.md` | +VULN-046 through VULN-053 |

### **Vulnerabilities Added (Sprint 9)**

| VULN-ID | Type | Description |
|---------|------|-------------|
| VULN-046 | SQL Injection | Dashboard name/description injected directly into f-string in create/update |
| VULN-047 | Stored XSS | Dashboard name rendered via `innerHTML` in tab bar |
| VULN-048 | IDOR | Edit any user's dashboard by ID (no ownership check) |
| VULN-049 | IDOR | Delete any user's dashboard by ID |
| VULN-050 | IDOR | Add widget to any dashboard by ID |
| VULN-051 | IDOR | Remove any widget by ID (dashboard_id param not used) |
| VULN-052 | Mass Assignment | `user_id` accepted in dashboard create request body |
| VULN-053 | CSRF | No token on any of the 5 new CRUD endpoints |

### **User Testing Sign-Off**

- ✅ Create new dashboard — appears as tab, auto-activates
- ✅ Rename dashboard — tab label updates immediately
- ✅ Delete dashboard — tab removed, switches to first remaining
- ✅ Add widget — all 12 types addable; widget appears in grid immediately
- ✅ Remove widget — confirmation; card removed from DOM; survives reload
- ✅ All 4 pre-built dashboards still auto-seed for new users
- ✅ No regressions in Sprint 8 functionality

---

## 🌬️ **Sprint 9b: "Wind Breathing — Hidden Technique" — Widget Settings**

**Date**: 2026-06-19
**Status**: ✅ **COMPLETE**
**Story Points**: 15/15 (100%)
**Scope**: `vulnerable-version/` only
**Covers**: ENH-006 extension — per-widget configuration

---

### **What Was Built**

#### Database Schema

New `init-vulnerable-sprint9b.sql` adds 3 columns to `dashboard_widgets`:

```sql
ALTER TABLE dashboard_widgets
    ADD COLUMN chart_type    VARCHAR(20)  DEFAULT NULL,
    ADD COLUMN filter_config JSON         DEFAULT NULL,
    ADD COLUMN custom_title  VARCHAR(150) DEFAULT NULL;
```

#### Model Updates

- **`dashboard_widget.py`** — 3 new fields in `__init__` and `_from_row`; `update_state` extended with `chart_type`, `filter_config`, `custom_title` parameters + `_*_set` boolean flags (sentinel pattern to distinguish "not in request" from explicit null); `CAST('...' AS JSON)` used for MySQL 8.0 JSON column writes; `json.loads()` in `_from_row` for deserialization
- **`routes/api/dashboards.py`** — `_widget_to_dict` includes the 3 new fields; `update_widget` endpoint uses `'__unset__'` sentinel to selectively update only provided fields

#### Report Data Filters

All 6 applicable endpoints in `routes/api/reports_data.py` now accept filter query params:

| Endpoint | New Params |
|---|---|
| `/income-expense` | `category_ids`, `account_ids` |
| `/expense-distribution` | `category_ids` |
| `/category-heatmap` | `category_ids` |
| `/top-categories` | `category_ids` |
| `/potential-to-save` | `account_ids` |
| `/budget-vs-actual` | `category_ids` (on `bc.category_id`) |

Two helper functions added: `_category_filter(ids_str, table_alias)` and `_account_filter(ids_str, table_alias)` — both intentionally unsanitised (SQLi by design).

#### Frontend — Widget Settings Modal

Bootstrap modal with 4 sections:
1. **Custom Title** — text input; blank = use default widget type title
2. **Chart Type Picker** — shown only for 5 applicable widget types; pill buttons (Bar Chart / Line Chart / Donut Chart)
3. **Category Filter** — shown only for widgets with category support; pill checkboxes loaded from `/api/categories/list`
4. **Account Filter** — shown only for widgets with account support; pill checkboxes loaded from `/api/accounts/list`

#### JavaScript Architecture

- **`CHART_TYPE_OPTIONS`** — maps widget type → available chart types (5 entries)
- **`FILTER_SUPPORT`** — maps widget type → `{categories, accounts}` boolean flags (7 entries)
- **`openWidgetSettingsModal(widgetId)`** — fetches current widget state, populates all sections, shows modal
- **`saveWidgetSettings()`** — collects selections, POSTs to update endpoint, reloads widget in-place
- **`loadWidgetData()`** — extracts `filter_config` from widget state, appends `category_ids`/`account_ids` to data fetch URLs, passes `chart_type` to renderer
- **5 renderers updated** to accept `chartType` third param: `renderIncomeExpenseBar`, `renderExpenseDonut`, `renderTopCategoriesTrend`, `renderFixedVsVariable`, `renderObligationsMonthly`
- **`buildWidgetShell()`** — displays `custom_title || title` via `innerHTML`; adds ⚙ button calling `openWidgetSettingsModal`

#### CSS

New rules in `glass.css`: `.widget-settings-btn`, `.chart-type-picker`, `.chart-type-btn` / `.chart-type-btn.active`, `.filter-checklist`, `.filter-check-item`

### **Files Changed**

| File | Change |
|---|---|
| `database/init-vulnerable-sprint9b.sql` | New — ALTER TABLE dashboard_widgets (3 new columns) |
| `docker-compose.yml` | +mount for sprint9b SQL init file |
| `vulnerable-version/models/dashboard_widget.py` | +3 fields, updated update_state with sentinel pattern |
| `vulnerable-version/routes/api/dashboards.py` | Updated serialiser + sentinel logic in update_widget |
| `vulnerable-version/routes/api/reports_data.py` | +_category_filter, +_account_filter helpers; 6 endpoints updated |
| `vulnerable-version/templates/dashboard.html` | +Widget Settings Modal (inside block content) |
| `vulnerable-version/static/js/dashboard.js` | +constants, +modal functions, updated renderers and loadWidgetData |
| `vulnerable-version/static/css/glass.css` | +widget settings button and modal UI styles |

### **Vulnerabilities Added (Sprint 9b)**

| VULN-ID | Severity | Type | Description |
|---------|----------|------|-------------|
| VULN-054 | 🔴 Critical | SQL Injection | `category_ids` appended directly to IN clause in 5 report endpoints — UNION-based exfiltration possible |
| VULN-055 | 🔴 Critical | SQL Injection | `account_ids` appended directly to IN clause in 3 endpoints |
| VULN-056 | 🟡 High | Stored XSS | `custom_title` rendered via `innerHTML` in widget header — script tags execute on dashboard load |
| VULN-057 | 🟡 High | SQL Injection | `custom_title` injected directly into UPDATE f-string in `update_state` |

### **Key Technical Decisions**

| Decision | Rationale |
|---|---|
| Sentinel `'__unset__'` pattern for optional update fields | `data.get('key', None)` can't distinguish "key absent" from "key present with null value" — needed for selective NULL-clearing of chart_type / filter_config / custom_title |
| `CAST('...' AS JSON)` for JSON column writes | MySQL 8.0 JSON columns require explicit CAST when assigning via raw f-string; plain string assignment fails silently |
| `len(row) > 9` guard in `_from_row` | Backwards-compatibility: existing widget rows fetched before schema migration don't have the 3 new columns and would throw IndexError without the guard |
| `_category_filter(ids, table_alias='bc')` for budget_vs_actual | budget_vs_actual JOINs on `budget_categories bc` not `transactions t`, so the alias must be `bc` to filter on `bc.category_id` |

### **Post-Sprint Bug Fixes**

| ID | Description | Fix |
|----|-------------|-----|
| BUG-S9b-01 | Tab text, ⚙, ✏, 🗑, × icons barely visible against dark glass background | `glass.css`: changed `color: var(--th)` / `color: var(--ts)` → `color: #fff` on 5 selectors |
| BUG-S9b-02 | Widget Settings modal appeared at top of viewport instead of matching other modal position | `dashboard.html`: removed `modal-dialog-centered` + `glass-modal` from modal-content — matched structure of Account/Transaction modals; global CSS rule already handles glass styling on `.modal-content` |

### **User Testing Sign-Off**

- ✅ Widget Settings modal opens from ⚙ button on every widget
- ✅ Custom title saves and displays in widget header; persists on reload
- ✅ Chart type switching works on all 5 applicable widgets; persists
- ✅ Category filter narrows widget data; clearing all checkboxes restores full data
- ✅ Account filter narrows widget data; clearing all checkboxes restores full data
- ✅ Modal positions correctly (matches Account/Transaction modal position)
- ✅ Icon/text colours are white and readable
- ✅ No regressions in Sprint 8 or Sprint 9 functionality

---

**Last Updated**: 2026-06-19 | Sprint 9b complete

# Aura — Full Project Roadmap

**Last Updated**: 2026-08-02
**Total Planned**: 11 Releases · 12+ Sprints · ~374+ Story Points

This document is the single source of truth for the full project roadmap.
Sprint plans live in `docs/sprints/`. Release summaries live in `docs/releases/`.

---

## At a Glance

| Release | Name | Sprints | Points | Status |
|---|---|---|---|---|
| 1 | Hashira Foundation | 1–2 | ~54 pts | ✅ Complete |
| 2 | Shadow Extractor | 3–5 | ~91 pts | ✅ Complete |
| 3 | Crystal Vision | 6–8 | ~93 pts | ✅ Complete |
| 4 | Iron Fortress | 9 · 9b · 10–15 | ~230 pts (rough, see below) | 🚧 In Progress |
| 5 | Sovereign Ascent | 17–22 | TBD, points relative | ✅ Complete |
| 6 | Transparent World | 23–27 | TBD | ✅ Complete — AI Advisor (Groq) |
| 7 | Prism Bloom (working title) | 34–37 (38–39 dropped) | — | ⏸️ Paused — Theme System Expansion (reverted to Abyss-only 2026-08-03) |
| 8 | Compound Horizon (working title) | 28–33 | TBD | ✅ Complete — Loan Intelligence |
| 9 | Shattered Veil (working title) | 40–45 | TBD | ✅ Complete — Hidden CTF Challenge Page (vulnerable-version only), real flag mechanism, operator tooling. See `docs/releases/release-09-overview.md` |
| 10 | Twin Reflection (working title) | 47–48 | TBD | ✅ Complete — Full security audit (zero Critical/High) + UI differences reconciled. See `docs/releases/release-10-plan.md` |
| 11 | Whetstone (working title) | 50–53 | TBD | ✅ Complete — General Application Improvements (both versions) |
| 12 | (working title) | 54–57 | TBD | 📝 Planned — BUG-20 root-cause fix, VULN-085/086 confirmation, old UI bugs, backlog grooming |

---

## Release 1 — "Hashira Foundation"

**Theme**: Core infrastructure, authentication, foundational financial tracking
**Scope**: Both `vulnerable-version/` and `secure-version/`
**Status**: ✅ **COMPLETE**

### Sprint 1 — "Water Breathing: First Form"

**Goal**: Docker environment + user authentication
**Points**: 28 pts | **Status**: ✅ Complete

| Story | Description |
|---|---|
| US-001 | Docker + Docker Compose configuration |
| US-002 | MySQL database schema (both versions) |
| US-003 | Basic Flask application structure |
| US-004 | User registration — secure version (bcrypt, validation) |
| US-005 | User registration — vulnerable version (SQL injection, plaintext) |
| US-006 | Login / logout — both versions |
| US-007 | Documentation (README, setup guide, dev log) |

### Sprint 2 — "Thunder Breathing: Second Form"

**Goal**: Transaction management + category system + dashboard charts
**Points**: 26 pts | **Status**: ✅ Complete

| Story | Description |
|---|---|
| US-008 | Manual transaction entry (modal, AJAX, CRUD) |
| US-009 | Expense categorization |
| US-010 | Income categorization |
| US-011 | Dashboard with Chart.js (income vs expenses bar, category pie, recent transactions) |
| US-012 | Edit / delete transactions |

**Vulnerabilities introduced**: 13 new (total: 27)

---

## Release 2 — "Shadow Extractor"

**Theme**: Accounts, recurring transactions, budgets, goals, reports and export
**Scope**: `vulnerable-version/` primary
**Status**: ✅ **COMPLETE** | Date: 2026-06-17

### Sprint 3 — "Stone Breathing: Third Form"

**Goal**: Multiple bank accounts + recurring transactions with auto-generation
**Points**: 28 pts | **Status**: ✅ Complete

| Story | Description |
|---|---|
| US-013 | Multiple bank accounts (types: checking, savings, credit card, investment, cash) |
| US-014 | Create recurring transaction (daily/weekly/monthly/yearly) |
| US-015 | View recurring transactions (tabs: All / Active / Paused) |
| US-016 | Edit / delete recurring transactions |
| US-017 | Auto-generate from recurring (APScheduler, hourly, income/expense/transfer) |

### Sprint 4 — "Flame Breathing: Fourth Form"

**Goal**: Account transfers + budget planning + savings goals
**Points**: 30 pts | **Status**: ✅ Complete

| Story | Description |
|---|---|
| US-018 | Multiple bank accounts CRUD (full management page) |
| US-019 | Transfer between accounts (dual linked transactions) |
| US-020 | Monthly budget planning (period types, total limit) |
| US-021 | Budget tracking with per-category limits and progress bars |
| US-022 | Savings goals with timeline calculator (dual mode: deadline→amount / amount→date) |

### Sprint 5 — "Shadow Ledger"

**Goal**: Export / import / advanced reports
**Points**: 33 pts | **Status**: ✅ Complete

| Story | Description |
|---|---|
| US-023 | Export transactions to CSV |
| US-024 | Export transactions to PDF (reportlab) |
| US-025 | Export transactions to Excel (openpyxl) |
| US-026 | Import transactions from CSV |
| US-027 | Advanced filtering and reports dashboard |

**Bug fixes**: 6 bugs resolved (BUG-001 through BUG-009, excluding intentional vulnerabilities)
**Vulnerabilities total at end of Release 2**: 45

---

## Release 3 — "Crystal Vision"

**Theme**: UI excellence, UX enhancements, multi-dashboard analytics
**Scope**: `vulnerable-version/` primary; `secure-version/` UI deferred
**Status**: ✅ **COMPLETE** | Date: 2026-06-19

### Sprint 6 — "Shadow Evolution"

**Goal**: DB enhancements — global default categories, recurring templates
**Points**: 8 pts | **Status**: ✅ Complete

| Enhancement | Description |
|---|---|
| ENH-007 | Global default categories (`is_default` flag, NULL `user_id`, 15 seeded defaults) |
| ENH-002 | Recurring transaction templates (`is_template` flag) |

**Note**: `ADD COLUMN IF NOT EXISTS` SQL was MariaDB syntax — fixed in Sprint 7.

### Sprint 7 — "Moon Breathing: Seventh Form"

**Goal**: Full Liquid Glass UI Design System — "Abyss" theme
**Points**: 38 pts | **Status**: ✅ Complete | Dates: 2026-06-17 → 2026-06-18

| Story Group | Description |
|---|---|
| Background scene | Gradient mesh + 4 animated Abyss blobs |
| Glass architecture | 6-layer glass cards (lensing, highlights, shadow, tint, scroll-edge, glow) |
| Sidebar | Glass sidebar, collapsible to icon-only (60px), inline SVG nav icons |
| Modals | Z+4 glass modals with dimming overlay |
| All page templates | Full rewrite of all 19 templates (dashboard, transactions, categories, accounts, budgets, goals, recurring, reports, auth pages, error pages) |
| Interactions | Spring hover (`cubic-bezier(0.34, 1.50, 0.64, 1)`), focus rings, active states |

**6 bugs found and fixed during testing**: modal stacking contexts, MySQL SQL syntax, wrong column indices, error page rendering.

### Sprint 8 — "Flame Breathing: Eighth Form"

**Goal**: Multi-dashboard system with 4 pre-built dashboards, 12 configurable widgets, per-widget time filters
**Points**: 47 pts | **Status**: ✅ Complete | Date: 2026-06-19

| Enhancement | Description |
|---|---|
| ENH-003 | Budget vs Actual Charts — W5 widget in Savings & Goals dashboard |
| ENH-005 | Customizable Dashboard — 4 pre-built dashboards, widget minimize/maximize, per-widget time period |

**Deferred to Release 4**:
- ENH-001 — Category colour themes (implemented differently; emoji icons dropped)
- ENH-006 — Full CRUD dashboard creation (user-defined named dashboards)
- `secure-version/` UI — same glass system deferred

**4 Pre-Built Dashboards**:

| Dashboard | Widgets |
|---|---|
| Monthly Overview | Income vs Expenses bar (W1), Expense donut (W2), Recent transactions (W3) |
| Savings & Goals | Savings goals progress (W4), Budget vs Actual (W5), Potential to save (W6) |
| Spending Analysis | Category heatmap (W7), Top 5 trend lines (W8), Fixed vs Variable (W9) |
| Loan & Obligations | Obligations monthly (W10), Extra repayments YTD (W11), Debt payments metric (W12) |

---

## Release 4 — "Iron Fortress"

**Theme**: Security hardening, `secure-version/` catch-up, Kubernetes, observability
**Scope**: Both versions + infrastructure
**Status**: ✅ **COMPLETE**
**Sprints**: 9 · 9b · 10 · 11 · 12 · 13 · 14 · 15 · 16
**Estimated Points**: ~230 pts (rough — will refine sprint-by-sprint)

### Sprint 9 — "Wind Breathing: Ninth Form" ✅ Complete

**Goal**: Full CRUD dashboard creation for `vulnerable-version/`
**Points**: 18 pts | **Date**: 2026-06-19
**Scope**: `vulnerable-version/` only

| Story | Description |
|---|---|
| ENH-006 | Full CRUD dashboard creation — create, edit, delete named dashboards; add/remove widgets per dashboard |

**New vulnerabilities**: VULN-046 through VULN-053 (IDOR, SQLi, Stored XSS, CSRF, Mass Assignment)

### Sprint 9b — "Wind Breathing: Hidden Technique" ✅ Complete

**Goal**: Per-widget configuration — custom chart types, category/account filters, custom titles
**Points**: 15 pts | **Date**: 2026-06-19
**Scope**: `vulnerable-version/` only

| Story | Description |
|---|---|
| S9b-1 | DB schema — 3 new columns on dashboard_widgets (chart_type, filter_config JSON, custom_title) |
| S9b-2 | Model update — sentinel pattern for selective NULL updates; CAST for JSON writes |
| S9b-3 | API update — serialiser + update endpoint accept new widget config fields |
| S9b-4 | Filter params on 6 report data endpoints (category_ids, account_ids) |
| S9b-5 | Widget Settings Modal — title, chart type picker, category/account filter checklists |
| S9b-6 | CSS — settings button, chart type picker, filter checklist |
| S9b-7 | JS modal functions — openWidgetSettingsModal, saveWidgetSettings |
| S9b-8 | 5 chart renderers updated to accept chartType param; filters passed to data URLs |
| S9b-9 | Widget header — ⚙ button, custom_title display via innerHTML |

**New vulnerabilities**: VULN-054 through VULN-057 (SQLi via filter IDs, Stored XSS via custom_title)
**Bug fixes**: BUG-S9b-01 (icon colours), BUG-S9b-02 (modal positioning)

---

**Sprints 10–15 replace the original single "Sprint 10: secure-version catch-up" slot.** `secure-version/` turned out to be at Sprint-1 parity only (auth alone — not even Sprint 2's transactions/categories/dashboard), so reaching full feature parity with `vulnerable-version/`, done securely, is broken into six focused sprints instead of one:

### Sprint 10 — "Serpent Breathing: Tenth Form" ✅ Complete

**Goal**: Secure UI Foundation — port the Liquid Glass (Abyss) system to `secure-version/`'s 8 existing pages
**Points**: 13 pts | **Date**: 2026-07-23
**Scope**: `secure-version/` only

Found and fixed one pre-existing bug during testing: `SESSION_COOKIE_SECURE = True` was hardcoded, so the session cookie never persisted over local plain-HTTP dev — login appeared broken even though registration and password verification both worked. Fixed by making it environment-conditional (`False` only when `FLASK_ENV=development`). Not caused by the UI port; `secure-version/` had never been tested end-to-end before.

See `docs/sprints/sprint-10-plan.md` for full detail.

### Sprint 11 — "Serpent Breathing: Hidden Fang" ✅ Complete

**Goal**: Core Financial Tracking (secure) — transactions, categories (incl. global defaults), basic dashboard with charts
**Points**: 13 stories | **Date**: 2026-07-23
**Scope**: `secure-version/` only

Found and fixed one new stored-XSS vector during this sprint: category `color` was accepted unvalidated and rendered into a `style="background:${color}"` attribute client-side — a crafted value could break out of the attribute. Fixed with strict server-side hex validation (`^#[0-9a-fA-F]{6}$`).

**⚠️ Requires manual DB migration** — see `docs/sprints/sprint-11-plan.md` for the one-off command (the `mysql-secure` volume was already initialized before this schema existed, so `docker-entrypoint-initdb.d` won't run it automatically).

See `docs/sprints/sprint-11-plan.md` for full detail.

### Sprint 12 — "Serpent Breathing: Rock Piercer" ✅ Complete

**Goal**: Accounts + Recurring Transactions (secure)
**Date**: 2026-07-23
**Scope**: `secure-version/` only

'transfer' recurring type, `to_account_id`, and the accounts-page Transfer modal deliberately deferred to Sprint 13 (the `Transfer` model doesn't exist yet — same dependency vulnerable-version had between its own Sprint 3 and 4).

**⚠️ Requires manual DB migration** — see `docs/sprints/sprint-12-plan.md`.

See `docs/sprints/sprint-12-plan.md` for full detail.

### Sprint 13 — "Serpent Breathing: Dance of the Serpent" ✅ Complete

**Goal**: Transfers + Budgets + Savings Goals (secure)
**Date**: 2026-07-23
**Scope**: `secure-version/` only

See `docs/sprints/sprint-13-plan.md` for full detail.

**⚠️ Requires manual DB migration** — see `docs/sprints/sprint-13-plan.md`.

### Sprint 14 — "Serpent Breathing: Windfall Bloom" ✅ Complete

**Goal**: Export/Import + Reports + Multi-Dashboard System — full CRUD, widget settings (secure)
**Date**: 2026-07-23
**Scope**: `secure-version/` only

Built as a single sprint per user decision (not split into 14a/14b/14c despite the ~95 pt estimate).

See `docs/sprints/sprint-14-plan.md` for full detail.

**⚠️ Requires manual DB migration** — see `docs/sprints/sprint-14-plan.md`.

### Sprint 15 — "Serpent Breathing: Two-Headed Dragon" ✅ Complete

**Goal**: Security Hardening & Audit — CSRF sweep across every new form, rate limiting on auth endpoints, input validation audit, full IDOR/ownership check pass across every endpoint added in Sprints 11–14
**Date**: 2026-07-24
**Scope**: `secure-version/` only

Two notable findings: CSRF protection had been claimed in a docstring since Sprint 1 but was never actually wired up, and the account-lockout timeout (`LOGIN_TIMEOUT_MINUTES`) had been defined in config since Sprint 1 but never read anywhere, meaning locked accounts stayed locked forever. Both fixed. IDOR/ownership audit came back clean — every route already had its decorator.

See `docs/sprints/sprint-15-plan.md` for full detail.

**⚠️ Requires manual DB migration** — see `docs/sprints/sprint-15-plan.md`.

### Sprint 16 — "Mist Breathing: Eleventh Form" ✅ Complete

**Goal**: Kubernetes deployment + Prometheus/Grafana observability
**Date**: 2026-07-24
**Scope**: Infrastructure (both app versions, each in its own namespace)

| Story | Description |
|---|---|
| K8S-001 | Kubernetes manifests (Deployments, Services, ConfigMaps, Secrets) — `k8s/base/{secure,vulnerable,monitoring}/` |
| K8S-002 | Helm chart for Aura — `k8s/helm/aura/`, every value parameterized, each section independently toggleable |
| K8S-003 | Prometheus metrics scraping (Flask `/metrics` via `prometheus-flask-exporter` + `mysqld_exporter` per DB) |
| K8S-004 | Grafana dashboard for Aura application metrics — auto-provisioned, secure vs. vulnerable side by side |
| K8S-005 | Liveness + readiness probes — hit `/health`, gated on real DB connectivity |
| K8S-006 | Horizontal Pod Autoscaler — 2–6 replicas, 70% CPU / 80% memory targets |
| OBS-001 | Structured logging (JSON format) — `logging_config.py`, both app versions |
| OBS-002 | Health check endpoint `/health` — both app versions |

Decided with the user before starting: `k8s/` lives at the repo root (mirrors `docker-compose.yml`'s existing "infra is a shared top-level concern" pattern) rather than split per app version; separate namespaces (`aura-secure`/`aura-vulnerable`/`aura-monitoring`) for a real isolation boundary. See `docs/sprints/sprint-16-plan.md` for full detail, including what was explicitly not pursued (NetworkPolicies, Ingress, a scoped MySQL exporter user).

**⚠️ Requires manual deployment steps** — see `k8s/README.md` (build images, generate init ConfigMaps, `kubectl apply`/`helm install`).

**Post-completion fixes (2026-07-24, same day)**: a full `k8s/TESTING.md` walkthrough on minikube surfaced 6 real deployment defects (image tag naming, `mysqld_exporter` config format, ConfigMap init-script ordering, MySQL liveness-probe-induced corruption, CSRF/Secure-cookie behavior over plain HTTP, and `prometheus_flask_exporter` suppressing `/metrics` under the reloader) — all fixed same day. See "Post-Completion Fixes" in `docs/sprints/sprint-16-plan.md` for full detail. Also added, outside original scope: a systemd-based LAN-access script and a TLS ingress for `app-secure`.

---

## Release 5 — "Sovereign Ascent"

**Theme**: Multi-currency, expanded import, dashboard UX, simple analytics, in-app alerts, and a full pentest report
**Status**: ✅ **COMPLETE** | Date: 2026-07-28
**Style**: Insect Breathing (one style across all 6 sprints)
**Scope**: Both versions, in parity, every sprint
**Full plan**: `docs/releases/release-05-plan.md`

| Sprint | Focus |
|---|---|
| 17 | ✅ Multi-Currency (static/manual exchange rates) + shared upgrade runbook (`k8s/UPGRADE.md`) — complete 2026-07-25, docker-compose and k8s both verified end-to-end. Along the way: found and fixed a real k8s deployment bug (`:latest` tag + `IfNotPresent` silently serving stale images — see `k8s/UPGRADE.md`'s "Read this first" section) and removed VULN-065 at explicit user request. Full detail in "Retrospective" in `docs/sprints/sprint-17-plan.md` |
| 18 | ✅ Data Import Expansion — OFX + QIF bank statement formats — complete 2026-07-26, docker-compose and k8s both verified end-to-end. VULN-067 (OFX XXE) took three iterations to get the mechanism right (see retrospective); final version uses `lxml` (unhardened) in vulnerable-version, `defusedxml` in secure. OPS-003 used the unique-tag k8s approach cleanly on the first try. Full detail in `docs/sprints/sprint-18-plan.md` |
| 19 | ✅ Dashboard Drag-and-Drop — reorder dashboards and widgets (ENH-006 v2, ENH-010) — complete 2026-07-26, docker-compose and k8s both verified end-to-end. SortableJS (CDN) + bulk reorder endpoints; secure validates every id atomically before writing, vulnerable doesn't (VULN-070/071). No DB migration needed. Full detail in `docs/sprints/sprint-19-plan.md` |
| 20 | ✅ Advanced Analytics — simple statistical heuristics + YoY comparison widget (ENH-011) — complete 2026-07-26, docker-compose and k8s both verified. Grew mid-sprint from user feedback into a full per-widget chart color customization feature (7 widget types) plus two UX redesigns (anomaly chips, Potential to Save). Full detail in `docs/sprints/sprint-20-plan.md` |
| 21 | ✅ In-App Notifications — budget-overrun and bill-reminder alerts — complete 2026-07-26, docker-compose and k8s both verified. VULN-073 (IDOR+SQLi) and VULN-074 (stored XSS via notification content) confirmed. Also fixed several bell-icon-related UX issues found during testing (page-header overlap on 7 pages, a genuine Chromium/Windows scrollbar limitation, transaction-list pagination). Full detail in `docs/sprints/sprint-21-plan.md` |
| 22 | ✅ Full Penetration Testing Report — closing sprint, no new features — complete 2026-07-28. Compiled from existing evidence (per user decision) rather than a full live re-test of all 74 findings: `docs/vulnerability-matrix.md`'s confirmed entries, each sprint's retrospective, and this session's live-verified findings from Sprint 17 onward. Report published as `docs/testing/pentest-report-release-05.md` — findings grouped by root-cause pattern (SQL injection, IDOR, missing auth, XSS, CSRF, mass assignment, business logic, info disclosure, input validation — 9 systemic groups covering 65 of 74 findings) plus 9 individual write-ups for genuinely distinct vulnerabilities (plaintext passwords, XXE, weak password policy, session/cookie hardening gaps, CSV injection, race condition). Full detail in `docs/sprints/sprint-22-plan.md` |

Every sprint ends with a formal **Deploy & Verify** story, upgrading both the
`docker-compose` and k8s environments with that sprint's changes — turns
each sprint into recurring real-world DevOps upgrade practice rather than
something done ad hoc.

**Deferred to backlog**: CI/CD Pipeline (no test suite to run yet — revisit
once one exists); live FX API for multi-currency (static rates chosen
instead, to avoid API-key management and an external dependency for now).

---

## Release 6 — "Transparent World"

**Theme**: AI-powered financial advisor with real-world AI vulnerabilities for CTF
**Scope**: Both `secure-version/` and `vulnerable-version/`, in parity (secure hardened) — confirmed with user, updated from the original "vulnerable-version/ primary" note
**Status**: ✅ **COMPLETE** | Date: 2026-07-29
**LLM Provider**: Groq API — two separate API keys, one per version (not shared), so `vulnerable-version/`'s intentionally-leakable key is never the same one protecting `secure-version/`
**Estimated Points**: TBD, 5 sprints (23–27), all complete
**Report**: `docs/testing/pentest-report-release-06.md` — VULN-075–079 plus two honestly-documented `secure-version/` residual-risk findings (no VULN-ID, per project convention)
**k8s**: Sprints 23–26 caught up and fully verified 2026-07-29 (post-Sprint-27) — see `k8s/UPGRADE.md`'s "Sprint 23–26 catch-up" section. `GROQ_API_KEY` applied out-of-band via `kubectl create secret ... --dry-run=client | kubectl apply` (never committed, two separate keys per Release 6's original decision); images rebuilt under `sprint23to26`; all 5 migrations applied; both scheduler jobs confirmed registered on both versions; full browser smoke test confirmed the secure/vulnerable tool-calling contrast (confirmation-gated vs. immediate execution) working correctly through the actual cluster, not just docker-compose.

### Concept

Integrates an LLM-powered AI advisor into the application. The AI reads the user's actual financial
data (transactions, budgets, savings goals, accounts) and acts as a proactive financial coach.

### Planned Capabilities

| Feature | Description |
|---|---|
| Chat interface | Glass-styled chat panel, persisted conversation history per user |
| Proactive alerts | On dashboard load: flags unusual expenses, budget overruns, slow savings pace |
| Financial analysis | Month-over-month comparisons, category anomaly detection, trend summaries |
| Advisory suggestions | "At current pace, Holiday Fund goal is 3 months late — consider +500 RON/month" |
| Data-driven context | AI receives full user financial context before every response |

### AI-Specific CTF Vulnerabilities (Intentional)

| Vulnerability | Description |
|---|---|
| Prompt injection | Transaction descriptions containing injected instructions manipulate AI responses |
| Indirect prompt injection | Malicious data already in DB poisons AI context without direct chat input |
| System prompt extraction | Asking AI to repeat its instructions leaks the system prompt |
| IDOR through AI | Passing another user's `user_id` makes AI analyse their finances |
| Insecure API key storage | Key stored in plaintext in config, accessible via existing path traversal vulnerabilities |
| Excessive agency | If AI can write transactions, prompt injection triggers unintended financial writes |
| Jailbreaking | Bypassing the financial advisor persona via crafted chat input |

### Sprints

| Sprint | Focus |
|---|---|
| 23 | ✅ Sun Breathing: Dance — Foundation: Groq integration, chat interface, persisted conversation history — complete 2026-07-28. VULN-075 (SQLi + IDOR on AI advisor endpoints) and VULN-076 (insecure API key storage via extended debug endpoint) confirmed live. Advisor named "Solis"; login-scoped chat history with a 90-day auto-expire job + manual clear button added from user feedback. Full detail in `docs/sprints/sprint-23-plan.md` |
| 24 | ✅ Sun Breathing: Clear Blue Sky — Prompt injection & context-scoping attack surface — complete 2026-07-28. VULN-077 (prompt injection, direct + indirect, including raw Python-object leakage) and VULN-078 (insecure output handling — XSS via echoed AI response) confirmed live. secure-version's injection defense was found incomplete against direct extraction, hardened once (explicit anti-repeat/paraphrase/translate/summarize instruction), and retested honestly: meaningfully improved but not eliminated — documented as a real residual-risk finding rather than chased with more wording. Full detail in `docs/sprints/sprint-24-plan.md` |
| 25 | ✅ Sun Breathing: Fire Wheel — Proactive insights: dashboard alerts + AI-narrated financial analysis — complete 2026-07-28. Daily scheduled job narrates spending anomalies, savings-goal pacing, and a new subscription cost-creep detector into a single insight per user, delivered via the existing notification bell (no new VULN IDs — reuses VULN-073/077's existing surface). Live testing surfaced two real bugs: vulnerable-version's notification INSERT broke on ordinary apostrophes in AI text (fixed with the same naive-escaping precedent from Sprint 23), and `notifications.message` was too narrow (`VARCHAR(500)`) for a multi-finding narration — a shared bug in both versions, fixed by widening to `TEXT`. Full detail in `docs/sprints/sprint-25-plan.md` |
| 26 | ✅ Sun Breathing: Setting Sun Transformation — Excessive agency: AI-triggered financial actions — complete 2026-07-29. Groq tool-calling added (create transaction, create budget); vulnerable executes immediately with no confirmation, secure requires explicit confirmation via a new `ai_pending_actions` table + server-side re-validation. VULN-079 confirmed via the full live kill chain: a poisoned transaction description (Sprint 24 style) triggered a real, unconfirmed 9999 RON write on a completely unrelated follow-up chat message — worse than expected, since Solis's reply never disclosed taking the action at all. Mid-sprint functionality fix (both versions, not security-relevant): tool schema switched from IDs Solis never actually had to names it can see, resolved server-side. Full detail in `docs/sprints/sprint-26-plan.md` |
| 27 | ✅ Sun Breathing: Sovereign Radiance — AI vulnerability report addendum (closing sprint) — complete 2026-07-29. `docs/testing/pentest-report-release-06.md` published, anchored on the OWASP LLM Top 10 rather than the classic Web Top 10. Covers VULN-075–079 plus a "Secure-Version Defense-in-Depth Observations" section for two real gaps found by testing secure-version as adversarially as vulnerable-version — neither given a VULN-ID per project convention, both real and documented. Closing risk statement: 4 of 5 findings are the same root causes as the rest of this catalog and fix the same way; VULN-077/079 are the first findings where the model's own unreliability is part of the attack surface, confirmed twice independently to not reliably follow instructions about its own behavior even when told exactly what not to do. No Deploy & Verify this sprint (no code changes) — k8s catch-up for Sprints 23-26 explicitly deferred to backlog. Full detail in `docs/sprints/sprint-27-plan.md` |

Draft sprint breakdown — see `docs/releases/release-06-plan.md` for full scope decisions, story lists, and open items (naming, exact API-key exposure vector) still open to adjustment before Sprint 23 starts.

---

## Release 7 — "Prism Bloom" (working title)

**Theme**: Theme system expansion — 5 new themes alongside the existing Abyss theme, plus a real theme-switcher UI control
**Scope**: Both `secure-version/` and `vulnerable-version/`, in parity
**Status**: ⏸️ **PAUSED** (2026-08-03) — Sprints 34, 36, 37 were implemented (switcher, Daybreak, Ember, Wisteria, Tempest, hero cards), then the user asked to revert to Abyss-only. All Release 7 code is commented out (not deleted) in both versions, preserved for a possible future revival. Sprint 35 (Haori) was never built; Sprints 38–39 were dropped. Full history: `docs/releases/release-07-retrospective.md`.
**Style**: Flower Breathing (proposed)
**Full plan**: `docs/releases/release-07-plan.md`
**Planned**: 2026-08-02

### Summary (full detail in `docs/releases/release-07-plan.md`)

Six total themes: **Abyss** (existing) + **Daybreak** (light-mode counterpart of Abyss, token-only), **Ember** (new dark palette, flame-inspired, token-only), **Wisteria** (full redesign via the `ui-ux-pro-max` skill + `design/` folder reference, new layout allowed), **Tempest** (a second full redesign iterating on Wisteria's layout — depends on Wisteria finishing first), and **Haori** (directly Demon-Slayer-branded, black/deep-green with a checkered accent motif, token-only, exact colors adjustable later). Layout redesign work is scoped to Wisteria and Tempest only; the other four stay token-only. A decision gate after both redesigns exist decides whether the better layout gets retrofitted onto the rest. Switcher UI is a simple dropdown, persisted the same way as the existing sidebar-collapse ( `localStorage` + `data-theme`). `vulnerable-version/` gets a new intentional vulnerability tied to theme-preference storage, mechanism TBD at implementation time.

### Sprints

| # | Sprint | Focus |
|---|---|---|
| 34 | Flower Breathing: Higan Flower | Switcher infrastructure + Daybreak + Ember |
| 35 | Flower Breathing: Second Bloom | Haori |
| 36 | Flower Breathing: Wisteria's Reflection | Wisteria — full redesign |
| 37 | Flower Breathing: Petals in the Storm | Tempest — second full redesign, iterates on Wisteria |
| 38 | Flower Breathing: Full Bloom | Decision point — pick winning layout, optional retrofit |
| 39 | Flower Breathing: Everlasting Bloom | Vulnerable-version vulnerability + Deploy & Verify |

---

## Release 8 — "Compound Horizon" (working title)

**Theme**: Loan Intelligence — an event-sourced mortgage tracking and analysis system, built around the user's real, currently-active variable-rate home loan
**Scope**: Both `secure-version/` and `vulnerable-version/`, in parity
**Status**: ✅ **COMPLETE** | Date: 2026-08-03 — started 2026-07-29, ahead of Release 7 (user decision); full detail in `docs/releases/release-08-overview.md`, full original draft in `docs/releases/release-08-plan.md`. Vulnerability re-confirmation (VULN-080/VULN-081 against k8s) deferred to Release 9 — see that section below.
**Sequencing**: After Release 6 — its AI-narration sprint reuses Release 6's Groq integration rather than duplicating it. No dependency on Release 7, so it was moved ahead by user choice.
**Estimated Points**: TBD, 6 sprints (28–33)

### Concept

Not a loan amortization calculator — a system that measures the effectiveness of the user's own extra-payment decisions against a variable-rate mortgage (base index + 2% margin, revised quarterly), separating what their choices achieved from what the market did on its own. Grounded in an extended design conversation validated against the user's real bank chart data (formula verified to the cent) and ~2 years of real tracking history (`Personal_Financial_Management.xlsx`).

### Core Architecture

| Element | Description |
|---|---|
| Event-sourced model | The loan is a timeline of events (creation, extra payment, rate change, bank snapshot, refinance, closure); every schedule is a *projection* — the output of one deterministic `project(loan_terms, events[]) -> schedule` function, not stored state |
| Actual vs. Baseline | Actual = replay all events. Baseline = replay all events except extra payments (rate changes stay in, since they're not the user's decision). Isolates the user's own impact from market rate movement |
| Deterministic engine, AI narrates only | Payoff dates, interest totals, and balances always come from backend code; the AI's role is limited to interpreting already-correct numbers, never computing them |
| Bank snapshots as checkpoints | A real bank-issued chart *pins* state at that date rather than being the primary data source — matches the event-sourcing "snapshot" pattern used for both performance and correctness |
| Reuses existing features | On-time payments via the existing Recurring Transactions feature; extra payments via ordinary Transactions in a dedicated category, linked with an explicit `loan_id` FK |

### Deferred (deliberately, not designed in detail yet)

Multi-loan portfolio UX, deferred/grace-period repayment logic, refinancing/closure business rules, and PDF chart parsing — all have minimal schema insurance reserved (a `loan_id` FK, reserved deferred-amount fields, a `status` field) but no built logic yet, since none are active in the user's real, current loan.

### Sprints

| # | Sprint | Focus |
|---|---|---|
| 28 | Beast Breathing: Rip and Tear | ✅ Foundation — data model, the `project()` engine, historical backfill |
| 29 | Beast Breathing: Crazy Cutting | ✅ Actual vs. Baseline projections + bank-snapshot reconciliation |
| 30 | Beast Breathing: Devour | ✅ Dedicated Loan Intelligence page + dashboard summary widget + PDF chart-upload assist |
| 31 | Beast Breathing: Wild Dance | ✅ Behavioral analytics — interest/years saved, payment-impact ranking, what-if simulator |
| 32 | Beast Breathing: Demon Slayer Mark | ✅ AI narration integration (depends on Release 6) — closed 2026-08-03, see `docs/sprints/sprint-32-plan.md`'s retrospective |
| 33 | Beast Breathing: Beast's Instinct | ✅ Add Loan UI + Loan Intelligence UI overhaul (card redesign, 5 new Dashboard widgets) + Deploy & Verify + close-out — closed 2026-08-03, see `docs/sprints/sprint-33-plan.md` and `docs/releases/release-08-overview.md` |

Started 2026-07-29, ahead of Release 7 (user decision), closed 2026-08-03 — see `docs/releases/release-08-overview.md` for the full delivered summary and `docs/releases/release-08-plan.md` for the original scope-decision record (the two confirmed event-recalculation rules, the honest breakdown of which behavioral metrics are trivial vs. need careful definition, and everything deferred).

---

## Release 9 — "Shattered Veil" (working title)

**Theme**: A hidden CTF challenge/scoreboard page, Juice Shop-style — lets a "hacker" user track which of this app's intentional vulnerabilities they've found and exploited
**Scope**: `vulnerable-version/` only (explicitly confirmed with user — no equivalent in `secure-version/`, there's nothing to hunt there)
**Status**: ✅ **COMPLETE** | Date: 2026-08-08 — all six sprints (40–45) delivered; full summary in `docs/releases/release-09-overview.md`, original scope decisions in `docs/releases/release-09-plan.md`. **Sprint 46 (2026-08-09) is a small addendum** added after close — a CTF organizer control panel — not a reopening of the release.
**Style**: Sound Breathing
**Planned**: 2026-08-05 (Release Planning Session)

### Scope, as decided (2026-08-05 planning session — see `docs/releases/release-09-plan.md` for full detail)

1. **A hidden challenge page**, unlinked route findable via light recon (not puzzle-gated or breadcrumb-leaked) — surfaces the catalog of intentional vulnerabilities (`docs/vulnerability-matrix.md`, 81 entries) to a "hacker" persona, tracking which ones have actually been found/solved.
2. **A validation sprint (Sprint 40) re-tests all 81 cataloged vulnerabilities live**, not a sample — the challenge page's mechanic depends on genuine current exploitability. **Includes VULN-080/VULN-081's k8s re-confirmation**, deferred here from Release 8 Sprint 33 Epic 3 (2026-08-03 user decision) — see `docs/sprints/sprint-33-plan.md`'s Scope Decision 6.
3. **Per-user solved-state persistence + a real leaderboard** (Sprint 42), not a global/anonymous checklist.
4. **The flag mechanism (2026-08-07 re-scope, now Sprints 43-45)** — flags are embedded directly in what each vulnerability leaks (the same code that serves the leak marks it solved server-side, no request-pattern-sniffing). Random `Aura{...}` format, organizer-controlled global mode toggle (reveal flag vs. just "found!"), popup + manual-submission fallback for non-browser exploitation. Coverage grew from "a flagship handful" to "most vulnerabilities" via reusable embedding patterns per vulnerability *shape* (IDOR-read, SQLi-UNION, stored XSS, etc.) applied broadly rather than 70+ bespoke designs — split across 43 (infrastructure + proving set), 44 (broad rollout + CTF seed script + Solis-delivered flags), 45 (reset script + closing). Full detail: `docs/releases/release-09-plan.md`'s "Sprint 43-45 detailed design" section.

### Sprints

| # | Sprint | Focus |
|---|---|---|
| 40 | Sound Breathing: Roar | ✅ Complete (2026-08-05) — Vulnerability validation: 79 of 81 confirmed unchanged, VULN-025 relocated (Sprint 8/9 had unintentionally removed its original surface), VULN-080/081 re-confirmed live on k8s |
| 41 | Sound Breathing: String Performance | ✅ Complete (2026-08-07) — hidden `/scoreboard` page, catalog grouped by category with tabs, client-side self-report; verified on docker-compose and k8s |
| 42 | Sound Breathing: Constant Resounding Slashes | ✅ Complete (2026-08-07) — real per-user persistence + public leaderboard, VULN-082 (the tracking API's own intentional IDOR+SQLi) confirmed live; verified on docker-compose and k8s |
| 43 | Sound Breathing: Rapid Fire Slice | ✅ Complete (2026-08-08) — flag mechanism infrastructure, 11/12 proving-set findings confirmed live (VULN-077 pending on external Groq quota, not a code issue); two real bugs found and fixed (localStorage-based notification tracking, a silently-failed migration); verified on docker-compose and k8s |
| 44 | Sound Breathing (name TBD) | ✅ Complete (2026-08-08) — 51 new flags across ~15 files, extending Sprint 43's 10 shapes plus an 11th (XXE) and a DB vault-table placement (VULN-043); live-tested via representative sample across all 11 shapes and verified on both docker-compose and k8s (see `docs/vulnerability-matrix.md`'s 2026-08-08 update); also closed out VULN-077's flag (deferred from Sprint 43), confirmed exploitable only via indirect/meta-framed extraction, not a direct ask |
| 45 | Sound Breathing (name TBD, closing) | ✅ Complete (2026-08-08) — CTF seed script (`seed_ctf_victims.py`, 5 synthetic victims: `emma`/`james`/`olivia`/`daniel`/`sophie`), reset script (`reset_ctf.py`, preserves `testuser`/`admin`, cleans orphaned mass-assignment rows), live end-to-end operator-flow rehearsal confirmed (seed → session → reset → reseed). Docker-compose only by explicit decision, k8s out of scope for these scripts. Closes Release 9. Full detail: `docs/sprints/sprint-45-plan.md`, `docs/releases/release-09-overview.md` |
| 46 | CTF Organizer Control Panel (addendum, not a "Sound Breathing" sprint) | ✅ Complete (2026-08-09) — hidden `/ctf-admin` page: mode toggle, one-click seed/reset (`utils/ctf_ops.py`, in-app port of Sprint 45's scripts), organizer-customizable flag prefix (`ctf_settings.flag_prefix`, no migration), issued-flags audit view with By-Time/By-Vulnerability tabs. Verified on docker-compose, then k8s (`sprint46` tag). Full detail: `docs/sprints/sprint-46-plan.md` |

---

## Release 10 — "Twin Reflection" (working title — name and style not yet confirmed with user)

**Theme**: A dedicated audit of `secure-version/` — vulnerabilities, potential bugs, and discrepancies against `vulnerable-version/`'s behavior
**Scope**: `secure-version/` primary focus, but inherently comparative against `vulnerable-version/`
**Status**: ✅ **COMPLETE** | Date: 2026-08-09 — both sprints (47, 48) delivered same day. Full plan: `docs/releases/release-10-plan.md`
**Planned**: 2026-08-02 (initial scope), finalized 2026-08-09

### Scope, as decided (2026-08-09 planning session — see `docs/releases/release-10-plan.md` for full detail)

1. **Full systematic security audit** of the entire `secure-version/` codebase (not sampled/targeted — explicit user decision) — check for vulnerabilities or bugs that may have slipped in despite the "secure by design" intent.
2. **UI differences audit**, run after the security audit — reconciles the backlog's discrepancy-shaped `BUG-*` items (already curated, plus the already-agreed 2026-08-06 global button style resolution) case-by-case, not blanket parity-forcing.
3. Findings documented in a dedicated report: `docs/testing/pentest-report-release-10.md`.
4. No overlap with Release 9 — confirmed entirely `vulnerable-version/`-only, nothing to reconcile.
5. Backlog's Enhancement Requests / UI Improvements are **not** in scope here — deferred to Release 11. A new finding this session (transfers double-counted as both income and expense in dashboard totals — `BUG-18`) also deferred to Release 11, since it's a shared data-accuracy bug, not a security finding or UI discrepancy.

### Sprints

| # | Focus |
|---|---|
| 47 | ✅ Complete (2026-08-09) — Full systematic security audit, all 58 files. Zero Critical/High findings. Report: `docs/testing/pentest-report-release-10.md`. |
| 48 | ✅ Complete (2026-08-09) — Global button style resolution (11 buttons/version) + BUG-04/BUG-10/BUG-17 reconciled. **Post-completion fixes same day**: a dim-text bug in the shared `.btn-glass-secondary` class (repeat of Sprint 46's mistake, fixed at the class level for all affected buttons at once) + three new frontpage discrepancies (card titles, emojis, the frontpage Login link) found via live testing and fixed. Sprint detail: `docs/sprints/sprint-48-plan.md`. |

---

## Release 11 — "Whetstone" (working title — name and style not yet confirmed with user)

**Theme**: General application improvements — new functionality across both versions, in parity, spanning data-accuracy bugs, Loan Intelligence follow-ups, account/security UX, and UI polish
**Scope**: Both `secure-version/` and `vulnerable-version/`, in parity
**Status**: ✅ **COMPLETE** (2026-08-24) — all four sprints shipped and verified on docker-compose and k8s. Full plan: `docs/releases/release-11-plan.md`; close-out: `docs/releases/release-11-overview.md`
**Planned**: 2026-08-02 (initial scope discussion), finalized 2026-08-12 (Release Planning Session)

### Scope, as decided (2026-08-12 planning session — see `docs/releases/release-11-plan.md` for full detail)

Prioritized by impact rather than covering the full 20-item candidate backlog at once (explicit user decision) — real data-accuracy bugs affecting the user's live production totals first, then a curated set of enhancements/UI, with under-scoped or lower-priority items held back.

### Sprints

| # | Focus |
|---|---|
| 50 | ✅ Complete (2026-08-12) — Data accuracy: `BUG-18` (transfer double-counting, also caught in `export.py`'s report endpoint, not originally listed), `BUG-19` (currency aggregate-conversion gap + `get_category_breakdown()` fix), `ENH-06` (transfers excluded from Transactions list by default), `ENH-05` (real filter UI, absorbing `ENH-07`). Verified against real k8s production data (is_transfer flag-consistency check, exact match) and live dashboard/report totals after deploy. Sprint detail: `docs/sprints/sprint-50-plan.md`. |
| 51 | ✅ Complete (2026-08-12) — Loan Intelligence follow-ups: `ENH-01` (edit/delete a loan, safe fields only), `ENH-12` (recurring installment auto-sync), `ENH-13` (loan payment ledger, depended on ENH-12 as expected). Verified on docker-compose and k8s against real production data. Sprint detail: `docs/sprints/sprint-51-plan.md`. |
| 52 | ✅ Complete (2026-08-13) — Account/security UX: `ENH-03` (forgot/reset password, real SMTP, separate credentials per version), `ENH-04` (2FA via TOTP), `ENH-09` (alphabetize Accounts/Loans dropdowns), `ENH-10` (searchable category select). Two real bugs found and fixed during testing (CSP blocking the 2FA QR code; a password-reset bug that locked vulnerable-version users out of their own account). New `VULN-083`/`VULN-084` cataloged. Sprint detail: `docs/sprints/sprint-52-plan.md`. |
| 53 | ✅ Complete (2026-08-24) — UI: `UI-01` (Accounts drag-and-drop reordering, supersedes Sprint 52's `ENH-09` alphabetical sort for accounts; vulnerable-version's reorder endpoint cataloged as `VULN-085`, not yet confirmed live). `UI-02` (Dashboard stat card drag-and-drop reordering, first server-persisted user preference in either version; vulnerable-version's endpoint cataloged as `VULN-086`, not yet confirmed live). `UI-03` (pagination First/Last + page-jump controls, all 4 call sites: Transactions list, Loans' Payment Impact + Event Timeline). `UI-04` ("Interlocking Rings" glassmorphism mark + favicon — a deliberate pivot from the originally-planned theme-adaptive `currentColor` mark to a fixed indigo gradient, after an extended design-review process against two rounds of AI-generated concepts). All four verified on docker-compose and k8s, both namespaces (`UI-01` under tag `sprint53`, `UI-02`/`UI-03`/`UI-04` together under tag `sprint53b`). Sprint detail: `docs/sprints/sprint-53-plan.md`. |

### Held back — not part of Release 11

`ENH-02` (admin page — scope too vague to size yet), `ENH-11` (savings interest — needs its own scoping discussion, narrowed 2026-08-24 with per-account/balance-based accrual detail), `ENH-14` (k8s HTTPS/cert — isolated infra, can slot in anytime), `ENH-08` (category merge — one-off production DB operation, not a sprint item, still genuinely pending). ("Fixing the k8s GROQ API," deferred at this same planning session, was separately resolved 2026-08-12 — see `docs/backlog.md`.)

New items surfaced during Release 11's own sprints, never part of its scope: `BUG-20` (Loan Intelligence Payment Impact card reporting a suspicious result on real production data, investigation deferred) and `ENH-15` (extend `ENH-10`'s searchable-combobox pattern elsewhere, not sized). See `docs/releases/release-11-overview.md` for the full close-out.

---

## Release 12 — "Total Concentration"

**Theme**: Carry-over data-accuracy fix (Loan Intelligence), outstanding security validation, old UI bugs, and a backlog-grooming pass that grew into a full build sprint
**Scope**: Both `secure-version/` and `vulnerable-version/`, item-dependent (not full parity by default the way Release 11 was)
**Status**: ✅ **COMPLETE** (closed 2026-09-05) | Full overview: `docs/releases/release-12-overview.md`
**Planned**: 2026-08-24 (Release Planning Session, same day Release 11 closed)

### Scope, as decided (2026-08-24 planning session — see `docs/releases/release-12-plan.md` for full detail)

Everything currently pending from Release 11's close-out and the open backlog goes into this release, in different sprints grouped by theme (explicit user decision) — rather than holding items back for further scoping the way Release 11 did. `BUG-20` gets a full root-cause fix, not a minimal patch (explicit user decision) — root-caused the same day: a shared gap where `effective_date` on loan events/snapshots has no secondary ordering, producing three symptoms (same-day snapshot-vs-snapshot ties, a same-day snapshot wrongly surviving into a payment's own counterfactual, and general asymmetric pinning between the `actual` and `variant` tracks). Full root-cause writeup in `docs/releases/release-12-plan.md`.

### Sprints

| # | Focus |
|---|---|
| 54 | ✅ Closed (2026-08-28) — Data Accuracy: `BUG-20` full root-cause fix in `loan_engine.py`/`routes/api/loans.py`, both versions — a complete `get_payment_impact()` redesign (`start_override`-based symmetric local runs, anchored strictly before each payment's date, preferring the bank's own reported `remaining_term_months` over simulated math wherever real data cleanly brackets a payment). Every real payment now matches the official bank loan charts exactly, except two payments in an acknowledged, permanent 2021–2025-04 rate-history gap (accepted limitation, not a bug). A suspected duplicate-loan data-integrity issue was investigated and retracted as a false lead (two different real user accounts, not a duplicate — no fix needed). Deployed and verified live against real k8s production data. Sprint detail: `docs/sprints/sprint-54-plan.md`. |
| 55 | ✅ Closed (2026-09-02) — Security Validation: `VULN-085`/`VULN-086` confirmed live on `vulnerable-version/` (SQLi + IDOR, no auth, on the Accounts reorder and stat-card-order endpoints — the latter chained to a full plaintext-password leak). Cataloged in `docs/vulnerability-matrix.md`. |
| 56 | ✅ Closed (2026-09-02) — UI Polish: `BUG-06` (Category Heatmap fixed category column, several iterations before landing on this app's own "Customize" button styling), `BUG-07` (new-dashboard Customize panel stale state + widget render gap — an early `return` skipped a state refresh), `BUG-09` (Exchange Rates card hover scrollbar — a shared hover transform creating new scrollable overflow). All three user-confirmed live on docker-compose and on k8s (tag `sprint56`), both versions. |
| 57 | ✅ Closed (2026-09-05) — Backlog Grooming + `ENH-08`, grew into a full build sprint. `ENH-08` (Salary/Salar category merge) done. `ENH-02` (admin panel, all 6 groups + impersonation) done, deployed to real k8s (secure-version). `ENH-11` (savings interest, both versions) done on docker-compose, not yet deployed to k8s — scheduler job's first real run not yet observed. `ENH-14` (k8s HTTPS on default port + mkcert-trusted cert) done — VM/Windows/Linux confirmed, iPhone gap accepted. `ENH-15` (searchable combobox extended to Recurring + Budgets, both versions) done on docker-compose. `ENH-16` (Loan Intelligence months/years exact-count fix, both versions) done, user-verified against real bank snapshot data — added same day after two real bugs were caught via live testing. Full detail: `docs/releases/release-12-overview.md`. |

---

## Enhancement Backlog

Enhancements discussed but not yet scheduled:

| ID | Description | Target Release |
|---|---|---|
| ENH-006 | Full CRUD dashboard creation — user-defined named dashboards | Release 4 Sprint 9 |
| ~~ENH-008~~ | ~~Mobile responsive sidebar~~ | ~~Dropped by user decision — not a priority; may revisit in a future release~~ |
| ENH-009 | Additional Abyss colour themes / theme switcher expansion | Release 7 |
| ENH-010 | Per-widget reorder (drag-and-drop, SortableJS) | Release 5 Sprint 19 |
| ENH-011 | YoY category comparison widget | Release 5 Sprint 20 |
| — | CI/CD Pipeline (GitHub Actions — lint, Docker build; test suite once one exists) | Deferred from Release 5, TBD |
| ENH-012 | Loan amortisation schedule tracker (dedicated table) | Release 8 |

---

## Vulnerability Coverage

| Release | New Vulns | Cumulative |
|---|---|---|
| Release 1 | ~27 | 27 |
| Release 2 | 18 | 45 |
| Release 3 | 12+ (Sprint 8 follows same patterns) | ~57 |
| Release 4 | Secure version remediations | N/A |

Full vulnerability details in `docs/vulnerability-matrix.md`.

---

## Tech Stack Summary

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + Flask 3.0 |
| Database | MySQL 8.0 |
| Frontend | HTML5 + CSS3 (Liquid Glass) + Bootstrap 5 + Chart.js + vanilla JS |
| Containerisation | Docker + Docker Compose |
| Scheduling | APScheduler (recurring transactions) |
| Planned infra | Kubernetes + Helm + Prometheus + Grafana |

---

## Key Project Conventions

| Convention | Value |
|---|---|
| Sprint length | 1 week |
| Sprint naming | Demon Slayer breathing style + ordinal form |
| Story point scale | Simple = 1pt, Medium = 2pt, Complex = 3pt |
| Scope rule | Changes to `vulnerable-version/` never automatically apply to `secure-version/` |
| Vulnerability rule | Intentional vulnerabilities in `vulnerable-version/` must never be fixed |
| DB rule | New columns: never use `ADD COLUMN IF NOT EXISTS` (MariaDB syntax, rejected by MySQL 8.0) |

---

*Roadmap is a living document. Update after each sprint retrospective.*

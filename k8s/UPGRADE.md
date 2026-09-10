# Aura — Kubernetes Upgrade Runbook

Reusable procedure for rolling a new sprint's code + DB changes out to an
**already-running** cluster (secure and vulnerable namespaces already
deployed, PVCs already initialized). If you're deploying from scratch,
use `k8s/README.md` or `k8s/TESTING.md` instead — this doc is specifically
for "day 2" upgrades, where `docker-entrypoint-initdb.d`-style ConfigMap
init scripts won't rerun automatically because the volume already has data.

Every Release 5 sprint from Sprint 17 onward ends with a Deploy & Verify
story that follows these steps (see `docs/releases/release-05-plan.md`).

---

## ⚠️ Read this first: the `:latest` + `IfNotPresent` trap

Every manifest in `k8s/base/` uses `image: aura-app-secure:latest` (and
`aura-app-vulnerable:latest`) with `imagePullPolicy: IfNotPresent`. That
policy makes kubelet ask a purely *string-based* question before starting a
container: "do I already have anything cached under this exact tag?" — not
"is this the newest version." Combined with `minikube image load` having
its own similar "already loaded this tag, skip" shortcut, the two together
can produce a cluster that silently keeps running old code through any
number of rebuild → load → restart cycles, **with no error anywhere in the
process.** This bit Sprint 17's own rollout hard — see "Worked example"
below for the full story of what happened and how it was diagnosed.

**The reliable fix, confirmed working**: use a unique, never-before-seen
tag for the upgrade, and point the Deployment at it explicitly:

```bash
docker build -t aura-app-secure:sprintNN ./secure-version
docker build -t aura-app-vulnerable:sprintNN ./vulnerable-version
minikube image load aura-app-secure:sprintNN
minikube image load aura-app-vulnerable:sprintNN

kubectl set image deployment/app-secure app-secure=aura-app-secure:sprintNN -n aura-secure
kubectl set image deployment/app-vulnerable app-vulnerable=aura-app-vulnerable:sprintNN -n aura-vulnerable
```

A tag that never existed before **cannot** have stale cached content under
it, so there's no ambiguity for kubelet or minikube to get wrong — and
`kubectl set image` changes the pod template itself, which unambiguously
forces a real new revision (verifiable via `kubectl rollout history`,
unlike `kubectl rollout restart`, which should also always create a new
revision by design but did not reliably do so in practice this sprint —
cause unconfirmed, so don't trust it blindly; always verify the revision
number actually incremented, not just that `rollout status` reports
success). Steps 1 and 4 below still show the plain `:latest` flow, since
that's what the manifests declare and it may well work — but treat step 5
(verify) as mandatory before considering an upgrade done, and fall back to
the unique-tag approach immediately if verification fails.

---

## 0. Before you start

- [ ] Confirm which namespaces/deployments you're touching this sprint —
      `app-secure` (`aura-secure`), `app-vulnerable` (`aura-vulnerable`),
      or both. Most sprints touch both, in parity.
- [ ] Confirm whether this sprint has a DB migration (`database/init-*.sql`
      files added since the last deploy). If yes, note the exact filenames
      — you'll apply them by hand in step 3.
- [ ] Confirm whether this sprint's docker-compose testing already
      surfaced bugs that got hotfixed mid-sprint (extra `*-hotfix.sql`
      files, extra ConfigMap keys) — those need to come along too, not
      just the sprint's "headline" migration file.
- [ ] If you have the LAN port-forward systemd services running
      (`k8s/setup-lan-portforward.sh`), you don't need to stop them for
      this procedure — they point at Service names, not specific pods, so
      they keep working through pod restarts with at most a few seconds
      of reconnect time.

---

## 1. Rebuild the images

```bash
docker build -t aura-app-secure:latest ./secure-version
docker build -t aura-app-vulnerable:latest ./vulnerable-version
```

(`docker compose build` produces the same tags, so building via compose
works too — see `k8s/README.md` for why the tag names matter.)

Load the new image content into the cluster. **This step matters even
though the tag (`:latest`) doesn't change** — `minikube image load`
overwrites what that tag points to inside the cluster's image store, but
nothing forces already-running pods to notice; that happens in step 4.

```bash
minikube image load aura-app-secure:latest
minikube image load aura-app-vulnerable:latest
```

---

## 2. Apply changed/new manifests

If this sprint changed any YAML under `k8s/base/` (new env vars, probe
tweaks, new Ingress rules, etc.), apply it now:

```bash
kubectl apply -f k8s/base/secure/
kubectl apply -f k8s/base/vulnerable/
kubectl apply -f k8s/base/monitoring/
```

`kubectl apply` is safe to run even for unchanged files — it no-ops
(`unchanged`) on anything identical to what's already live. If you're on
the Helm path instead:

```bash
helm upgrade aura ./k8s/helm/aura
```

---

## 3. Apply this sprint's DB migration(s) against the live pods

The PVCs already have data, so `docker-entrypoint-initdb.d` won't rerun
these automatically (same caveat as docker-compose). Pipe each new SQL
file into the running MySQL pod directly:

```bash
# Secure
kubectl exec -i -n aura-secure deploy/mysql-secure -- \
  mysql -uroot -p'SecureRootPass123!' aura_secure < database/init-secure-sprintNN.sql

# Vulnerable
kubectl exec -i -n aura-vulnerable deploy/mysql-vulnerable -- \
  mysql -uroot -p'VulnRootPass123!' aura_vulnerable < database/init-vulnerable-sprintNN.sql
```

Repeat for every new file this sprint added — including any `-hotfix`
files discovered during docker-compose testing (check your `git status`
for untracked/new files under `database/` to be sure you don't miss one).
Apply them in the same numeric order their ConfigMap keys use (see step
3b) — a hotfix file that depends on its parent sprint's schema will error
if applied first.

**Watch the output of each command.** A `CREATE TABLE IF NOT EXISTS` or
`ALTER TABLE ... ADD COLUMN` that fails (e.g. "Duplicate column name")
usually means this migration was already applied — safe to ignore *only
after confirming* via `DESCRIBE <table>` that the expected column/table is
actually there, not just assuming.

### 3b. Update the init ConfigMap too (for future fresh deploys)

The migration you just applied by hand won't be there if someone spins up
a **new** cluster from scratch later — the ConfigMap in `k8s/README.md`
step 1 needs the same new file added as a new numbered key, or a fresh
deploy will silently be missing this sprint's schema changes:

```bash
kubectl create configmap mysql-secure-init -n aura-secure \
  --from-file=01-init.sql=database/init-secure.sql \
  ... \
  --from-file=NN-sprintNN.sql=database/init-secure-sprintNN.sql \
  --dry-run=client -o yaml | kubectl apply -f -
```

Using `--dry-run=client -o yaml | kubectl apply -f -` instead of a plain
`kubectl create configmap` lets you re-run the *full* key list (including
everything from prior sprints) without first deleting the old ConfigMap —
`kubectl create` alone fails if the ConfigMap already exists. Copy the
complete up-to-date `--from-file=...` list from `k8s/README.md` (update
that doc with the new key first, then paste from there, so the two never
drift apart).

---

## 4. Restart the app deployments

This is what actually makes running pods pick up the freshly-loaded image
(step 1) and any new ConfigMap/Secret values (step 2):

```bash
kubectl rollout restart deployment/app-secure -n aura-secure
kubectl rollout restart deployment/app-vulnerable -n aura-vulnerable

kubectl rollout status deployment/app-secure -n aura-secure
kubectl rollout status deployment/app-vulnerable -n aura-vulnerable
```

`rollout status` blocks until the new pods are ready (or fails loudly if
they crash-loop) — don't move to verification until both return
`successfully rolled out`. **That message alone is not proof a new rollout
actually happened** — it also prints trivially if the deployment was
already fully available beforehand (Sprint 17 hit exactly this: `rollout
status` reported success while pods were still 18 hours old). Confirm a
new revision actually exists:

```bash
kubectl rollout history deployment/app-secure -n aura-secure
kubectl get pods -n aura-secure -o wide   # AGE should be seconds/minutes old, RESTARTS 0
```

If the revision number didn't increment or `AGE` is old, the restart
didn't take — skip straight to the unique-tag approach at the top of this
doc rather than repeating `rollout restart`.

If MySQL itself changed (rare — usually only probe/resource tweaks, since
schema changes go through step 3, not a new image), restart it too:

```bash
kubectl rollout restart deployment/mysql-secure -n aura-secure
kubectl rollout restart deployment/mysql-vulnerable -n aura-vulnerable
```

---

## 5. Verify

1. **Health checks:**
   ```bash
   kubectl port-forward -n aura-secure svc/app-secure 5050:80 &
   curl -s http://localhost:5050/health | python3 -m json.tool
   ```
   Expect `{"status": "ok", "checks": {"database": "ok"}}`. Repeat for
   `app-vulnerable` on a different local port.

2. **Feature smoke test** — exercise whatever this sprint actually shipped,
   not just that the app boots. `/health` alone is not enough — it only
   checks DB connectivity and will happily report `ok` even on a pod
   running last sprint's code, which is exactly how Sprint 17's stale
   rollout went unnoticed until an actual browser check. For Sprint 17
   (multi-currency): log in, confirm the Exchange Rates page loads real
   rate data (not a 500), add an account in a non-RON currency, confirm
   Net Worth on the Accounts page shows a converted total rather than a
   naive sum.

   For a faster, scriptable version of the same check, `exec` into the pod
   and confirm a file/string that only exists in this sprint's code is
   actually there — this is what caught the stale-image problem directly:
   ```bash
   kubectl exec -n aura-secure deploy/app-secure -- test -f /app/routes/api/some_new_file.py
   kubectl exec -n aura-secure deploy/app-secure -- grep -c "some new UI string" /app/templates/some/page.html
   ```

3. **Prometheus targets** (if this sprint touched anything metrics-related):
   `http://localhost:9090/targets` — all targets `UP`.

4. **Logs, if anything looks off:**
   ```bash
   kubectl logs -n aura-secure deploy/app-secure --tail=50
   kubectl logs -n aura-vulnerable deploy/app-vulnerable --tail=50
   ```

---

## 6. Rollback

**App code** (image/manifest changes) rolls back cleanly:

```bash
kubectl rollout undo deployment/app-secure -n aura-secure
kubectl rollout undo deployment/app-vulnerable -n aura-vulnerable
```

This reverts to the previous ReplicaSet's pod template. **If you used a
unique per-sprint tag** (the recommended approach above), this actually
works correctly — the previous ReplicaSet's pod spec still references the
*previous* sprint's real tag (e.g. `aura-app-secure:sprint16`), which still
exists and still has the old code, so `rollout undo` genuinely restores it.

If you deployed on plain `:latest` instead, `rollout undo` is **not
trustworthy for app code** — the previous ReplicaSet's pod spec still just
says `image: aura-app-secure:latest`, which now resolves to whatever the
*current* image content is, not what was actually running before. This is
the same ambiguity described at the top of this doc. To truly roll back
app code under `:latest`, you'd have to rebuild/reload the previous
commit's code first, then run `rollout undo` — another reason to prefer
unique tags going forward.

**DB migrations do not have an automated rollback.** SQL migrations in
this project are forward-only (matches the docker-compose workflow used
all sprint). If a migration needs reverting, write and apply a new
hand-written "undo" SQL file (drop the added column/table, etc.) through
the same `kubectl exec -i ... mysql ...` pattern as step 3 — there's no
tooling shortcut for this, budget time accordingly if a migration turns
out to be wrong after real data has been written against it.

---

## Sprint 23–26 catch-up (Release 6 — AI Advisor)

Unlike every prior Deploy & Verify, Sprints 23–26 were **not** deployed to k8s one at a time — docker-compose was verified after each sprint (per each sprint's own retrospective), but k8s deployment was deliberately deferred until Release 6 closed, by explicit user decision at Sprint 27. This section rolls all four sprints into a single catch-up deploy, following the same 6-step procedure above with the specifics that apply here.

**What changed across all four sprints** (the full diff this catch-up needs to carry):
- New Python modules: `models/ai_conversation.py`, `models/ai_pending_action.py` (secure only), `utils/ai_context.py`, `utils/ai_insights.py`, `utils/ai_tools.py`, `utils/groq_client.py`, `routes/api/ai_advisor.py`
- Modified: `app.py` (blueprint registration), `config.py` (`GROQ_API_KEY`/`GROQ_MODEL`), `requirements.txt` (added `requests`), `scheduler.py` (three new jobs: AI insight generation, AI conversation cleanup, notification job unchanged), `models/user.py`, `models/transaction.py`, `models/recurring_transaction.py`, `models/notification.py` (vulnerable only — quote-escaping fix), `models/budget.py`, `models/transfer.py`, `routes/auth.py`, `templates/base.html`, `static/css/glass.css`, `static/js/chat.js`
- **DB migrations, in order**: `database/init-{secure,vulnerable}-sprint23.sql` (`ai_conversations`), `database/init-{secure,vulnerable}-sprint25.sql` (`ALTER TABLE notifications MODIFY message TEXT`), `database/init-secure-sprint26.sql` (`ai_pending_actions` — **secure only**, no vulnerable equivalent). Sprint 24 shipped no schema changes.
- **New required config**: `GROQ_API_KEY` (real external credential, two separate values — one per version) and `GROQ_MODEL` (not secret, already added to both ConfigMaps in `k8s/base/{secure,vulnerable}/02-app.yaml`).

### Step 1 — Apply the GROQ_API_KEY secret (out-of-band, not committed)

This is the one departure from every prior sprint's Secrets: `DATABASE_PASSWORD`/`SECRET_KEY` are fake lab values already committed in the manifests, but `GROQ_API_KEY` is a real credential with real billing implications and must never be committed. Recreate each Secret with its existing (already-public, already-fake) values plus your real key, using the same `--dry-run=client -o yaml | kubectl apply -f -` idiom already established for ConfigMaps in step 3b above — this replaces the Secret's full contents, so every existing key needs to be listed again, not just the new one:

```bash
kubectl create secret generic app-secure-secrets -n aura-secure \
  --from-literal=DATABASE_PASSWORD='SecureUserPass123!' \
  --from-literal=SECRET_KEY='secure-secret-key-change-in-production-xyz123' \
  --from-literal=GROQ_API_KEY='<your real secure-version Groq key>' \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic app-vulnerable-secrets -n aura-vulnerable \
  --from-literal=DATABASE_PASSWORD='VulnUserPass123!' \
  --from-literal=SECRET_KEY='weak-secret-123' \
  --from-literal=GROQ_API_KEY='<your real vulnerable-version Groq key — must be different from the secure one>' \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Step 2 — Apply the ConfigMap changes (GROQ_MODEL, already committed)

```bash
kubectl apply -f k8s/base/secure/
kubectl apply -f k8s/base/vulnerable/
```

### Step 3 — Rebuild images under a unique tag and load them

Given this catches up four sprints at once, use a single tag covering all of them rather than one per sprint:

```bash
docker build -t aura-app-secure:sprint23to26 ./secure-version
docker build -t aura-app-vulnerable:sprint23to26 ./vulnerable-version
minikube image load aura-app-secure:sprint23to26
minikube image load aura-app-vulnerable:sprint23to26

kubectl set image deployment/app-secure app-secure=aura-app-secure:sprint23to26 -n aura-secure
kubectl set image deployment/app-vulnerable app-vulnerable=aura-app-vulnerable:sprint23to26 -n aura-vulnerable
```

### Step 4 — Apply the DB migrations, in order

```bash
# Secure
kubectl exec -i -n aura-secure deploy/mysql-secure -- \
  mysql -uroot -p'SecureRootPass123!' aura_secure < database/init-secure-sprint23.sql
kubectl exec -i -n aura-secure deploy/mysql-secure -- \
  mysql -uroot -p'SecureRootPass123!' aura_secure < database/init-secure-sprint25.sql
kubectl exec -i -n aura-secure deploy/mysql-secure -- \
  mysql -uroot -p'SecureRootPass123!' aura_secure < database/init-secure-sprint26.sql

# Vulnerable (no sprint26 file — ai_pending_actions is secure-only)
kubectl exec -i -n aura-vulnerable deploy/mysql-vulnerable -- \
  mysql -uroot -p'VulnRootPass123!' aura_vulnerable < database/init-vulnerable-sprint23.sql
kubectl exec -i -n aura-vulnerable deploy/mysql-vulnerable -- \
  mysql -uroot -p'VulnRootPass123!' aura_vulnerable < database/init-vulnerable-sprint25.sql
```

### Step 5 — Verify: revision incremented, health, then a real feature smoke test

```bash
kubectl rollout history deployment/app-secure -n aura-secure
kubectl rollout history deployment/app-vulnerable -n aura-vulnerable
kubectl get pods -n aura-secure -o wide
kubectl get pods -n aura-vulnerable -o wide
```

Confirm a genuinely new revision and fresh `AGE` before trusting anything else — per this doc's standing warning, `rollout status` alone is not proof.

```bash
kubectl port-forward -n aura-secure svc/app-secure 5050:80 &
curl -s http://localhost:5050/health | python3 -m json.tool
kubectl port-forward -n aura-vulnerable svc/app-vulnerable 5051:80 &
curl -s http://localhost:5051/health | python3 -m json.tool
```

Then the real smoke test — `/health` won't catch a stale rollout here any more than it did in Sprint 17:
1. Log in on both, open the Solis chat bubble, send a message, confirm a real Groq reply comes back (proves `GROQ_API_KEY` actually reached the pod).
2. On secure, ask Solis to create a transaction — confirm the pending-action confirmation card appears (proves `ai_pending_actions` migration landed and the tool-calling code path is live).
3. On vulnerable, do the same — confirm it executes immediately with no confirmation (proves the same code path, opposite behavior, is live).
4. Check logs for the new scheduler jobs registering on startup:
   ```bash
   kubectl logs -n aura-secure deploy/app-secure --tail=100 | grep -i "AI insight\|AI conversation cleanup"
   kubectl logs -n aura-vulnerable deploy/app-vulnerable --tail=100 | grep -i "AI insight\|AI conversation cleanup"
   ```
   Expect to see both `[Scheduler] AI insight job registered` and `[Scheduler] AI conversation cleanup job registered` in each.

### Step 6 — Update the init ConfigMap for future fresh deploys

Already updated in `k8s/README.md` with the new `23-sprint23.sql`/`25-sprint25.sql`/`26-sprint26.sql` keys — run the full recreate command from there (not just the new keys) so a future from-scratch deploy doesn't drift from what's actually live:

```bash
kubectl create configmap mysql-secure-init -n aura-secure \
  --from-file=01-init.sql=database/init-secure.sql \
  --from-file=11-sprint11.sql=database/init-secure-sprint11.sql \
  --from-file=12-sprint12.sql=database/init-secure-sprint12.sql \
  --from-file=13-sprint13.sql=database/init-secure-sprint13.sql \
  --from-file=13b-sprint13-hotfix.sql=database/init-secure-sprint13-hotfix.sql \
  --from-file=14-sprint14.sql=database/init-secure-sprint14.sql \
  --from-file=15-sprint15.sql=database/init-secure-sprint15.sql \
  --from-file=17-sprint17.sql=database/init-secure-sprint17.sql \
  --from-file=17c-sprint17-currencies.sql=database/init-secure-sprint17-currencies.sql \
  --from-file=18-sprint18.sql=database/init-secure-sprint18.sql \
  --from-file=20-sprint20.sql=database/init-secure-sprint20.sql \
  --from-file=20b-sprint20-colors.sql=database/init-secure-sprint20-colors.sql \
  --from-file=21-sprint21.sql=database/init-secure-sprint21.sql \
  --from-file=23-sprint23.sql=database/init-secure-sprint23.sql \
  --from-file=25-sprint25.sql=database/init-secure-sprint25.sql \
  --from-file=26-sprint26.sql=database/init-secure-sprint26.sql \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap mysql-vulnerable-init -n aura-vulnerable \
  --from-file=01-init.sql=database/init-vulnerable.sql \
  --from-file=02-sprint2.sql=database/init-vulnerable-sprint2.sql \
  --from-file=03-sprint3.sql=database/init-vulnerable-sprint3.sql \
  --from-file=04-sprint4.sql=database/init-vulnerable-sprint4.sql \
  --from-file=06-sprint6.sql=database/init-vulnerable-sprint6.sql \
  --from-file=08-sprint8.sql=database/init-vulnerable-sprint8.sql \
  --from-file=09b-sprint9b.sql=database/init-vulnerable-sprint9b.sql \
  --from-file=17-sprint17.sql=database/init-vulnerable-sprint17.sql \
  --from-file=17b-sprint17-hotfix.sql=database/init-vulnerable-sprint17-hotfix.sql \
  --from-file=18-sprint18.sql=database/init-vulnerable-sprint18.sql \
  --from-file=20-sprint20-colors.sql=database/init-vulnerable-sprint20-colors.sql \
  --from-file=21-sprint21.sql=database/init-vulnerable-sprint21.sql \
  --from-file=23-sprint23.sql=database/init-vulnerable-sprint23.sql \
  --from-file=25-sprint25.sql=database/init-vulnerable-sprint25.sql \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## Sprint 28–33 catch-up (Release 8 — Loan Intelligence)

Same deferred-until-release-closes pattern as Sprints 23–26: every sprint
from 28 through 32 explicitly deferred its k8s work to Sprint 33's Deploy &
Verify epic. This one also caught a real scope gap worth recording: the
sprint plan's own scope decision said "Sprints 29, 31, and 32 shipped no
schema changes," which was true, but didn't account for
`database/init-secure-sprint34-admin.sql` — an ad-hoc migration added
alongside admin-panel work that predates this sprint's numbering but had
never been deployed anywhere. Found by diffing `database/init-*.sql`
against the sprint plan's migration list rather than trusting the list at
face value, then confirmed as a hard requirement (not optional) by grepping
the app code for `is_admin` and finding it live in `routes/main.py`,
`routes/auth.py`, `models/user.py`, and `base.html` — deploying the new
image without this migration would have broken any query touching that
column. **Lesson for future catch-ups: always grep/glob for migration files
against the sprint plan's own list before trusting "no schema changes" —
it's a claim about what a sprint intended to ship, not a guarantee about
every file that ended up in `database/`.**

**What changed across Sprints 28–32** (the full diff this catch-up carried):
- Loan Intelligence: `models/loan.py`, `routes/api/loans.py`,
  `utils/loan_engine.py`, `utils/chart_parser.py`, the dedicated `/loans`
  page and its Dashboard widgets (Loan Summary, All Loans Overview, Payoff
  Trajectory, Debt Reduction Impact, Interest Overview)
- Reports/CSV/OFX/QIF export-import, structured JSON logging, synthetic
  demo data seeder
- **Migrations, in order**: `init-secure-sprint28.sql`,
  `init-vulnerable-sprint28.sql` (Loan Intelligence schema — both versions),
  `init-secure-sprint30.sql` (secure-only `CHECK` constraint update —
  vulnerable's schema doesn't enforce it, no vulnerable file exists),
  `init-secure-sprint34-admin.sql` (secure-only `users.is_admin` column —
  the scope-gap finding above; vulnerable's `/admin` stays intentionally
  ungated per VULN-002, no equivalent needed)
- **No manifest changes** — checked `k8s/base/{secure,vulnerable}/02-app.yaml`
  against `config.py` for new required env vars from all five sprints;
  found none. `GROQ_MODEL` was already committed from the Sprint 23–26
  catch-up. `kubectl apply -f k8s/base/` still run for safety (no-ops
  correctly on unchanged manifests) but was not actually required this time.

### Execution

Rebuilt under a single `sprint28to33` tag (unique-tag approach from the
start, not `:latest` — no repeat of Sprint 17's stale-cache trap):

```bash
docker build -t aura-app-secure:sprint28to33 ./secure-version
docker build -t aura-app-vulnerable:sprint28to33 ./vulnerable-version
minikube image load aura-app-secure:sprint28to33
minikube image load aura-app-vulnerable:sprint28to33

kubectl set image deployment/app-secure app-secure=aura-app-secure:sprint28to33 -n aura-secure
kubectl set image deployment/app-vulnerable app-vulnerable=aura-app-vulnerable:sprint28to33 -n aura-vulnerable
```

Migrations applied via `kubectl exec -i ... mysql ...` in the order listed
above. Verified via `kubectl rollout history` — both deployments landed on
revision 11, with pod `AGE` at 6–7 minutes at verification time (not hours),
confirming this was a genuine new rollout, not a false-success repeat of
Sprint 17. `/health` returned `ok` on both, followed by a real browser smoke
test (login, Loans page showing real numbers, Solis narrating loan status
correctly, Add Loan form creating a loan) on both versions before this was
considered done — `/health` alone was deliberately not treated as
sufficient, per this doc's standing warning.

ConfigMaps updated last (`k8s/README.md`'s key list extended with
`28-sprint28.sql`, `30-sprint30.sql`, `34-sprint34-admin.sql` for secure and
`28-sprint28.sql` for vulnerable) via the same
`--dry-run=client -o yaml | kubectl apply -f -` idiom as the Sprint 23–26
catch-up, so a future from-scratch cluster deploy won't silently miss
Release 8's schema.

---

## Worked example: Sprint 17 (Multi-Currency)

What actually shipped, and the real story of how the rollout went — kept
in full because the failure mode is the most valuable part of this
example:

- **Images**: rebuilt both, `minikube image load`'d both under `:latest`
  (currency conversion touched both app codebases extensively).
- **Manifests**: no YAML changes this sprint (no new env vars, no new
  probes) — step 2 was a no-op.
- **Migrations applied, in order**:
  1. `database/init-secure-sprint17.sql` / `init-vulnerable-sprint17.sql`
     — `accounts.currency` column, `exchange_rates` table (MC-001)
  2. `database/init-secure-sprint13-hotfix.sql` — missing
     `transactions.is_transfer` column, discovered during manual
     transfer-testing (unrelated to currency, but surfaced the same week)
  3. `database/init-vulnerable-sprint17-hotfix.sql` — dedupe +
     `UNIQUE(currency_code)` on `exchange_rates`, fixing VULN-065's
     duplicate-row behavior (explicit user request — see
     `docs/vulnerability-matrix.md`)
  4. `database/init-secure-sprint17-currencies.sql` — new `currencies`
     reference table; `accounts.currency` and `exchange_rates.currency_code`
     converted from fixed `ENUM` to `FOREIGN KEY REFERENCES currencies(code)`
  All four verified correct at the schema level via `DESCRIBE`/`SHOW CREATE
  TABLE` on the live pods — the DB side was never actually the problem.
- **First restart attempt (failed)**: `kubectl rollout restart` on both
  deployments, `rollout status` reported `successfully rolled out` on
  both. Looked done. It wasn't — see below.
- **What went wrong**: browser testing days later showed neither app had
  any of the sprint's features. `kubectl rollout history` showed both
  deployments stuck on a revision created 18 hours earlier — the
  `rollout restart` had not produced a new revision at all, despite
  reporting success. Rebuilding with `--no-cache`, reloading with
  `minikube image load --overwrite`, and force-deleting the pods
  (`kubectl delete pod -l app=...`) *still* didn't fix it — the freshly
  deleted, freshly recreated pods came back with the same stale code.
  Root cause: the `:latest` tag + `IfNotPresent` trap described at the top
  of this doc — some combination of minikube's image-load caching and
  kubelet's "already present" check meant the node's cached `:latest`
  image was never actually being replaced, and no step in the process
  surfaced an error anywhere.
- **The actual fix**: rebuilt under a throwaway unique tag
  (`aura-app-secure:sprint17fix`), `minikube image load`'d that tag, then
  `kubectl set image deployment/app-secure app-secure=aura-app-secure:sprint17fix
  -n aura-secure` (and the vulnerable equivalent). This produced a genuine
  new revision immediately, and `kubectl exec` checks for sprint-specific
  files/strings confirmed the new code was actually present within
  minutes — first time in the whole rollout that verification actually
  passed.
- **Verify**: `/health` on both (was passing the whole time — it doesn't
  check app version, only DB connectivity, which is exactly why it didn't
  catch this), then the multi-currency smoke test in a real browser, which
  is what actually confirmed success.

---

*Sprint 17 — Insect Breathing: Butterfly Dance – Caprice | OPS-001 | Release 5 "Sovereign Ascent"*

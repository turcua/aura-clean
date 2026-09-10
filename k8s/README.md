# Aura — Kubernetes Deployment

Sprint 16 (Release 4: Iron Fortress). Two ways to deploy: raw manifests
(`k8s/base/`) or the Helm chart (`k8s/helm/aura/`) — pick one, don't mix them
in the same cluster (both create the same namespaces/resource names).

This doc covers a **fresh** deploy. If you already have a cluster running
and just need to roll out a new sprint's changes, use `k8s/UPGRADE.md`
instead — it covers rebuilding images, applying new migrations against
live pods, and restarting deployments without wiping data.

Everything here is written for a **local** cluster (kind/minikube/k3d) — no
container registry or Ingress controller is assumed. Adjust `image.repository`
and add an Ingress if deploying to a real cluster.

## 0. Build the images

```bash
docker build -t aura-app-secure:latest ./secure-version
docker build -t aura-app-vulnerable:latest ./vulnerable-version
```

(`docker compose build` produces the same `aura-app-secure:latest` /
`aura-app-vulnerable:latest` tags, so building via compose works too.)

Load them into your cluster (skip if your cluster shares the host's Docker
daemon, e.g. Docker Desktop's built-in Kubernetes):

```bash
# kind
kind load docker-image aura-app-secure:latest
kind load docker-image aura-app-vulnerable:latest

# minikube
minikube image load aura-app-secure:latest
minikube image load aura-app-vulnerable:latest
```

## 1. Generate the database init ConfigMaps

Both `mysql-secure` and `mysql-vulnerable` need their schema/migration SQL
files mounted at `/docker-entrypoint-initdb.d/`, executed once against an
empty volume — exactly like `docker-compose.yml`'s mounts. These ConfigMaps
are **not** committed as static YAML (that would duplicate `database/*.sql`
and go stale the moment a new sprint adds a migration), so generate them
directly from source before the first deploy:

MySQL's entrypoint runs `*.sql` files in alphabetical filename order, and `-`
sorts before `.` in ASCII — a bare `--from-file=database/init-secure.sql`
would keep the source filename as the key, and every `-sprintNN` file would
alphabetically sort *before* the base schema file that creates `users`. Use
`--from-file=<key>=<path>` to force the same numeric-prefixed order
`docker-compose.yml` already relies on:

```bash
kubectl create namespace aura-secure
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
  --from-file=28-sprint28.sql=database/init-secure-sprint28.sql \
  --from-file=30-sprint30.sql=database/init-secure-sprint30.sql \
  --from-file=34-sprint34-admin.sql=database/init-secure-sprint34-admin.sql \
  --from-file=34b-sprint34-widgets.sql=database/init-secure-sprint34-widgets.sql \
  --from-file=49-sprint49-loan-soft-delete.sql=database/init-secure-sprint49-loan-soft-delete.sql \
  --from-file=51-sprint51-recurring-loan-link.sql=database/init-secure-sprint51-recurring-loan-link.sql \
  --from-file=51b-sprint51-payment-type.sql=database/init-secure-sprint51-payment-type.sql \
  --from-file=52-sprint52-password-reset.sql=database/init-secure-sprint52-password-reset.sql \
  --from-file=52b-sprint52-2fa.sql=database/init-secure-sprint52-2fa.sql \
  --from-file=53-sprint53-accounts-order.sql=database/init-secure-sprint53-accounts-order.sql \
  --from-file=53b-sprint53-stat-card-order.sql=database/init-secure-sprint53-stat-card-order.sql \
  --from-file=57-sprint57-scheduler-jobs.sql=database/init-secure-sprint57-scheduler-jobs.sql \
  --from-file=57b-sprint57-impersonation.sql=database/init-secure-sprint57-impersonation.sql \
  --from-file=57c-sprint57-savings-interest.sql=database/init-secure-sprint57-savings-interest.sql

kubectl create namespace aura-vulnerable
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
  --from-file=28-sprint28.sql=database/init-vulnerable-sprint28.sql \
  --from-file=42-sprint42.sql=database/init-vulnerable-sprint42.sql \
  --from-file=43-sprint43.sql=database/init-vulnerable-sprint43.sql \
  --from-file=43b-sprint43-notify.sql=database/init-vulnerable-sprint43-notify.sql \
  --from-file=44-sprint44.sql=database/init-vulnerable-sprint44.sql \
  --from-file=49-sprint49-loan-soft-delete.sql=database/init-vulnerable-sprint49-loan-soft-delete.sql \
  --from-file=51-sprint51-recurring-loan-link.sql=database/init-vulnerable-sprint51-recurring-loan-link.sql \
  --from-file=51b-sprint51-payment-type.sql=database/init-vulnerable-sprint51-payment-type.sql \
  --from-file=52-sprint52-password-reset.sql=database/init-vulnerable-sprint52-password-reset.sql \
  --from-file=52b-sprint52-2fa.sql=database/init-vulnerable-sprint52-2fa.sql \
  --from-file=53-sprint53-accounts-order.sql=database/init-vulnerable-sprint53-accounts-order.sql \
  --from-file=53b-sprint53-stat-card-order.sql=database/init-vulnerable-sprint53-stat-card-order.sql \
  --from-file=57-sprint57-savings-interest.sql=database/init-vulnerable-sprint57-savings-interest.sql
```

(Sprint 26 added `ai_pending_actions` — `secure-version/` only, no vulnerable equivalent; nothing to add to the vulnerable ConfigMap for that sprint. Sprint 24 shipped no schema changes for either version. Sprints 29, 31, 32 shipped no schema changes for either version. Sprint 30 added a `secure-version/`-only `CHECK` constraint update — vulnerable's schema doesn't enforce it, so no vulnerable file exists for Sprint 30. Sprint 34's `is_admin` column (ad-hoc, not originally scoped for Release 8 — added alongside the admin panel work) is also `secure-version/`-only; vulnerable's `/admin` route stays intentionally ungated per VULN-002, no flag needed. Sprint 34's widget-types `CHECK` constraint update (`34b-sprint34-widgets.sql`) is likewise `secure-version/`-only — same reason as Sprint 30's: vulnerable's `dashboard_widgets.widget_type` is deliberately unconstrained free-text, no enum to update. Sprint 42's `scoreboard_progress` table (Release 9's hidden challenge page) is `vulnerable-version/`-only by design — no secure-version equivalent, same as every Release 9 sprint. Sprint 43's `flag_value` column + `ctf_settings` table, same reason. Sprint 43's `notified_at` follow-up hotfix (43b), same reason. Sprint 44's `ctf_vault` table, same reason.)

(`init-vulnerable-sprint6-backup.sql` is intentionally excluded — it's not
mounted in `docker-compose.yml` either.)

MySQL only runs these on a **fresh, empty** PVC. If you're re-deploying
against an existing volume, this step has no effect — same caveat as
`docker-compose`'s `docker-entrypoint-initdb.d`.

## 2a. Deploy with raw manifests

```bash
kubectl apply -f k8s/base/secure/
kubectl apply -f k8s/base/vulnerable/
kubectl apply -f k8s/base/monitoring/
```

## 2b. Deploy with Helm (alternative to 2a)

```bash
helm install aura ./k8s/helm/aura
# or, to deploy only part of the stack:
helm install aura ./k8s/helm/aura --set vulnerable.enabled=false
```

Override any `values.yaml` field with `--set` or `-f my-values.yaml` — see
`k8s/helm/aura/values.yaml` for everything that's parameterized (image tags,
replica counts, resource limits, credentials, Grafana admin password).

## 2c. TLS certificate for aura-secure.local (ENH-14, Sprint 57)

`k8s/base/secure/03-ingress.yaml` terminates TLS for `aura-secure.local`
using a Secret named `aura-secure-tls` in the `aura-secure` namespace. This
Secret isn't created by `kubectl apply` — generate it once per cluster
before app-secure's ingress can serve valid HTTPS:

```bash
# 1. Install mkcert (a local certificate authority for private hostnames —
#    no public CA can issue a cert for aura-secure.local, so a real CA
#    doesn't apply here; this is the standard fix, not a workaround).
sudo apt install libnss3-tools
curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/amd64"
chmod +x mkcert-v*-linux-amd64
sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert

# 2. Create and trust the local root CA on THIS machine (installs into the
#    OS trust store and Firefox/Chrome's NSS store via libnss3-tools).
mkcert -install

# 3. Generate the leaf cert for aura-secure.local.
mkdir -p /tmp/aura-certs && cd /tmp/aura-certs
mkcert aura-secure.local

# 4. Create/update the k8s Secret from it.
kubectl create secret tls aura-secure-tls -n aura-secure \
  --cert=aura-secure.local.pem --key=aura-secure.local-key.pem \
  --dry-run=client -o yaml | kubectl apply -f -
```

Re-run this whenever the cert expires (mkcert leaf certs are valid ~2 years)
or the Secret is ever deleted. The root CA itself (`mkcert -install`) only
needs to be created/trusted once per machine.

### Trusting the cert on other LAN devices

The browser only stops warning on a device that trusts the mkcert root CA.
`mkcert -install` above only did that for this machine. To reach
`https://aura-secure.local` warning-free from another device on the LAN
(phone, laptop, etc.), copy that same root CA to it and install it into
that device's trust store — do **not** run `mkcert -install` again on the
other device, that generates a *different* root CA that this cluster's
cert wasn't signed by.

Find the root CA file:

```bash
mkcert -CAROOT
# prints a directory; the file you need is rootCA.pem inside it
```

Copy `rootCA.pem` to the other device (scp/AirDrop/USB/email to yourself),
then install it there:

- **Android**: Settings → Security → Encryption & credentials → Install a
  certificate → CA certificate → pick `rootCA.pem`.
- **iOS**: AirDrop/email the file to the device, open it (installs a
  configuration profile), then Settings → General → VPN & Device Management
  → install the profile, then Settings → General → About → Certificate
  Trust Settings → enable full trust for it.
- **Windows**: rename to `rootCA.crt`, double-click → Install Certificate →
  Local Machine → place in "Trusted Root Certification Authorities".
- **macOS**: double-click `rootCA.pem` → Keychain Access → System keychain
  → double-click the entry → Trust → "Always Trust".
- **Another Linux machine**: `sudo cp rootCA.pem
  /usr/local/share/ca-certificates/mkcert-aura.crt && sudo
  update-ca-certificates`, then also import it into Firefox/Chrome's NSS
  store with `certutil` if the browser doesn't read the system store.

Each device also still needs `aura-secure.local` resolving to this
machine's LAN IP (a `/etc/hosts` entry, or LAN DNS) — the same requirement
the port-forward setup already had at `:5443`, unchanged by this move to
the default port.

## 3. Access everything

```bash
kubectl port-forward -n aura-secure svc/app-secure 5050:80
kubectl port-forward -n aura-vulnerable svc/app-vulnerable 5051:80
kubectl port-forward -n aura-monitoring svc/prometheus 9090:9090
kubectl port-forward -n aura-monitoring svc/grafana 3000:3000
```

(5050/5051 rather than 5000/5001 for the local side, so these don't collide
with docker-compose's host ports 5000/5001 if that stack is also running.)

Grafana: http://localhost:3000 — the "Aura — Application Overview" dashboard
is auto-provisioned (folder: Aura). Login `admin` / `admin` by default (raw
manifests) — change it, or set `monitoring.grafana.adminPassword` via Helm.

## What's isolated from what

- **Namespaces**: `aura-secure`, `aura-vulnerable`, `aura-monitoring` — fully
  separate. Nothing in `aura-vulnerable` can reach a Secret/ConfigMap in
  `aura-secure` or vice versa.
- **Databases**: separate PVCs, separate Secrets, separate credentials —
  `mysql-secure-data` and `mysql-vulnerable-data` never share a volume.
- **Monitoring**: Prometheus needs a `ClusterRole` (read-only: get/list/watch
  on pods/services/endpoints, plus `/metrics` on non-resource URLs) to
  discover pods across all three namespaces — see `01-rbac.yaml`. No app or
  database resource grants monitoring any write access.

## Health checks & metrics (both app versions)

- `GET /health` — checks DB connectivity (`SELECT 1`), returns `200` with
  `{"status": "ok", ...}` or `503` with `{"status": "degraded", ...}`. Used by
  both the liveness and readiness probes.
- `GET /metrics` — Prometheus text format (`prometheus-flask-exporter`),
  request count + latency histograms. Unauthenticated by design (the normal
  Prometheus-scraping pattern) — access is restricted at the network layer,
  not the app layer: only Prometheus in `aura-monitoring` is configured to
  scrape it, and nothing prevents a NetworkPolicy from locking this down
  further in a real cluster (not added here — out of scope for this sprint).
- Container logs are structured JSON on stdout (`logging_config.py` in each
  app), ready for a cluster-level aggregator (Loki, EFK, CloudWatch) to parse.

## Cleanup

```bash
# raw manifests
kubectl delete namespace aura-secure aura-vulnerable aura-monitoring

# Helm
helm uninstall aura
kubectl delete namespace aura-secure aura-vulnerable aura-monitoring  # PVCs/namespaces aren't removed by helm uninstall
```

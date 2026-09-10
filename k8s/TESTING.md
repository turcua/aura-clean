# Sprint 16 — Step-by-Step Test Guide

A copy-paste walkthrough to stand up the Kubernetes deployment from Sprint 16
and verify every piece actually works: both apps, both databases, health
checks, metrics, and the Prometheus/Grafana stack. See `k8s/README.md` for
the shorter reference version and architectural notes — this file is the
"run it and confirm it works" version, with expected output at each step.

Estimated time: 20-30 minutes for a full run-through.

---

## 0. Prerequisites

You need, on your machine:
- Docker
- `kubectl`
- A local Kubernetes cluster tool: **kind** (used below), or minikube, or
  Docker Desktop's built-in Kubernetes (any works — only the "load the image
  into the cluster" step differs, noted inline)
- `helm` (only if you're testing the Helm-chart path in step 4b)

Check what you have:

```bash
docker version
kubectl version --client
kind version        # or: minikube version
helm version         # optional
```

If you don't have a cluster tool yet, kind is the fastest to set up:

```bash
# macOS
brew install kind
# Linux — see https://kind.sigs.k8s.io/docs/user/quick-start/#installation
```

---

## 1. Create a local cluster

```bash
kind create cluster --name aura
kubectl cluster-info --context kind-aura
```

Expected: a `Kubernetes control plane is running at ...` message, no errors.

(minikube users: `minikube start` instead, and use `minikube image load` in
place of `kind load docker-image` throughout this guide. Docker Desktop
users: skip cluster creation, and skip the image-loading step entirely —
locally-built images are already visible to it.)

---

## 2. Build and load the app images

From the repo root:

```bash
docker build -t aura-app-secure:latest ./secure-version
docker build -t aura-app-vulnerable:latest ./vulnerable-version
```

(If you instead build via `docker compose build`, it produces the same
`aura-app-secure:latest` / `aura-app-vulnerable:latest` tags — no need to
run the two commands above separately in that case.)

Expected: both builds finish with `Successfully tagged aura-app-secure:latest`
and `Successfully tagged aura-app-vulnerable:latest` (or the Buildkit equivalent
`naming to docker.io/library/aura-app-...` line).

Load them into the kind cluster:

```bash
kind load docker-image aura-app-secure:latest --name aura
kind load docker-image aura-app-vulnerable:latest --name aura
```

Expected: `Image: "aura-app-secure:latest" with ID "sha256:..." not yet present
on node ... loading...` followed by no errors.

---

## 3. Generate the database init ConfigMaps

MySQL only runs `/docker-entrypoint-initdb.d/*.sql` once, against a fresh
empty volume — same as `docker-compose.yml`'s mounts. These ConfigMaps are
generated directly from `database/*.sql`, not committed as static YAML:

MySQL's entrypoint runs `*.sql` files in alphabetical filename order, and `-`
sorts before `.` in ASCII — so a bare `--from-file=database/init-secure.sql`
would let the key keep its source filename, and every `-sprintNN` file would
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
  --from-file=21-sprint21.sql=database/init-secure-sprint21.sql

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
  --from-file=21-sprint21.sql=database/init-vulnerable-sprint21.sql
```

Verify both ConfigMaps landed with all their keys:

```bash
kubectl get configmap mysql-secure-init -n aura-secure -o jsonpath='{.data}' | python3 -m json.tool | grep '\.sql'
kubectl get configmap mysql-vulnerable-init -n aura-vulnerable -o jsonpath='{.data}' | python3 -m json.tool | grep '\.sql'
```

Expected: 13 keys for secure, 12 for vulnerable.

---

## 4a. Deploy with raw manifests

```bash
kubectl apply -f k8s/base/secure/
kubectl apply -f k8s/base/vulnerable/
kubectl apply -f k8s/base/monitoring/
```

Expected: a stream of `namespace/... created`, `secret/... created`,
`persistentvolumeclaim/... created`, `deployment.apps/... created`,
`service/... created`, `horizontalpodautoscaler.autoscaling/... created`
lines, no errors. (`namespace/aura-secure unchanged` / `aura-vulnerable
unchanged` is expected since you already created them in step 3.)

**Skip step 4b if you did this.**

## 4b. Deploy with Helm (alternative to 4a)

```bash
helm install aura ./k8s/helm/aura
```

Expected: a `NOTES.txt`-driven summary printing port-forward commands for
whichever sections are enabled.

---

## 5. Wait for everything to come up

```bash
kubectl get pods -n aura-secure -w
```

Expected, after 1-2 minutes: `mysql-secure-xxx` → `Running` (1/1) first, then
`app-secure-xxx` pods (×2) → `Running` (1/1) once their `wait-for-mysql`
initContainer finishes. Ctrl-C once both are `Running`.

Repeat for the other two namespaces:

```bash
kubectl get pods -n aura-vulnerable
kubectl get pods -n aura-monitoring
```

Expected in `aura-monitoring`: `prometheus-xxx`, `grafana-xxx`,
`mysql-exporter-secure-xxx`, `mysql-exporter-vulnerable-xxx`, all `Running`.

If any pod is stuck in `Init:0/1` for more than ~2 minutes, MySQL likely
isn't answering pings yet — check `kubectl logs -n aura-secure
deploy/mysql-secure`. If a pod is `CrashLoopBackOff`, jump to
**Troubleshooting** at the bottom.

---

## 6. Test app-secure end-to-end

```bash
kubectl port-forward -n aura-secure svc/app-secure 5050:80
```

(Using 5050 rather than 5000 for the local side of the forward so this
doesn't collide with docker-compose, which already binds host port 5000 to
its own `app-secure` container — see `docker-compose.yml`. The k8s Service
itself listens on port 80 internally either way; only the local-machine side
of `port-forward` is arbitrary.)

In a second terminal (or browser):

```bash
curl -s http://localhost:5050/health | python3 -m json.tool
```

Expected:
```json
{
    "status": "ok",
    "checks": { "database": "ok" }
}
```

```bash
curl -s http://localhost:5050/metrics | head -20
```

Expected: Prometheus text-format output starting with `# HELP` / `# TYPE`
lines (e.g. `flask_http_request_total`).

Then open **http://localhost:5050** in a browser: register a test account,
log in, add a transaction — confirms the app is actually functional, not
just that `/health` returns 200. Also confirm in DevTools → Network that
responses carry the new headers: `X-Frame-Options: DENY`,
`Content-Security-Policy: ...frame-ancestors 'none'`, `Referrer-Policy`,
`Permissions-Policy` (these were the security-audit fix from this session —
worth confirming they made it into the image you just built).

---

## 7. Test app-vulnerable end-to-end

```bash
kubectl port-forward -n aura-vulnerable svc/app-vulnerable 5051:80
```

(Same reasoning as the secure app above — 5051 avoids colliding with
docker-compose's host port 5001.)

```bash
curl -s http://localhost:5051/health | python3 -m json.tool
```

Expected: same `{"status": "ok", ...}` shape. Open
**http://localhost:5051** and confirm login/register work the same way.

---

## 8. Test the monitoring stack

```bash
kubectl port-forward -n aura-monitoring svc/prometheus 9090:9090
```

Open **http://localhost:9090/targets**. Expected: targets for
`app-secure` (×2 pods), `app-vulnerable` (×2 pods),
`mysql-exporter-secure`, `mysql-exporter-vulnerable` — all state `UP`.

If targets are missing entirely, check the ClusterRoleBinding took effect:
```bash
kubectl auth can-i list pods --as=system:serviceaccount:aura-monitoring:prometheus --all-namespaces
```
Expected: `yes`.

```bash
kubectl port-forward -n aura-monitoring svc/grafana 3000:3000
```

Open **http://localhost:3000**, log in `admin` / `admin` (or whatever you
set via `monitoring.grafana.adminPassword` if using Helm). Go to
**Dashboards → Aura → Aura — Application Overview**. Expected: 6 panels
(request rate, 5xx rate, p95 latency, MySQL up, MySQL connections, pod
count), each split secure vs. vulnerable. Panels will be flat/empty until
you generate some traffic — refresh a few pages on both apps (steps 6-7),
wait ~30s, and the request-rate/latency panels should start showing data.

---

## 9. (Optional) Test the HPA

```bash
kubectl get hpa -n aura-secure -w
```

To actually trigger a scale-up you need sustained load — a quick way:

```bash
kubectl run load-generator -n aura-secure --image=busybox --restart=Never -- \
  /bin/sh -c "while true; do wget -q -O- http://app-secure/health; done"
```

Watch the HPA's `TARGETS` column climb and `REPLICAS` increase from 2
towards 6 over the next few minutes. Clean up afterward:

```bash
kubectl delete pod load-generator -n aura-secure
```

---

## Troubleshooting

- **`ImagePullBackOff`**: the image wasn't loaded into the cluster (step 2)
  — re-run the `kind load docker-image` commands, or confirm
  `imagePullPolicy: IfNotPresent` is set (it is, by default in these
  manifests) so it doesn't try to pull from a registry.
- **`mysql-secure` pod `CrashLoopBackOff`**: check `kubectl logs -n
  aura-secure deploy/mysql-secure` — most common cause is the PVC retaining
  data from a previous failed run with different credentials. Fix:
  `kubectl delete pvc mysql-secure-data -n aura-secure` and re-apply (this
  wipes that namespace's DB — fine for a test cluster).
- **App pod stuck in `Init:0/1` forever**: the `wait-for-mysql` initContainer
  is looping — check `kubectl logs -n aura-secure <pod> -c wait-for-mysql`;
  if it says "waiting for mysql-secure" indefinitely, MySQL itself is
  unhealthy (see previous point).
- **`/health` returns `{"status": "degraded", ...}`**: DB connectivity is
  failing from the app pod specifically (not MySQL itself) — check the
  ConfigMap's `DATABASE_HOST` matches the MySQL Service name exactly
  (`mysql-secure` / `mysql-vulnerable`), and that the Secret's
  `DATABASE_PASSWORD` matches the MySQL Secret's `MYSQL_PASSWORD`.
- **Prometheus shows no targets at all**: the ClusterRoleBinding didn't
  apply, or the ServiceAccount isn't attached — confirm
  `kubectl get pod -n aura-monitoring -o jsonpath='{.items[0].spec.serviceAccountName}'`
  (via `-l app=prometheus`) returns `prometheus`, not `default`.

---

## Cleanup

```bash
# raw manifests
kubectl delete namespace aura-secure aura-vulnerable aura-monitoring

# Helm
helm uninstall aura
kubectl delete namespace aura-secure aura-vulnerable aura-monitoring

# tear down the whole cluster
kind delete cluster --name aura
```

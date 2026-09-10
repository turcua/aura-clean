#!/usr/bin/env bash
# Creates systemd services that keep `kubectl port-forward --address 0.0.0.0`
# running persistently for the Aura k8s services, so app-secure, app-vulnerable,
# Prometheus, and Grafana stay reachable from any device on the LAN without a
# manual port-forward terminal open.
#
# Usage:
#   sudo ./k8s/setup-lan-portforward.sh [run-as-user]
#
# run-as-user defaults to $SUDO_USER (the user who invoked sudo), or $USER if
# not set. This should be whichever user has a working `kubectl` context for
# the minikube cluster (KUBECONFIG, etc).
#
# Requires: kubectl on PATH, systemd, root privileges (unit files live in
# /etc/systemd/system).

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run this script with sudo (systemd units go in /etc/systemd/system)." >&2
  exit 1
fi

RUN_USER="${1:-${SUDO_USER:-$USER}}"
KUBECTL_BIN="$(command -v kubectl || true)"

if [[ -z "$KUBECTL_BIN" ]]; then
  echo "kubectl not found in PATH" >&2
  exit 1
fi

# name -> "namespace service port-mapping"
#
# app-secure routes through the ingress-nginx controller (TLS termination for
# aura-secure.local) rather than straight to svc/app-secure, since
# FLASK_ENV=production requires HTTPS for the session/CSRF cookie to survive.
# See k8s/base/secure/03-ingress.yaml and k8s/README.md for the one-time
# `minikube addons enable ingress` + mkcert cert/secret setup this depends on.
#
# ENH-14 (Sprint 57): app-secure binds the default HTTPS port 443 (no
# trailing :5443 in the URL) instead of a high port, so it needs root — a
# regular user can't bind a privileged port. This is the one service in
# this script that runs as root; the other three stay on the unprivileged
# user for the least privilege that still works.
SERVICES=(
  "app-secure ingress-nginx svc/ingress-nginx-controller 443:443"
  "app-vulnerable aura-vulnerable svc/app-vulnerable 5051:80"
  "prometheus aura-monitoring svc/prometheus 9090:9090"
  "grafana aura-monitoring svc/grafana 3000:3000"
)

for entry in "${SERVICES[@]}"; do
  read -r name namespace svc ports <<< "$entry"
  unit_path="/etc/systemd/system/k8s-portforward-${name}.service"

  if [[ "$name" == "app-secure" ]]; then
    # Runs as root to bind port 443. KUBECONFIG is pointed at RUN_USER's
    # kubeconfig explicitly, since root's own $HOME/.kube/config won't
    # exist/won't have the right cluster context otherwise.
    user_directive="Environment=KUBECONFIG=/home/${RUN_USER}/.kube/config"
  else
    user_directive="User=${RUN_USER}"
  fi

  cat > "$unit_path" <<EOF
[Unit]
Description=kubectl port-forward for ${name} (${namespace})
After=network-online.target

[Service]
ExecStart=${KUBECTL_BIN} port-forward -n ${namespace} ${svc} --address 0.0.0.0 ${ports}
Restart=always
RestartSec=3
${user_directive}

[Install]
WantedBy=multi-user.target
EOF

  echo "Wrote ${unit_path}"
done

systemctl daemon-reload

for entry in "${SERVICES[@]}"; do
  read -r name _ <<< "$entry"
  # `enable --now` is a no-op start on a unit that's already active, so a
  # re-run of this script (e.g. picking up an ExecStart/port change) would
  # silently keep the OLD process running under the OLD unit file. `enable`
  # (persist across reboots) + `restart` (always re-exec, whether it was
  # already running or not) covers both a first run and a re-run correctly.
  systemctl enable "k8s-portforward-${name}"
  systemctl restart "k8s-portforward-${name}"
  echo "Enabled and (re)started k8s-portforward-${name}"
done

echo
echo "Done. Check status with: systemctl status k8s-portforward-<name>"
echo "Follow logs with:        journalctl -u k8s-portforward-<name> -f"
echo "Remove a service with:   sudo systemctl disable --now k8s-portforward-<name> && sudo rm /etc/systemd/system/k8s-portforward-<name>.service && sudo systemctl daemon-reload"

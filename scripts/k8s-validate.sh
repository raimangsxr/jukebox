#!/usr/bin/env bash
# Validate deploy/k8s manifests: server dry-run + bull file-set parity (SC-004, SC-005).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
K8S_DIR="${ROOT}/deploy/k8s"
BULL_DIR="${BULL_MANIFESTS_DIR:-${ROOT}/../argocd-apps/manifests/bull}"

CORE_MANIFESTS=(
  namespace.yaml
  configmap.yaml
  secret.yaml
  backend.yaml
  frontend.yaml
  migration-job.yaml
  ingress.yaml
)

echo "==> File-set parity vs bull (SC-005)"
if [[ ! -d "$BULL_DIR" ]]; then
  echo "error: bull reference not found: $BULL_DIR" >&2
  echo "Set BULL_MANIFESTS_DIR to argocd-apps/manifests/bull" >&2
  exit 1
fi

for file in "${CORE_MANIFESTS[@]}"; do
  if [[ ! -f "${K8S_DIR}/${file}" ]]; then
    echo "error: missing ${K8S_DIR}/${file}" >&2
    exit 1
  fi
  if [[ ! -f "${BULL_DIR}/${file}" ]]; then
    echo "error: bull reference missing ${BULL_DIR}/${file}" >&2
    exit 1
  fi
done
echo "OK: same seven core manifest files as bull"

validate_yaml_syntax() {
  local file="$1"
  python3 -c "
import yaml, sys
from pathlib import Path
path = Path(sys.argv[1])
list(yaml.safe_load_all(path.read_text()))
print(f'  OK yaml syntax: {path.name}')
" "$file"
}

echo "==> kubectl apply --dry-run (SC-004)"
if ! command -v kubectl >/dev/null 2>&1; then
  echo "warn: kubectl not found; validating YAML syntax only" >&2
  for file in "${CORE_MANIFESTS[@]}"; do
    validate_yaml_syntax "${K8S_DIR}/${file}"
  done
  echo "OK: YAML syntax valid (server dry-run skipped — no kubectl)"
  exit 0
fi

if kubectl cluster-info >/dev/null 2>&1; then
  for file in "${CORE_MANIFESTS[@]}"; do
    echo "  - ${file} (server)"
    kubectl apply --dry-run=server -f "${K8S_DIR}/${file}"
  done
  echo "OK: all core manifests passed server dry-run"
else
  echo "warn: cluster unreachable; validating YAML syntax only" >&2
  for file in "${CORE_MANIFESTS[@]}"; do
    validate_yaml_syntax "${K8S_DIR}/${file}"
  done
  echo "OK: YAML syntax valid (server dry-run deferred — run with cluster access)"
fi

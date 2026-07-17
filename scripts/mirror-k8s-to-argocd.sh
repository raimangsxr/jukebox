#!/usr/bin/env bash
# Mirror canonical K8s manifests to argocd-apps GitOps repo.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${ROOT}/deploy/k8s"
DEST="${ARGOCD_APPS_DIR:-${ROOT}/../argocd-apps}/manifests/jukebox"

if [[ ! -d "$SRC" ]]; then
  echo "error: source not found: $SRC" >&2
  exit 1
fi

mkdir -p "$DEST"
rsync -av --delete "$SRC/" "$DEST/" \
  --exclude argocd-application.yaml.example \
  --exclude README.md

echo "Mirrored $SRC -> $DEST"

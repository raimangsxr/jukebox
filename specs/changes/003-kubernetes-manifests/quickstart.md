# Quickstart: 003-kubernetes-manifests

Validation after implementation.

## Prerequisites

- `kubectl` configured for target cluster
- Images published: `rromani/jukebox-backend:0.1`, `rromani/jukebox-frontend:0.1` (or current release tag)
- PostgreSQL database `jukebox` reachable from cluster
- DNS `jukebox.rromani.eu` → Traefik (or port-forward for dev)

## Phase 1 — Prepare secrets

1. Copy `deploy/k8s/secret.yaml` and replace `REPLACE_ME` values **locally** (do not commit):
   - `JUKEBOX_DATABASE_URL`
   - `JUKEBOX_OPERATOR_USERNAME` / `JUKEBOX_OPERATOR_PASSWORD`
   - `JUKEBOX_SESSION_SECRET`
2. Or create Secret in cluster: `kubectl create secret generic jukebox-secrets -n jukebox --from-literal=...`

## Phase 2 — Apply base resources

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/secret.yaml   # after filling placeholders
```

## Phase 3 — Migrate

```bash
kubectl apply -f deploy/k8s/migration-job.yaml
kubectl wait --for=condition=complete job/jukebox-migrate -n jukebox --timeout=120s
kubectl logs job/jukebox-migrate -n jukebox
```

Verify schema (US2 — `api_tokens` from change 002):

```bash
# Option A: psql against external DB (use postgresql:// URL; strip +psycopg from SQLAlchemy URL if needed)
psql "postgresql://user:pass@host:5432/jukebox" -c "\dt api_tokens"

# Option B: in-cluster backend pod after Phase 4 (if backend exposes no direct DB check)
# Expect migration logs to show alembic reaching head without error
```

## Phase 4 — Workloads

```bash
kubectl apply -f deploy/k8s/backend.yaml
kubectl apply -f deploy/k8s/frontend.yaml
kubectl rollout status deployment/jukebox-backend -n jukebox
kubectl rollout status deployment/jukebox-frontend -n jukebox
```

## Phase 5 — Ingress

```bash
kubectl apply -f deploy/k8s/ingress.yaml
```

## Phase 6 — Smoke tests

```bash
# In-cluster health
kubectl run curl --rm -it --image=curlimages/curl -- \
  curl -s http://jukebox-backend.jukebox.svc.cluster.local:8000/api/health

# Public health + SPA
curl -s https://jukebox.rromani.eu/api/health
curl -I https://jukebox.rromani.eu/

# US4 — CSP frame-ancestors (must reflect JUKEBOX_FRAME_ANCESTORS in ConfigMap)
curl -sI https://jukebox.rromani.eu/api/health | grep -i content-security-policy
# Expect frame-ancestors to include https://kiosk.rromani.eu
```

Login test: open `https://jukebox.rromani.eu/login` with operator credentials.

## Phase 7 — Mirror to ArgoCD (GitOps)

```bash
# From amrn-jukebox repo root (adjust path to argocd-apps)
./scripts/mirror-k8s-to-argocd.sh
# or manually:
rsync -av --delete deploy/k8s/ ../argocd-apps/manifests/jukebox/ \
  --exclude argocd-application.yaml.example

# Register Application (see deploy/k8s/argocd-application.yaml.example)
```

## Phase 8 — Dry-run and bull parity (SC-004, SC-005)

```bash
./scripts/k8s-validate.sh
```

The script applies server dry-run to core manifests only (excludes `argocd-application.yaml.example`) and verifies the same seven YAML resource files exist as in `argocd-apps/manifests/bull/`.

## Release bump checklist

On each GitHub Release `X.Y`:

1. CI pushes `rromani/jukebox-*:X.Y`
2. Update image tags in `backend.yaml`, `frontend.yaml`, `migration-job.yaml`
3. Mirror to argocd-apps; ArgoCD sync
4. Re-run migration Job before or with rollout (if schema changed)

# Kubernetes deployment — amrn-jukebox

Canonical manifests for production. Mirror to `argocd-apps/manifests/jukebox/` for GitOps.

## Files

| File | Resource |
|------|----------|
| `namespace.yaml` | Namespace `jukebox` (Pod Security restricted) |
| `configmap.yaml` | `jukebox-config` |
| `secret.yaml` | `jukebox-secrets` (placeholders only — do not commit real values) |
| `migration-job.yaml` | Job `jukebox-migrate` |
| `backend.yaml` | Service + Deployment `jukebox-backend` |
| `frontend.yaml` | Service + Deployment `jukebox-frontend` |
| `ingress.yaml` | Ingress `jukebox-ingress` |
| `argocd-application.yaml.example` | Example ArgoCD Application (not applied to cluster) |

## Environment variables

### ConfigMap `jukebox-config`

| Key | Production value |
|-----|------------------|
| `JUKEBOX_CORS_ALLOW_ORIGINS` | `https://jukebox.rromani.eu,https://kiosk.rromani.eu` |
| `JUKEBOX_COOKIE_SECURE` | `"true"` |
| `JUKEBOX_FRAME_ANCESTORS` | `https://kiosk.rromani.eu` |
| `JUKEBOX_GOOGLE_REDIRECT_URI` | `https://jukebox.rromani.eu/api/auth/google/callback` |
| `JUKEBOX_PARTICIPANT_OAUTH_RETURN_URL` | `https://jukebox.rromani.eu/participar` |

### Secret `jukebox-secrets`

| Key | Notes |
|-----|-------|
| `JUKEBOX_DATABASE_URL` | External PostgreSQL |
| `JUKEBOX_OPERATOR_USERNAME` | Operator login |
| `JUKEBOX_OPERATOR_PASSWORD` | ≥12 characters |
| `JUKEBOX_SESSION_SECRET` | Random hex string |
| `JUKEBOX_GOOGLE_CLIENT_ID` | Google Cloud OAuth Web client id |
| `JUKEBOX_GOOGLE_CLIENT_SECRET` | Google Cloud OAuth client secret |

Replace `REPLACE_ME` in `secret.yaml` locally before apply, or create the Secret in-cluster with `kubectl create secret generic`.

## Deploy order

1. `namespace.yaml`, `configmap.yaml`, `secret.yaml`
2. `migration-job.yaml` — wait until Job `jukebox-migrate` is `Complete`
3. `backend.yaml`, `frontend.yaml`
4. `ingress.yaml`
5. Smoke: `/api/health`, login, CSP header

Full validation steps: `specs/changes/003-kubernetes-manifests/quickstart.md`

## Images

- `rromani/jukebox-backend:0.1`
- `rromani/jukebox-frontend:0.1`

On each GitHub Release `X.Y`, update tags in `backend.yaml`, `frontend.yaml`, and `migration-job.yaml`.

## Validation

```bash
./scripts/k8s-validate.sh
```

Runs server dry-run on core manifests and verifies file-set parity with `argocd-apps/manifests/bull/`.

## GitOps mirror

```bash
./scripts/mirror-k8s-to-argocd.sh
```

Copies manifests to `../argocd-apps/manifests/jukebox/` (excludes this README and `argocd-application.yaml.example`).

Register the Application using `argocd-application.yaml.example` as reference (`path: manifests/jukebox` in `argocd-apps` repo).

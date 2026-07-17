# Contract Deltas: 003-kubernetes-manifests

**Status**: merged — consolidated into `specs/contracts/ops-platform/contract.md` (2026-07-17)

## deploy/k8s/ (new)

Seven manifests + README (canonical source in monorepo):

| File | Purpose |
|------|---------|
| `namespace.yaml` | Namespace `jukebox` + Pod Security labels |
| `configmap.yaml` | `JUKEBOX_CORS_ALLOW_ORIGINS`, `JUKEBOX_COOKIE_SECURE`, `JUKEBOX_FRAME_ANCESTORS` |
| `secret.yaml` | Template `jukebox-secrets` (placeholders) |
| `backend.yaml` | Service + Deployment, probes `/api/health` |
| `frontend.yaml` | Service + Deployment, probes `/health` |
| `migration-job.yaml` | Alembic `upgrade head` |
| `ingress.yaml` | `jukebox.rromani.eu`, `/api` + `/` |
| `README.md` | Env table, deploy order, mirror instructions |
| `argocd-application.yaml.example` | ArgoCD Application for `argocd-apps` |

## Image tags

- `rromani/jukebox-backend:<release>` and `rromani/jukebox-frontend:<release>`
- Initial manifest tag: `0.1` (bump on each GitHub Release)

## Production ConfigMap defaults

| Key | Prod value |
|-----|------------|
| `JUKEBOX_COOKIE_SECURE` | `"true"` |
| `JUKEBOX_CORS_ALLOW_ORIGINS` | `https://kiosk.rromani.eu` |
| `JUKEBOX_FRAME_ANCESTORS` | `https://kiosk.rromani.eu` |

## GitOps mirror

- Canonical: `amrn-jukebox/deploy/k8s/`
- Mirror target: `argocd-apps/manifests/jukebox/`
- ArgoCD Application path: `manifests/jukebox` (repo `argocd-apps`)

## Deploy order

1. Namespace, ConfigMap, Secret
2. Migration Job → wait Complete
3. Backend + Frontend Deployments
4. Ingress
5. Smoke: `/api/health`, login, kiosk CORS/CSP

## Deferred section removal

Remove from ops-platform **Deferred**:

- `deploy/k8s/` manifests
- ArgoCD app manifests (example ships; live app in argocd-apps)

## Validation

- `scripts/k8s-validate.sh` — `kubectl apply --dry-run=server` on core manifests (exclude `argocd-application.yaml.example`) + file-set parity vs bull (SC-005)
- Manual quickstart: migration schema (`api_tokens`), CSP header, login (no cluster in CI v1)

## Change history entry

- **003-kubernetes-manifests** — `deploy/k8s/`, GitOps mirror, production env contract

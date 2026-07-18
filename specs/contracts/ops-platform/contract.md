# ops-platform Contract

Status: active. Consolidated from changes **001-foundation-jukebox** and **003-kubernetes-manifests** (2026-07-17).

## Purpose

Local development, container images, CI release workflow, and Kubernetes deployment manifests for amrn-jukebox. Aligned with amrn-bull and amrn-escalabirras-dual.

## docker-compose.yml

Services:

| Service | Image | Port |
|---------|-------|------|
| `postgres` | postgres:16 | internal |
| `migrate` | jukebox-backend:local | one-shot `alembic upgrade head` |
| `backend` | jukebox-backend:local | 8000 |
| `frontend` | build target `dev` | 4200 |

Required `.env` keys: `JUKEBOX_DATABASE_PASSWORD`, `JUKEBOX_OPERATOR_PASSWORD`, `JUKEBOX_SESSION_SECRET`.

Backend services do **not** define Docker HEALTHCHECK (platform standard).

## Docker images

- `backend/Dockerfile` — multi-stage Python wheel build, uvicorn on 8000; `.dockerignore` present
- `frontend/Dockerfile` — targets: `dev`, `build`, `prod` (nginx on 8080); `.dockerignore` present

## Local validation

- `scripts/compose-smoke.sh` — builds postgres + migrate + backend, asserts `/api/health` and CSP header
- `specs/changes/001-foundation-jukebox/quickstart.md` — manual validation steps

## CI

`.github/workflows/release-images.yml` triggers on GitHub `release: created`:

1. `pytest backend/tests`
2. `npm --prefix frontend ci && npm --prefix frontend run test`
3. `npm --prefix frontend run build`
4. Build and push `jukebox-backend` and `jukebox-frontend` to Docker Hub as `rromani/jukebox-*:<release-tag>`

`.github/workflows/bump-app.yml` triggers on successful `Release Images` via `workflow_run`:

1. Downloads the `release-tag` artifact and patches `argocd-apps/manifests/jukebox/{backend,frontend,migration-job}.yaml`
2. Opens a PR in `raimangsxr/argocd-apps` labeled `jukebox`
3. Auto-merges minor and hotfix releases (same major version); leaves major bumps open for manual review

Requires repo secret `ARGOCD_APPS_TOKEN` (fine-grained PAT with `Contents: Read and write` on `argocd-apps`).

## Production routing

- Ingress sends `/api/*` → backend
- All other paths → frontend nginx (SPA fallback)

Migrations run via Kubernetes Job before backend rollout (not at backend startup).

## deploy/k8s/ (canonical source)

Seven core manifests + README in `deploy/k8s/`:

| File | Purpose |
|------|---------|
| `namespace.yaml` | Namespace `jukebox` + Pod Security `restricted` labels |
| `configmap.yaml` | `JUKEBOX_CORS_ALLOW_ORIGINS`, `JUKEBOX_COOKIE_SECURE`, `JUKEBOX_FRAME_ANCESTORS` |
| `secret.yaml` | Template `jukebox-secrets` (`REPLACE_ME` placeholders only) |
| `backend.yaml` | Service + Deployment, probes `/api/health` |
| `frontend.yaml` | Service + Deployment, probes `/health` |
| `migration-job.yaml` | Alembic `upgrade head` |
| `ingress.yaml` | `jukebox.rromani.eu`, `/api` + `/` |
| `README.md` | Env table, deploy order, mirror instructions |
| `argocd-application.yaml.example` | ArgoCD Application for `argocd-apps` repo |

### Image tags

- `rromani/jukebox-backend:<release>` and `rromani/jukebox-frontend:<release>`
- Initial manifest tag: `0.1` — bump in `backend.yaml`, `frontend.yaml`, and `migration-job.yaml` on each GitHub Release

### Production ConfigMap defaults

| Key | Prod value |
|-----|------------|
| `JUKEBOX_COOKIE_SECURE` | `"true"` |
| `JUKEBOX_CORS_ALLOW_ORIGINS` | `https://kiosk.rromani.eu` |
| `JUKEBOX_FRAME_ANCESTORS` | `https://kiosk.rromani.eu` |

### Secret keys (`jukebox-secrets`)

| Key | Notes |
|-----|-------|
| `JUKEBOX_DATABASE_URL` | External PostgreSQL (`postgresql+psycopg://...`) |
| `JUKEBOX_OPERATOR_USERNAME` | Bootstrap operator |
| `JUKEBOX_OPERATOR_PASSWORD` | ≥12 characters |
| `JUKEBOX_SESSION_SECRET` | Long random hex |

Git-tracked `secret.yaml` uses `REPLACE_ME` placeholders only. Operator applies real values out-of-band.

### Deploy order

1. Namespace, ConfigMap, Secret (operator fills Secret)
2. Migration Job → wait `Complete`
3. Backend + Frontend Deployments
4. Ingress
5. Smoke: `/api/health`, login, kiosk CORS/CSP

### GitOps mirror

- **Canonical**: `amrn-jukebox/deploy/k8s/`
- **Mirror target**: `argocd-apps/manifests/jukebox/`
- **ArgoCD Application path**: `manifests/jukebox` (repo `argocd-apps`)
- **Helper**: `scripts/mirror-k8s-to-argocd.sh`

Live ArgoCD Application lives in `argocd-apps/apps/jukebox/`; example ships as `deploy/k8s/argocd-application.yaml.example`.

### Validation

- `scripts/k8s-validate.sh` — server dry-run on core manifests + file-set parity vs bull
- Manual quickstart: `specs/changes/003-kubernetes-manifests/quickstart.md`

## Deferred

- Compose smoke in GitHub Actions (operator-run via `scripts/compose-smoke.sh` for now)
- SealedSecrets / External Secrets Operator
- HPA, PDB, advanced network policies

## Change history

- **001-foundation-jukebox** — compose, Dockerfiles, nginx, release workflow, compose smoke script
- **003-kubernetes-manifests** — `deploy/k8s/`, GitOps mirror, production env contract

# Context Pack: 003-kubernetes-manifests

## Read first

1. `specs/manifest.yml` — active change
2. `specs/contracts/ops-platform/contract.md` — compose, CI, deferred k8s
3. `specs/changes/003-kubernetes-manifests/spec.md`
4. Reference: `/Users/rromanit/workspace/argocd-apps/manifests/bull/`

## Repo artifacts (existing)

- `docker-compose.yml` — env vars `JUKEBOX_*`
- `backend/Dockerfile`, `frontend/Dockerfile` (prod nginx :8080)
- `.github/workflows/release-images.yml` — `rromani/jukebox-backend`, `rromani/jukebox-frontend`

## Bull → Jukebox parity map

| Bull (`argocd-apps/manifests/bull`) | Jukebox (canonical → mirror) |
|-------------------------------------|------------------------------|
| 7 YAML files | `deploy/k8s/*.yaml` → `argocd-apps/manifests/jukebox/` |

## Env prefix

`BULL_*` → `JUKEBOX_*` (no `MAX_RECENT_LIMIT` — jukebox-specific config only).

## Clarifications applied

- Canonical: `deploy/k8s/` in monorepo
- Image tag: fixed per release (`0.1` initial)
- `JUKEBOX_COOKIE_SECURE: "true"` in prod ConfigMap

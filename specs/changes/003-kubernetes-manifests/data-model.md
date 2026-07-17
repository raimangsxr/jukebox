# Platform Resource Model: 003-kubernetes-manifests

Kubernetes objects and runtime configuration (not application DB schema).

## Namespace

| Name | Labels |
|------|--------|
| `jukebox` | Pod Security `restricted` (enforce/warn/audit) |

## Workloads

| Kind | Name | Image | Ports |
|------|------|-------|-------|
| Deployment | `jukebox-backend` | `rromani/jukebox-backend:<version>` | 8000 |
| Deployment | `jukebox-frontend` | `rromani/jukebox-frontend:<version>` | 8080 |
| Job | `jukebox-migrate` | `rromani/jukebox-backend:<version>` | — |

## Services

| Name | Selector | Port → target |
|------|----------|---------------|
| `jukebox-backend` | `jukebox-backend` | 8000 → 8000 |
| `jukebox-frontend` | `jukebox-frontend` | 80 → 8080 |

## ConfigMap `jukebox-config`

| Key | Example prod value | Source |
|-----|------------------|--------|
| `JUKEBOX_CORS_ALLOW_ORIGINS` | `https://kiosk.rromani.eu` | clarify + assumptions |
| `JUKEBOX_COOKIE_SECURE` | `"true"` | clarify |
| `JUKEBOX_FRAME_ANCESTORS` | `https://kiosk.rromani.eu` | kiosk iframe |

## Secret `jukebox-secrets`

| Key | Notes |
|-----|-------|
| `JUKEBOX_DATABASE_URL` | `postgresql+psycopg://...` external DB |
| `JUKEBOX_OPERATOR_USERNAME` | bootstrap operator |
| `JUKEBOX_OPERATOR_PASSWORD` | ≥12 chars |
| `JUKEBOX_SESSION_SECRET` | long random hex |

Git-tracked `secret.yaml` uses `REPLACE_ME` placeholders only.

## Ingress `jukebox-ingress`

| Field | Value |
|-------|-------|
| host | `jukebox.rromani.eu` |
| class | `my-traefik` |
| `/api` Prefix | `jukebox-backend:8000` |
| `/` Prefix | `jukebox-frontend:80` |

## Probes

| Workload | Readiness / Liveness |
|----------|---------------------|
| backend | `GET /api/health` |
| frontend | `GET /health` |

## Security context (from bull pattern)

- `runAsNonRoot: true`
- backend UID/GID 10001; frontend 101
- `readOnlyRootFilesystem: true` + `emptyDir` `/tmp`
- `allowPrivilegeEscalation: false`, drop ALL caps

## Lifecycle

```text
apply namespace/config/secret
  → run migration Job (Complete)
  → rollout backend + frontend
  → apply ingress
  → verify public URL
```

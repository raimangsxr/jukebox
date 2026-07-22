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
| `JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT` | `"2"` (max `pending_review` per participant) |

### Secret `jukebox-secrets`

| Key | Notes |
|-----|-------|
| `JUKEBOX_DATABASE_URL` | External PostgreSQL |
| `JUKEBOX_OPERATOR_USERNAME` | Operator login |
| `JUKEBOX_OPERATOR_PASSWORD` | ≥12 characters |
| `JUKEBOX_SESSION_SECRET` | Random hex string |
| `JUKEBOX_GOOGLE_CLIENT_ID` | Google Cloud OAuth Web client id |
| `JUKEBOX_GOOGLE_CLIENT_SECRET` | Google Cloud OAuth client secret |
| `JUKEBOX_YOUTUBE_API_KEYS` | Comma-separated YouTube Data API v3 keys (enables `/participar` search + song duration) |

Replace `REPLACE_ME` in `secret.yaml` locally before apply, or create the Secret in-cluster with `kubectl create secret generic`.

> **Never commit real secrets.** The repo `.env` is git-ignored (only `.env.example` is tracked). `secret.yaml` carries `REPLACE_ME` placeholders only.

### Rotating `JUKEBOX_SESSION_SECRET`

The session secret signs operator/participant cookies **and** the Google OAuth state token. Rotating it is required if the value may have been exposed, and is a one-time operation:

```bash
NEW=$(python3 -c "import secrets; print(secrets.token_hex(32))")
kubectl -n jukebox patch secret jukebox-secrets \
  --type merge -p "{\"stringData\":{\"JUKEBOX_SESSION_SECRET\":\"$NEW\"}}"
kubectl -n jukebox rollout restart deploy/jukebox-backend
```

**Effect**: all operator and participant sessions are invalidated (one-time re-login); in-flight Google OAuth flows must be restarted. The kiosk shows the existing "Sesión caducada" state and re-bootstraps from its embed token.

### Reissuing embed / API tokens

The API-token lookup uses an indexed non-secret prefix (010). **Tokens created before this change no longer validate.** After upgrading:

1. Operator signs in to `/admin` → **Tokens de iframe** → create a new token.
2. Update the kiosk embed URL `?token=<new-plaintext>` with the regenerated value.
3. Revoke the old tokens.

### YouTube search

1. Enable **YouTube Data API v3** in Google Cloud and create an API key.
2. Set `JUKEBOX_YOUTUBE_API_KEYS` in `jukebox-secrets` (comma-separated for quota failover).
3. Restart `jukebox-backend` after updating the secret.
4. Smoke: `GET /api/youtube/search/config` → `{"enabled":true}`.

## Scaling constraint (single replica)

`jukebox-backend` **must run with `replicas: 1`**. The following runtime state is per-process and not shared across pods:

- SSE subscriber fan-out (`/api/events/stream`)
- YouTube search rate limiting (per participant)
- YouTube API key round-robin rotation and in-memory exhaustion
- Per-key daily quota counters' in-memory broadcast bookkeeping

Running more than one replica would split this state and break realtime updates, rate limiting, and quota accounting. **Do not add an HPA** or raise `replicas` until the shared state is externalized (e.g. Redis) in a future change.

Outbound calls to YouTube/Google run inside synchronous FastAPI path operations, which execute in the framework threadpool — they do not block the async event loop, so a single replica stays responsive under concurrent searches.

## Deploy order

1. `namespace.yaml`, `configmap.yaml`, `secret.yaml`
2. `migration-job.yaml` — wait until Job `jukebox-migrate` is `Complete`
3. `backend.yaml`, `frontend.yaml`
4. `ingress.yaml`
5. Smoke: `/api/health`, login, CSP header, `GET /api/youtube/search/config`

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

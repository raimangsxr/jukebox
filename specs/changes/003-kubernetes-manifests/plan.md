# Implementation Plan: Kubernetes Deployment Manifests

**Branch**: `003-kubernetes-manifests` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/changes/003-kubernetes-manifests/spec.md`

## Summary

Ship production Kubernetes manifests under `deploy/k8s/` in amrn-jukebox, mirroring `argocd-apps/manifests/bull` structure with `JUKEBOX_*` env vars, Pod Security restricted hardening, fixed release image tags, and `JUKEBOX_COOKIE_SECURE=true`. Operator mirrors manifests to `argocd-apps/manifests/jukebox` for ArgoCD GitOps.

## Technical Context

**Language/Version**: Kubernetes 1.28+ manifests (YAML); cluster Traefik ingress class `my-traefik`

**Primary Dependencies**: Docker images `rromani/jukebox-backend`, `rromani/jukebox-frontend`; external PostgreSQL; ArgoCD (sibling repo)

**Storage**: PostgreSQL external (connection via `JUKEBOX_DATABASE_URL` Secret); no in-cluster DB

**Testing**: `scripts/k8s-validate.sh` (`kubectl apply --dry-run=server` + bull file-set parity); manual quickstart validation

**Target Platform**: Home/production cluster (same as bull); host `jukebox.rromani.eu`

**Project Type**: Ops / platform manifests in monorepo `deploy/k8s/`

**Performance Goals**: Single replica per workload (v1); readiness &lt; 3 min after image pull

**Constraints**: Pod Security `restricted`; non-root UIDs (backend 10001, frontend 101); readOnlyRootFilesystem; no secrets in git (placeholders only)

**Scale/Scope**: 7 core manifest files + README + ArgoCD example; mirror workflow to argocd-apps

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts | Pass | Update `ops-platform` via contract-deltas before implement |
| IV. Contract before code | Pass | T001 merge deltas into `specs/contracts/ops-platform/contract.md` |
| V. Tests for changed behavior | Pass | `kubectl dry-run` + manual quickstart (no cluster in CI v1) |
| VI. Sibling conventions | Pass | Mirror bull `deploy/k8s/` layout and argocd-apps GitOps |

**Post-design re-check**: All gates pass.

## Project Structure

### Documentation (this feature)

```text
specs/changes/003-kubernetes-manifests/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/contract-deltas.md
└── tasks.md          # (/speckit-tasks)
```

### Source (to implement)

```text
deploy/k8s/
├── namespace.yaml
├── configmap.yaml
├── secret.yaml              # placeholders only — REPLACE_ME
├── backend.yaml
├── frontend.yaml
├── migration-job.yaml
├── ingress.yaml
├── README.md
└── argocd-application.yaml.example

scripts/
└── mirror-k8s-to-argocd.sh   # optional helper: rsync deploy/k8s → ../argocd-apps/manifests/jukebox
```

**Structure Decision**: Canonical source in jukebox monorepo; `argocd-apps/manifests/jukebox` is deployment mirror (clarify 2026-07-17).

## Phase 0 — Research

See [research.md](./research.md). All clarifications resolved in session 2026-07-17.

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Resource inventory | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Deploy guide | [quickstart.md](./quickstart.md) |

### Bull → Jukebox mapping

| File | Key renames |
|------|-------------|
| All | `bull` → `jukebox` namespace/labels; `BULL_*` → `JUKEBOX_*` |
| `configmap.yaml` | `JUKEBOX_COOKIE_SECURE: "true"`; CORS `https://kiosk.rromani.eu`; drop `BULL_MAX_RECENT_LIMIT` |
| `secret.yaml` | Placeholders `REPLACE_ME` (no real credentials in git) |
| `ingress.yaml` | host `jukebox.rromani.eu`; same `/api` + `/` paths |
| Images | `rromani/jukebox-backend:0.1`, `rromani/jukebox-frontend:0.1` (update per release) |

### Deploy order (documented in README + quickstart)

1. Namespace, ConfigMap, Secret (operator fills real Secret out-of-band or in cluster)
2. `migration-job.yaml` — wait `Complete`
3. `backend.yaml`, `frontend.yaml`
4. `ingress.yaml`
5. Verify `/api/health`, `/health`, public URL

## Phase 2 — Implementation phases (for tasks)

### Phase A — Contract + scaffold

- Merge ops-platform contract deltas
- Create `deploy/k8s/` directory and README

### Phase B — Core manifests

- namespace, configmap, secret template, backend, frontend, migration-job, ingress

### Phase C — GitOps artifacts

- `argocd-application.yaml.example`
- Optional `scripts/mirror-k8s-to-argocd.sh`

### Phase D — Validation

- `scripts/k8s-validate.sh` — dry-run core manifests (exclude `argocd-application.yaml.example`) + SC-005 parity vs bull
- Manual quickstart checklist (api_tokens, CSP smoke)
- Update manifest status

## Risks

| Risk | Mitigation |
|------|------------|
| Secret committed with real creds | Placeholders + README warning; `.gitignore` not needed if only REPLACE_ME |
| Forgot migrate before backend | README + quickstart enforce Job-first order |
| Image tag drift vs release | Document bump tag in both YAML files on each GitHub Release |
| Mirror drift argocd-apps | mirror script or checklist step in quickstart |

## Complexity Tracking

> No violations.

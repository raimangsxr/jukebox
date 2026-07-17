---
description: "Task list for 003-kubernetes-manifests"
---

# Tasks: Kubernetes Deployment Manifests

**Input**: Design documents from `specs/changes/003-kubernetes-manifests/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/contract-deltas.md, quickstart.md

**Tests**: Manual validation via `kubectl apply --dry-run=server` and quickstart (SC-004); no cluster in CI v1.

**Organization**: Tasks grouped by user story for independent validation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US5)

## Phase 1: Setup (Contract Consolidation)

**Purpose**: Merge contract deltas before manifests (Constitution IV)

- [x] T001 Update `specs/contracts/ops-platform/contract.md` from `specs/changes/003-kubernetes-manifests/contracts/contract-deltas.md`
- [x] T002 Create `deploy/k8s/` directory and scaffold `deploy/k8s/README.md` (env table, deploy order, mirror instructions)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Namespace required by all resources

- [x] T003 Create `deploy/k8s/namespace.yaml` with Pod Security `restricted` labels (mirror `argocd-apps/manifests/bull/namespace.yaml`)

**Checkpoint**: Namespace manifest ready

---

## Phase 3: User Story 4 — Runtime JUKEBOX_* config (Priority: P2)

**Goal**: ConfigMap and Secret template supply env vars for backend auth and kiosk integration.

**Independent Test**: `kubectl apply --dry-run=server` on configmap + secret; keys match data-model.md.

### Implementation for User Story 4

- [x] T004 [P] [US4] Create `deploy/k8s/configmap.yaml` (`JUKEBOX_CORS_ALLOW_ORIGINS`, `JUKEBOX_COOKIE_SECURE: "true"`, `JUKEBOX_FRAME_ANCESTORS`)
- [x] T005 [P] [US4] Create `deploy/k8s/secret.yaml` template with `REPLACE_ME` placeholders for `JUKEBOX_DATABASE_URL`, operator creds, `JUKEBOX_SESSION_SECRET`

**Checkpoint**: Config resources defined; operator can substitute real Secret out-of-band

---

## Phase 4: User Story 2 — Migrations before traffic (Priority: P1)

**Goal**: Alembic Job runs `upgrade head` before backend serves traffic.

**Independent Test**: `kubectl apply --dry-run=server -f deploy/k8s/migration-job.yaml`; Job spec uses `rromani/jukebox-backend:0.1` and `JUKEBOX_DATABASE_URL` from Secret.

### Implementation for User Story 2

- [x] T006 [US2] Create `deploy/k8s/migration-job.yaml` (Job `jukebox-migrate`, `alembic upgrade head`, securityContext per bull pattern)

**Checkpoint**: Migration Job manifest ready; deploy order places this before backend rollout

---

## Phase 5: User Story 1 — Deploy core workloads (Priority: P1) 🎯 MVP

**Goal**: Backend and frontend Deployments + Services reach Ready with health probes.

**Independent Test**: After apply (with Secret populated), `kubectl get pods -n jukebox` shows backend and frontend Ready; `/api/health` and `/health` succeed.

### Implementation for User Story 1

- [x] T007 [P] [US1] Create `deploy/k8s/backend.yaml` mirroring `argocd-apps/manifests/bull/backend.yaml` (Service + Deployment, probes `/api/health`, securityContext UID 10001, resources, `readOnlyRootFilesystem` + `emptyDir` `/tmp`, image `rromani/jukebox-backend:0.1`, env from ConfigMap/Secret)
- [x] T008 [P] [US1] Create `deploy/k8s/frontend.yaml` mirroring `argocd-apps/manifests/bull/frontend.yaml` (Service port 80→8080, Deployment, probes `/health`, securityContext UID 101, resources, image `rromani/jukebox-frontend:0.1`)

**Checkpoint**: Core workloads defined; MVP deployable after migrate Job completes

---

## Phase 6: User Story 3 — Public Ingress (Priority: P2)

**Goal**: `jukebox.rromani.eu` routes `/api` → backend and `/` → frontend.

**Independent Test**: `kubectl apply --dry-run=server -f deploy/k8s/ingress.yaml`; rules match FR-006.

### Implementation for User Story 3

- [x] T009 [US3] Create `deploy/k8s/ingress.yaml` (host `jukebox.rromani.eu`, `ingressClassName: my-traefik`, paths `/api` and `/`)

**Checkpoint**: Public routing manifest complete

---

## Phase 7: User Story 5 — ArgoCD integration (Priority: P3)

**Goal**: Document GitOps mirror and example Application for `argocd-apps`.

**Independent Test**: `argocd-application.yaml.example` validates against Argo CD Application schema; README documents rsync mirror path.

### Implementation for User Story 5

- [x] T010 [US5] Create `deploy/k8s/argocd-application.yaml.example` (Application `jukebox`, path `manifests/jukebox`, repo `argocd-apps`)
- [x] T011 [P] [US5] Create `scripts/mirror-k8s-to-argocd.sh` (rsync `deploy/k8s/` → `../argocd-apps/manifests/jukebox/`, exclude example file)

**Checkpoint**: GitOps workflow documented and scriptable

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validation, documentation, change closure

- [x] T012 Create `scripts/k8s-validate.sh` — server dry-run on core manifests (exclude `argocd-application.yaml.example`) + SC-005 file-set parity vs `argocd-apps/manifests/bull/`
- [x] T013 Run `scripts/k8s-validate.sh` per SC-004 and SC-005
- [x] T014 Finalize `deploy/k8s/README.md` (env reference, deploy order, release tag bump, mirror steps, link to `scripts/k8s-validate.sh`)
- [x] T015 Sync `specs/changes/003-kubernetes-manifests/quickstart.md` with final manifest paths and smoke steps (api_tokens, CSP) per FR-009
- [x] T016 Execute manual validation checklist from `specs/changes/003-kubernetes-manifests/quickstart.md` (document results in checklist)
- [x] T017 Mark change `implemented` in `specs/manifest.yml`
- [x] T018 Update implementation validation in `specs/changes/003-kubernetes-manifests/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** → **Phase 2** → **US4** (config) → **US2** (migrate) → **US1** (workloads) → **US3** (ingress) → **US5** (GitOps) → **Polish**

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US4 | Foundational namespace | dry-run configmap + secret |
| US2 | US4 (Secret keys) | dry-run migration Job |
| US1 | US4 + US2 complete at runtime | pods Ready in cluster |
| US3 | US1 (Services exist) | dry-run ingress rules |
| US5 | All manifests in `deploy/k8s/` | example Application + mirror script |

### Parallel Opportunities

- **US4**: T004 + T005 parallel
- **US1**: T007 + T008 parallel
- **US5**: T011 parallel with T010 after manifests exist

---

## Parallel Example: User Story 1

```bash
# After US2 migration Job manifest exists:
# T007: deploy/k8s/backend.yaml
# T008: deploy/k8s/frontend.yaml
```

---

## Implementation Strategy

### MVP First (through US1)

1. Phase 1–2: Contract + namespace
2. US4: ConfigMap + Secret template
3. US2: Migration Job
4. US1: Backend + Frontend
5. **STOP**: Validate in-cluster health before ingress

### Full delivery

Add US3 (ingress) → US5 (ArgoCD) → Polish (`k8s-validate.sh` + quickstart)

### Suggested MVP scope

**T001–T008** (Setup + Foundational + US4 + US2 + US1)

---

## Notes

- Reference: `/Users/rromanit/workspace/argocd-apps/manifests/bull/`
- Image tag initial: `0.1` — bump on each GitHub Release in backend, frontend, migration-job YAML
- Never commit real credentials; `secret.yaml` uses `REPLACE_ME` only

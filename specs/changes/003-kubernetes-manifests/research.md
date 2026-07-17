# Research: 003-kubernetes-manifests

**Date**: 2026-07-17

## Decision: Canonical manifest location

**Decision**: `deploy/k8s/` in amrn-jukebox monorepo; mirror to `argocd-apps/manifests/jukebox`.

**Rationale**: Clarify session; aligns with amrn-bull also shipping `deploy/k8s/` in monorepo while ArgoCD consumes sibling repo.

**Alternatives**: Only argocd-apps (rejected — ops contract deferred to jukebox repo).

## Decision: Image tag strategy

**Decision**: Fixed tag per GitHub Release (initial `0.1`); update `backend.yaml`, `frontend.yaml`, `migration-job.yaml` manually on each release.

**Rationale**: Matches bull `0.7` pattern; CI pushes `rromani/jukebox-*:${{ github.event.release.tag_name }}`.

**Alternatives**: `latest` (rejected — poor GitOps traceability).

## Decision: JUKEBOX_COOKIE_SECURE

**Decision**: `"true"` in production ConfigMap.

**Rationale**: HTTPS public host + session auth (002); bull uses `false` but jukebox explicitly diverges.

## Decision: Secret handling

**Decision**: `secret.yaml` with `REPLACE_ME` placeholders committed; operator applies real values in cluster or via sealed secret later.

**Rationale**: FR-008; avoid committing credentials like bull's argocd-apps copy (anti-pattern).

## Decision: Migration orchestration

**Decision**: Standalone Job manifest; operator applies and waits `Complete` before backend Deployment (manual order, same as bull).

**Rationale**: No PreSync hook in v1; matches existing cluster tooling.

**Alternatives**: ArgoCD sync waves (deferred).

## Decision: Ingress topology

**Decision**: Mirror bull — `ingressClassName: my-traefik`, entrypoint `web`, host `jukebox.rromani.eu`, `/api` → backend:8000, `/` → frontend:80.

**Rationale**: Same cluster ingress controller as bull; TLS termination assumed at Traefik edge.

## Decision: Resource naming

**Decision**: `jukebox-backend`, `jukebox-frontend`, `jukebox-config`, `jukebox-secrets`, `jukebox-migrate`.

**Rationale**: Parallel to `bull-*` naming in argocd-apps.

## Open questions

None blocking.

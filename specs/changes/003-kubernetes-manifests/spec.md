---
id: 003-kubernetes-manifests
type: change
status: implemented
modifies:
  - ops-platform
depends_on:
  - 001-foundation-jukebox
  - 002-operator-auth-embed-tokens
requires_contract_update: true
read_by_default: true
---

# Feature Specification: Kubernetes Deployment Manifests

**Feature Branch**: `003-kubernetes-manifests`

**Created**: 2026-07-17

**Status**: Implemented

**Input**: Crear los ficheros de Kubernetes para amrn-jukebox basándose en el patrón de despliegue de amrn-bull en `argocd-apps/manifests/bull` (namespace, backend, frontend, migración, ingress, config y secret).

## Clarifications

### Session 2026-07-17

- Q: ¿Dónde es la fuente canónica de los manifiestos K8s? → A: `deploy/k8s/` en amrn-jukebox; el operador copia/sincroniza a `argocd-apps/manifests/jukebox`.
- Q: ¿Estrategia de tag de imagen en manifiestos? → A: Tag fijo por release GitHub (p. ej. `0.1`); actualizar manualmente en cada release CI (patrón bull).
- Q: ¿Valor de `JUKEBOX_COOKIE_SECURE` en ConfigMap de producción? → A: `"true"` (HTTPS público; cookies de sesión seguras).

## SDD Context

- Depends on: **001-foundation-jukebox** (imágenes Docker, compose, CI release), **002-operator-auth-embed-tokens** (variables `JUKEBOX_*` de auth en runtime)
- Modifies contract: `ops-platform`
- Reference implementation: `../argocd-apps/manifests/bull/` (bull-backend, bull-frontend, bull-migrate, ingress Traefik, Pod Security restricted)
- Product constraint: ingress enruta `/api/*` → backend y el resto → frontend nginx (SPA)

## Problem

Hoy jukebox solo se valida con Docker Compose local. No hay manifiestos Kubernetes en el monorepo ni en ArgoCD para desplegar en el cluster de producción con el mismo modelo que bull (GitOps, migraciones previas al rollout, probes en health).

## Goals

- Manifiestos K8s en **`deploy/k8s/`** (fuente canónica en el monorepo); mirror a `argocd-apps/manifests/jukebox` para GitOps.
- Namespace dedicado `jukebox` con Pod Security `restricted`.
- Backend y frontend como Deployments + Services ClusterIP.
- Job de migración Alembic (`alembic upgrade head`) usando la misma imagen backend.
- Ingress con host público, paths `/api` → backend y `/` → frontend.
- ConfigMap para valores no sensibles (`JUKEBOX_CORS_ALLOW_ORIGINS`, `JUKEBOX_COOKIE_SECURE`, `JUKEBOX_FRAME_ANCESTORS`).
- Secret para credenciales (`JUKEBOX_DATABASE_URL`, operador, `JUKEBOX_SESSION_SECRET`).
- Imágenes referenciadas como `rromani/jukebox-backend:<release>` y `rromani/jukebox-frontend:<release>` con **tag fijo** (p. ej. `0.1`) actualizado en cada GitHub Release.

## Non-Goals

- Provisionar PostgreSQL dentro del cluster (se asume BD externa como en bull).
- SealedSecrets / External Secrets Operator (documentar; valores reales fuera del repo).
- HPA, PDB, network policies avanzadas (v1).
- Cambios en kiosk-screen (change posterior).
- Modificar el cluster Traefik / ingress class (reutilizar `my-traefik` existente).

## User Scenarios & Testing

> **Deploy order vs story priority**: P1 stories (US1 workloads, US2 migration) are implemented after **US4** (P2 config) because ConfigMap and Secret are blocking prerequisites at runtime. Task phases follow deploy order, not numeric priority alone.

### User Story 1 — Desplegar workloads core (Priority: P1)

Como operador de plataforma, sincronizo los manifiestos en el namespace `jukebox` y obtengo backend + frontend en ejecución con probes verdes.

**Why this priority**: Sin pods no hay despliegue.

**Independent Test**: `kubectl get pods -n jukebox` muestra backend y frontend `Running`; readiness en `/api/health` y `/health`.

**Acceptance Scenarios**:

1. **Given** imágenes publicadas en Docker Hub, **When** aplico Deployments y Services, **Then** ambos pods alcanzan `Ready` en menos de 3 minutos.
2. **Given** Secret y ConfigMap montados, **When** el backend arranca, **Then** responde `200` en `/api/health` desde dentro del cluster.

---

### User Story 2 — Migraciones antes del tráfico (Priority: P1)

Como operador, ejecuto el Job de migración antes de exponer usuarios para que el esquema DB esté al día.

**Why this priority**: Evita arrancar backend contra esquema obsoleto.

**Independent Test**: Job `jukebox-migrate` termina `Complete`; tablas incluyen `api_tokens` (002).

**Acceptance Scenarios**:

1. **Given** BD vacía o en revisión anterior, **When** ejecuto el Job de migración, **Then** `alembic upgrade head` completa con éxito.
2. **Given** migración fallida, **When** el Job reintenta hasta `backoffLimit`, **Then** no se asume backend listo para producción.

---

### User Story 3 — Exposición pública vía Ingress (Priority: P2)

Como usuario final, accedo a `https://jukebox.rromani.eu` y la SPA carga; las llamadas a `/api/*` llegan al backend.

**Why this priority**: Habilita uso real tras despliegue interno.

**Independent Test**: `curl https://jukebox.rromani.eu/api/health` → `{"status":"ok"}`; `curl -I https://jukebox.rromani.eu/` → frontend.

**Acceptance Scenarios**:

1. **Given** Ingress aplicado, **When** solicito `/api/health`, **Then** la respuesta proviene del backend.
2. **Given** Ingress aplicado, **When** solicito `/login` o `/`, **Then** la respuesta proviene del frontend nginx.

---

### User Story 4 — Configuración runtime JUKEBOX_* (Priority: P2)

Como operador, configuro CORS, cookies seguras y `frame-ancestors` para kiosk sin rebuild de imagen.

**Why this priority**: Kiosk iframe y auth dependen de variables de entorno (002).

**Independent Test**: Cambiar `JUKEBOX_FRAME_ANCESTORS` en ConfigMap y ver header CSP en `/api/health`.

**Acceptance Scenarios**:

1. **Given** ConfigMap con `JUKEBOX_CORS_ALLOW_ORIGINS` del kiosk, **When** el SPA llama API con credenciales, **Then** CORS permite el origen configurado.
2. **Given** Secret con operador y session secret, **When** login vía `/api/auth/login`, **Then** se establece cookie `jukebox_session`.

---

### User Story 5 — Integración ArgoCD (Priority: P3)

Como operador GitOps, registro la aplicación jukebox en `argocd-apps` apuntando a los manifiestos del repo.

**Why this priority**: Automatiza sync continuo; puede vivir en repo hermano como bull.

**Independent Test**: Application ArgoCD `jukebox` en estado `Synced` y `Healthy`.

**Acceptance Scenarios**:

1. **Given** `Application` ArgoCD con `repoURL` apuntando a `argocd-apps` y `path: manifests/jukebox` (contenido sincronizado desde `deploy/k8s/`), **When** ArgoCD sincroniza, **Then** crea namespace y recursos sin drift manual.
2. **Given** nuevo tag de imagen en manifiestos, **When** sync, **Then** rollout actualiza pods.

---

### Edge Cases

- Imagen con tag inexistente → pods `ImagePullBackOff`; documentar en quickstart.
- Secret ausente o clave incorrecta → backend crash loop; probes fallan.
- Migración concurrente con backend viejo → operador debe ejecutar Job antes de rollout (orden documentado).
- `JUKEBOX_FRAME_ANCESTORS` debe incluir origen kiosk para iframe display.
- Pod Security restricted: contenedores non-root, `readOnlyRootFilesystem`, `emptyDir` en `/tmp` (patrón bull).

## Requirements

### Functional Requirements

- **FR-001**: El change MUST añadir manifiestos bajo `deploy/k8s/` en el monorepo jukebox como **fuente canónica** (namespace, backend, frontend, migration job, ingress, configmap, secret template).
- **FR-001b**: El operador MUST poder copiar/sincronizar `deploy/k8s/` → `argocd-apps/manifests/jukebox` sin transformación manual de estructura.
- **FR-002**: Los manifiestos MUST seguir la estructura y hardening de `argocd-apps/manifests/bull` (labels, securityContext, probes, resources).
- **FR-003**: Backend Deployment MUST exponer puerto 8000 y probes HTTP en `/api/health`.
- **FR-004**: Frontend Deployment MUST exponer puerto 8080 (nginx) y probes en `/health`.
- **FR-005**: Migration Job MUST ejecutar `alembic upgrade head` con imagen backend y `JUKEBOX_DATABASE_URL` del Secret.
- **FR-006**: Ingress MUST enrutar prefix `/api` al Service backend y `/` al Service frontend con `ingressClassName: my-traefik`.
- **FR-007**: ConfigMap MUST incluir `JUKEBOX_CORS_ALLOW_ORIGINS`, `JUKEBOX_COOKIE_SECURE` (`"true"` en producción HTTPS), y `JUKEBOX_FRAME_ANCESTORS`.
- **FR-008**: Secret MUST incluir `JUKEBOX_DATABASE_URL`, `JUKEBOX_OPERATOR_USERNAME`, `JUKEBOX_OPERATOR_PASSWORD`, `JUKEBOX_SESSION_SECRET` (plantilla sin valores reales en git).
- **FR-009**: Debe existir documentación de despliegue (quickstart) con orden: migración → backend/frontend → verificación ingress.
- **FR-010**: Debe entregarse `deploy/k8s/argocd-application.yaml.example` documentando la Application ArgoCD (`path: manifests/jukebox` en repo `argocd-apps`) y el flujo de mirror desde `deploy/k8s/`.
- **FR-011**: Deployments y Job de migración MUST referenciar tag de imagen **fijo** (`rromani/jukebox-backend:<version>`, `rromani/jukebox-frontend:<version>`); la versión se actualiza manualmente al publicar cada GitHub Release (mismo patrón que bull `0.7`).

### Key Entities

- **Namespace `jukebox`**: aislamiento y labels Pod Security.
- **ConfigMap `jukebox-config`**: variables no sensibles `JUKEBOX_*`.
- **Secret `jukebox-secrets`**: credenciales runtime.
- **Deployments**: `jukebox-backend`, `jukebox-frontend`.
- **Job**: `jukebox-migrate`.
- **Ingress**: host `jukebox.rromani.eu` (configurable).

## Success Criteria

- **SC-001**: Operador despliega stack completo en cluster de prueba en menos de 30 minutos siguiendo quickstart.
- **SC-002**: Tras sync, `/api/health` y login operador funcionan en URL pública.
- **SC-003**: Job de migración completa sin error en BD nueva.
- **SC-004**: Manifiestos pasan validación `kubectl apply --dry-run=server` sin errores.
- **SC-005**: Paridad estructural verificable con bull (mismo conjunto de tipos de recurso K8s).

## Assumptions

- Host de producción: `jukebox.rromani.eu` (paralelo a `bull.rromani.eu`).
- PostgreSQL externo en la misma red que el cluster (como bull).
- Imágenes publicadas por workflow `release-images.yml` a Docker Hub `rromani/jukebox-*`; tag en manifiestos = versión del GitHub Release (inicial `0.1`).
- CORS incluye `https://kiosk.rromani.eu` para integración kiosk-screen.
- `JUKEBOX_COOKIE_SECURE=true` en ConfigMap de producción (diverge de bull `false`; requerido para HTTPS y auth 002).
- ArgoCD consume manifiestos desde `argocd-apps/manifests/jukebox`; contenido originado en `deploy/k8s/` del monorepo jukebox (copia/sincronización por operador o script).

## Contract updates (required before implement)

- `specs/contracts/ops-platform/contract.md` — documentar `deploy/k8s/`, orden de despliegue, variables K8s, relación con ArgoCD.

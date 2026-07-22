# Implementation Plan: Hardening & Polish

**Branch**: `010-hardening-and-polish` | **Change id**: `010-hardening-and-polish` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/changes/010-hardening-and-polish/spec.md`

## Summary

Consolidated remediation + completion + hygiene across all three contracts. No new product surfaces. Core technical moves:

1. **SSE audience routing** — tag each `/api/events/stream` subscriber at connect time with its authorizing audience (`operator` or `participant:{id}`) and route events server-side so `api_key_usage` reaches only operators and `notification` reaches only the target participant. `state` stays broadcast.
2. **Secrets & auth hardening** — untrack `.env`, rotate `JUKEBOX_SESSION_SECRET`, restrict CORS `allow_headers`, add an indexed non-secret prefix to `api_tokens` and verify by prefix (prefix-less legacy tokens rejected → regenerate).
3. **Robustness** — migrate all outbound HTTP (YouTube search/videos/oEmbed, Google OAuth) off the event loop; bound the search rate limiter's memory; make the Pacific quota-day reset deterministic on read; add an FK on `queue_entries.submitted_by_participant_id` (nulling orphans); unify submit-metadata strictness.
4. **Event configuration** — add `GET/PUT /api/event-config` over the existing `event_config` singleton (no migration) and replace the admin "Evento" placeholder with an editable Spanish form; wire `event_config.theme` (`default` only).
5. **Frontend polish** — responsive kiosk layout (`app_height_px` as target, not clip), per-row moderation busy state, QR regeneration only on URL change, remove unused Angular Material/CDK, add a Spanish 404 page + loading states, gate residual dev/test affordances.
6. **Tests & hygiene** — cover changed behavior (backend + frontend); reconcile contract headers, remove the duplicated `.specify/.specify/`, update `AGENTS.md`/`manifest.yml`, pin backend `replicas: 1` and document single-replica constraint.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, psycopg 3, Starlette SessionMiddleware, itsdangerous; Angular standalone, TailwindCSS, `qrcode`. New backend dep: an async HTTP client (`httpx`) or `asyncio.to_thread` offload of the existing `urllib` calls (decision in research.md).

**Storage**: PostgreSQL. Two new Alembic revisions: `0007_api_token_prefix`, `0008_queue_submitter_fk`. No migration for event-config (columns exist on `event_config`).

**Testing**: pytest + FastAPI `TestClient` (backend); Vitest + Playwright browser provider (frontend). New: `test_event_config.py`, SSE isolation assertions, token-prefix, rate-limiter eviction, quota rollover-on-read, `0008` migration test; frontend guard/interceptor/SSE/event-config-form specs.

**Target Platform**: Docker Compose (dev) / Kubernetes + ArgoCD (prod), single backend replica.

**Project Type**: Web application (FastAPI API + Angular SPA monorepo).

**Performance Goals**: Event-loop not blocked by outbound HTTP (SC-003); token exchange ≤1 hash comparison/request (SC-004); event-config change reflected on kiosk within SSE window ~5 s (SC-005).

**Constraints**: Single replica (per-process shared state); Spanish UI; retain single SSE endpoint/transport; preserve all 001–009 client-visible behavior and error mappings; bundle within existing budgets (800 kb warn / 1.5 mb error).

**Scale/Scope**: 3 contracts; 2 new REST endpoints; SSE routing change; 2 migrations; ~5 backend service edits; ~6 frontend surfaces; ops manifest + docs; SDD hygiene.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` into `backend-api`, `app-core`, `ops-platform` at implement start |
| II. Manifest-driven context | Pass | `manifest.yml` updated; `010` active |
| III. Change specs incremental | Pass | This spec declares affected contracts + status `draft` |
| IV. Contract updates before implementation | Pass | Deltas drafted; behavior-changing items (SSE routing, event-config, token prefix, submit validation) documented |
| V. Tests for changed behavior | Pass | Test tasks per user story (FR-025/FR-026) |
| VI. Sibling conventions | Pass | `/api/*` prefix, operator/participant cookies, SSE on `/api/events/stream`, Spanish UI retained |

**Post-design re-check**: Pass. Single justified deviation tracked below (single-replica pin instead of externalized state).

## Project Structure

### Documentation (this change)

```text
specs/changes/010-hardening-and-polish/
├── spec.md
├── plan.md                     # this file
├── contracts/contract-deltas.md
└── tasks.md                    # Phase 2 (/speckit.tasks)
```

(`research.md`, `data-model.md`, `quickstart.md`, `context-pack.md`, `checklists/` may be added in later flow steps; not required for this specify/plan pass.)

### Source Code (repository root)

```text
backend/
├── alembic/versions/
│   ├── 0007_api_token_prefix.py          # new — indexed token prefix
│   └── 0008_queue_submitter_fk.py        # new — null orphans + FK
├── app/
│   ├── config.py                         # CORS allow_headers; single parse_youtube_api_keys reuse
│   ├── models.py                         # api_tokens.prefix; queue_entries FK
│   ├── schemas.py                        # EventConfigRead / EventConfigUpdate
│   ├── security.py                        # token lookup by prefix; SSE subscriber audience tagging helper
│   ├── routers/
│   │   ├── event_config.py               # new — GET/PUT /api/event-config
│   │   ├── state.py                       # subscribe with audience; stream setup
│   │   ├── auth.py / tokens.py            # prefix-based token create/verify
│   │   └── auth_google.py                 # async OAuth calls
│   ├── services/
│   │   ├── sse_hub.py                     # audience-aware subscribe + routed broadcast
│   │   ├── notification_service.py        # target-participant delivery
│   │   ├── youtube_api_key_usage_service.py # operator-audience broadcast; deterministic roll-on-read
│   │   ├── search_rate_limiter.py         # eviction of expired windows
│   │   ├── youtube_search_service.py      # async client
│   │   ├── youtube_meta.py                # async client; strict metadata for both submit paths
│   │   └── google_oauth_service.py        # async client
│   └── main.py
└── tests/
    ├── test_event_config.py              # new
    ├── test_sse.py / test_notifications.py  # isolation assertions
    ├── test_tokens.py / test_auth.py     # prefix lookup + legacy rejection
    ├── test_youtube_search.py            # rate-limiter eviction
    ├── test_youtube_api_key_usage.py     # roll-on-read + operator-only SSE
    ├── test_auth_policy.py               # + event-config routes
    └── test_migrations_0008.py           # orphan nulling (new)

frontend/src/app/
├── app.routes.ts                         # 404 route
├── auth.guard.spec.ts / auth.interceptor.spec.ts  # new tests
├── not-found/not-found.component.*       # new — Spanish 404
├── admin/admin.component.*               # Evento editor; per-row moderation busy
├── display/
│   ├── display.component.*               # responsive layout; theme application
│   └── qr-panel.component.ts             # QR cache on URL change
├── participate/participate.component.*   # theme application; residual dev affordance gating
├── services/
│   ├── event-config.service.ts           # new — GET/PUT /api/event-config
│   ├── display-state.service.ts          # (unchanged consumer; server now routes events)
│   └── *.spec.ts                          # SSE/guard/interceptor coverage
└── models/event-config.ts                # new DTO

frontend/package.json                     # remove @angular/material, @angular/cdk

deploy/k8s/
├── backend.yaml                          # replicas: 1
└── README.md                             # single-replica constraint + secret rotation + token reissue notes

.gitignore                                # ignore .env
```

**Structure Decision**: Extend existing routers/services; the only new backend router is `event_config.py`. SSE isolation is implemented inside `sse_hub.py` + `state.py` (subscriber carries an audience tag) without changing the endpoint or transport. Frontend adds a `not-found` component, an `event-config` service/model, and test specs; no new routes beyond `**` → 404.

## Phase 0 — Research (open decisions to resolve in research.md)

| Topic | Decision to make |
|-------|------------------|
| Async HTTP | `httpx.AsyncClient` (new dep) vs `asyncio.to_thread` wrapping current `urllib` — pick lowest-risk that preserves timeouts/error mapping |
| SSE audience tag | Where to store audience on subscriber (queue wrapper object vs metadata dict) and how `notification_service` selects target subscribers |
| Token prefix | Prefix length/format (e.g. first 8 chars of the token, stored plaintext + indexed) and create-time wiring; confirm legacy rejection path |
| Quota roll-on-read | Ensure `build_usage_list`/`record_attempt` both evaluate Pacific boundary without a scheduler; per-process acceptable under single replica |
| Rate-limiter eviction | Lazy purge on access vs periodic sweep; bound by time window |
| Event-config validation bounds | Concrete min/max for `app_height_px`, range for `queue_visible_count`, max lengths for `name`/`subtitle`; supported `theme` set = {`default`} |
| Kiosk responsive | CSS approach (flex/grid + `min-height`/`clamp`, `app_height_px` as target via CSS var without hard `max-height` clip) |

## Phase 1 — Design (highlights)

### Backend

1. **SSE routing** (`sse_hub.py`, `state.py`): subscribe returns a handle carrying `audience` (`operator` | `participant:{id}`). `broadcast_state` → all; `broadcast_api_key_usage` → operator subscribers only; notification delivery → subscribers whose `participant_id` matches. `get_stream_subscriber` already distinguishes identities — pass that identity into `subscribe`.
2. **event-config** (`routers/event_config.py`, `schemas.py`): `EventConfigRead` / `EventConfigUpdate`; `GET`/`PUT` require `CurrentUser`; `PUT` validates, persists, bumps `revision`, broadcasts `state`.
3. **Token prefix** (`models.py`, `security.py`, `tokens.py`, `0007`): store non-secret prefix at create; `find_active_token` filters by prefix (indexed) then verifies the single candidate hash; prefix-less rows never match → rejected.
4. **FK** (`0008`, `models.py`): `UPDATE queue_entries SET submitted_by_participant_id = NULL WHERE submitted_by_participant_id NOT IN (SELECT id FROM participants)`, then add FK; downgrade drops FK.
5. **Async I/O** (`youtube_search_service.py`, `youtube_meta.py`, `google_oauth_service.py`): swap `urllib.urlopen` for the chosen async approach; keep 10 s timeouts and existing exception→HTTP mappings.
6. **Rate limiter / quota** (`search_rate_limiter.py`, `youtube_api_key_usage_service.py`): evict expired windows on access; evaluate quota-day boundary on every read/increment.
7. **CORS** (`config.py`/`main.py`): explicit `allow_headers` list (e.g. `content-type`).

### Frontend

1. **event-config**: `event-config.service.ts` (`getConfig`, `updateConfig`), `models/event-config.ts`; `admin.component` "Evento" form (load on init, validate, save, Spanish success/error copy).
2. **Theme**: apply `state.event_config.theme` on `/` and `/participar`; `default` → current tokens; unknown → `default`.
3. **Kiosk layout**: replace hard `max-height` clip with responsive container; `--jukebox-app-height` used as target when it fits.
4. **Moderation**: per-row busy signal keyed by entry id (replace single `moderationBusy`).
5. **QR**: cache last URL; regenerate only when it changes.
6. **404 + loading**: `not-found` component; `**` route → it; loading indicators on admin/participar fetches.
7. **Deps / dev affordances**: remove Material/CDK; gate `resetForTesting`/`devAuthAsync`/dev button out of prod.

### Ops

1. `deploy/k8s/backend.yaml` → `replicas: 1`; README documents per-process state + single-replica requirement, session-secret rotation, and one-time token reissue.
2. `.gitignore` ignores `.env`; `git rm --cached .env`; rotate `JUKEBOX_SESSION_SECRET`.

## Phase 2 — Implementation phases (reference for tasks)

- **Phase A** — Contracts + manifest + hygiene (merge deltas; headers; `.specify` de-dup; `AGENTS.md`).
- **Phase B (US1)** — SSE audience routing + tests (P1).
- **Phase C (US2)** — Secrets/CORS: `.env` untrack, rotate secret, gitignore, CORS headers (P1).
- **Phase D (US3)** — Async I/O + `replicas:1` + single-replica docs (P2).
- **Phase E (US4)** — Token prefix (`0007`), FK (`0008`), rate-limiter eviction, quota roll-on-read, submit-validation unification (P2).
- **Phase F (US5)** — event-config endpoint + admin editor + theme wiring (P2).
- **Phase G (US6)** — Kiosk responsive, per-row moderation, QR cache, dead-dep removal, 404/loading, dev-affordance gating (P3).
- **Phase H (US7)** — Backend + frontend test coverage (P3).
- **Phase I (US8)** — Final contract/manifest/AGENTS reconciliation + regression + quickstart (P3).

## Risks

| Risk | Mitigation |
|------|------------|
| Session-secret rotation logs everyone out mid-event | Schedule rotation during setup; kiosk shows existing "Sesión caducada" state (002), not an error |
| Legacy tokens stop working | Documented one-time reissue; operator regenerates before rollout (US2/ops README) |
| Async I/O migration changes error mapping | Preserve timeouts + map exceptions to the same HTTP codes; regression tests on search/OAuth |
| FK migration fails on orphan data | Null orphans in the same migration before adding the constraint; reversible downgrade |
| SSE routing regression drops `state` updates | Explicit test that all audiences still receive `state`; least-privilege default only affects `notification`/`api_key_usage` |
| Kiosk responsive change clips on odd resolutions | Layout tests/manual checks at 720p/1080p/2160p; `app_height_px` as target not clip |
| Removing Material/CDK breaks a hidden import | Build + type-check gate; they are reported unused |

## Complexity Tracking

| Deviation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Pin backend `replicas: 1` instead of externalizing shared state | SSE hub, rate limiter, key pool, quota counters are per-process today; correct multi-replica behavior needs Redis/pub-sub, a larger change | Externalizing now expands scope beyond remediation; documented single-replica is the safe, low-risk interim (deferred to a future change) |

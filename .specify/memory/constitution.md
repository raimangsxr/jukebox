# amrn-jukebox Constitution

## Core Principles

### I. Active Contracts Are Source of Truth

Current behavior MUST be described in active contract specs under `specs/contracts/**/contract.md`. Historical feature specs under `specs/changes/**` MUST NOT be treated as source of truth after consolidation.

### II. Manifest-Driven Context Selection

Agents MUST start from `specs/manifest.yml`. Agents MUST NOT scan all specs, plans, tasks, or archived material by default.

### III. Change Specs Are Incremental Records

Change specs describe proposed, in-progress, implemented, or consolidated changes. They MUST declare affected contracts and status.

### IV. Contract Updates Before Implementation

If a change modifies user-visible behavior, API behavior, data behavior, security, or runtime behavior, the affected active contract MUST be updated before implementation.

### V. Tests For Changed Behavior

Every changed behavior MUST have automated tests or an explicit manual validation task with rationale.

### VI. Sibling App Conventions

Follow amrn-bull and amrn-escalabirras-dual monorepo layout, `/api/*` prefix, operator session cookies, embed tokens for kiosk iframes, and `bull:config` / `bull:resize` iframe protocol for kiosk-screen.

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL (`JUKEBOX_` env prefix).
- Frontend: Angular 22 standalone, TailwindCSS, TypeScript.
- User-facing language: Spanish (`lang="es"`).

## Development Workflow

1. Read `specs/manifest.yml`.
2. Read `context-pack.md` for the active change.
3. Update active contracts before implementation when behavior changes.
4. Implement from tasks with tests.
5. Consolidate accepted behavior into contracts and update manifest status.

**Version**: 1.0.0 | **Ratified**: 2026-07-17

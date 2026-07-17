# Kiosk Screen Constitution

## Core Principles

### I. Active Contracts Are Source of Truth

Current behavior MUST be described in active contract specs under `specs/contracts/**/contract.md`. Historical feature specs under `specs/changes/**` MUST NOT be treated as source of truth after consolidation.

### II. Manifest-Driven Context Selection

Agents MUST start from `specs/manifest.yml`. Agents MUST NOT scan all specs, plans, tasks, or archived material by default. Reading extra context requires a reason tied to the current task.

### III. Change Specs Are Incremental Records

Change specs under `specs/changes/**` describe proposed, in-progress, implemented, or consolidated changes. They MUST declare `modifies`, `status`, `requires_contract_update`, and whether they are safe to read by default.

### IV. Contract Updates Before Implementation

If a change modifies user-visible behavior, API behavior, data behavior, security, observability, accessibility, or runtime behavior, the affected active contract MUST be updated before implementation.

### V. Derived Artifacts Are Not Hidden Truth

`plan.md`, `tasks.md`, `research.md`, `data-model.md`, and `quickstart.md` are derived artifacts for a specific change. Durable technical rationale MUST be captured in ADRs under `docs/adr/` rather than living only in plans or task lists.

### VI. Tests For Changed Behavior

Every changed behavior MUST have automated tests or an explicit manual validation task with rationale. Backend contract/integration/unit tests and Angular specs are preferred over manual validation when technically feasible.

### VII. Token-Aware Context Packs

Before planning or implementation, the active change MUST have a `context-pack.md` that lists mandatory specs, optional specs, ADRs, code entrypoints, tests, and files that must not be read.

### VIII. Supersedes Means Replacement

`supersedes` MUST only mean replacement. Use `extends`, `depends_on`, or `modifies` for weaker relationships. A spec that merely adds behavior to an active contract MUST NOT claim to supersede that contract.

## Additional Constraints

- Backend is FastAPI, SQLAlchemy, Alembic, and PostgreSQL.
- Frontend is Angular and TypeScript.
- User-facing errors must not expose internal paths, storage locations, or secrets.
- Display runtime changes must preserve kiosk safety during live events.
- Generated specs should stay concise; if a spec exceeds the line budget, it must include an explicit oversize justification and a context pack.

## Development Workflow

1. Read `specs/manifest.yml`.
2. Identify affected active contracts.
3. Create or update the change spec under `specs/changes/NNN-<slug>/`.
4. Create or update `context-pack.md`.
5. Update active contracts before implementation when behavior changes.
6. Run `/speckit.clarify`, `/speckit.checklist`, `/speckit.plan`, `/speckit.tasks`, and `/speckit.analyze` as needed before implementation.
7. Implement from tasks with tests.
8. Consolidate accepted behavior back into the active contract and update `manifest.yml`.

## Governance

This constitution supersedes older flat-spec conventions in AGENTS.md, README.md, and individual feature plans. Amendments require an explicit update to this file, `specs/manifest.yml`, and the relevant templates or command instructions when the workflow changes.

**Version**: 1.0.0 | **Ratified**: 2026-06-25 | **Last Amended**: 2026-06-25

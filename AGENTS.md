# amrn-jukebox Agent Instructions

## SDD policy

1. Start every SDD task from `specs/manifest.yml`.
2. Treat `specs/contracts/**/contract.md` as the source of truth for current behavior.
3. Treat `specs/changes/**` as incremental records.
4. Read `context-pack.md` for the active change before planning or implementation.
5. If behavior changes, update the affected active contract before implementation.
6. Keep `specs/manifest.yml` synchronized with new contracts and change status.
7. Run narrow tests first, then broader validation.

## Active SDD work

Active change: **010-hardening-and-polish** (draft). Last completed: **009-admin-api-key-usage** (implemented).

010 is a consolidated remediation/completion/hygiene change across all three contracts (see `specs/changes/010-hardening-and-polish/spec.md` and `contracts/contract-deltas.md`). Next SDD steps for it: `clarify → checklist → plan → tasks → analyze → implement`.

To start a different feature: `/speckit.specify` and set `active.change` in `specs/manifest.yml`.

## Suggested flow

`specify → clarify → checklist → plan → tasks → analyze → implement`

Spec Kit commands live in `.opencode/commands/speckit.*.md` and `.cursor/skills/`.  
Set active feature via `.specify/feature.json` or `SPECIFY_FEATURE=NNN-slug`.

## Sibling conventions

Follow `amrn-bull` and `amrn-escalabirras-dual` for monorepo layout, `/api/*` prefix, operator sessions, embed tokens, SSE, and kiosk iframe protocol (`bull:config`, `bull:resize`).

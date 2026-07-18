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

No active change. Last completed: **008-youtube-text-search** (implemented).

To start a new feature: `/speckit.specify` and set `active.change` in `specs/manifest.yml`.

## Suggested flow

`specify → clarify → checklist → plan → tasks → analyze → implement`

Spec Kit commands live in `.opencode/commands/speckit.*.md` and `.cursor/skills/`.  
Set active feature via `.specify/feature.json` or `SPECIFY_FEATURE=NNN-slug`.

## Sibling conventions

Follow `amrn-bull` and `amrn-escalabirras-dual` for monorepo layout, `/api/*` prefix, operator sessions, embed tokens, SSE, and kiosk iframe protocol (`bull:config`, `bull:resize`).

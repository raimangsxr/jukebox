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

- Active change: **002-operator-auth-embed-tokens**
- Context pack: `specs/changes/002-operator-auth-embed-tokens/context-pack.md`
- SDD gates: specify ✅ clarify ✅ checklist ✅ plan ✅ tasks ✅ analyze ✅
- **Next**: `/speckit.implement`

## Suggested flow

`specify → clarify → checklist → plan → tasks → analyze → implement`

Spec Kit commands live in `.opencode/commands/speckit.*.md` and `.cursor/skills/`.  
Set active feature via `.specify/feature.json` or `SPECIFY_FEATURE=NNN-slug`.

## Sibling conventions

Follow `amrn-bull` and `amrn-escalabirras-dual` for monorepo layout, `/api/*` prefix, operator sessions, embed tokens, SSE, and kiosk iframe protocol (`bull:config`, `bull:resize`).

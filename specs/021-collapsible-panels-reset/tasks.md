---
description: "Task list for 021-collapsible-panels-reset"
---

# Tasks: Paneles plegables y reinicio de historial

**Input**: Design documents from `specs/021-collapsible-panels-reset/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/contract-deltas.md](./contracts/contract-deltas.md), [research.md](./research.md)

**Tests**: Backend US3 + `collapsible-section.component.spec.ts` + `participate.component.spec.ts` smoke; manual validation T024 (constitution V for UI).

**Organization**: Grouped by user story (US1–US3). US1/US2 = P1, US3 = P2. Depends on **017** queue history API.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: owning user story (US1…US3)
- Paths are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: SDD scaffolding before code changes.

- [X] T001 [P] Merge `specs/021-collapsible-panels-reset/contracts/contract-deltas.md` into `specs/contracts/backend-api/contract.md` and `specs/contracts/app-core/contract.md` (draft DELETE history + collapsible layout sections).
- [X] T002 [P] Register change `021-collapsible-panels-reset` in `specs/manifest.yml` (`changes:` entry, `status: planned`, `modifies: backend-api, app-core`); set `active.change` and `active.context_pack` to this feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared UI primitive required by US1 and US2.

**⚠️ CRITICAL**: No user story UI work can begin until T003 is complete.

- [X] T003 Create standalone `CollapsibleSectionComponent` in `frontend/src/app/components/collapsible-section/collapsible-section.component.ts` (+ `.html`, `.css`) with `@Input() title`, `expanded`, optional `badge`; `@Output() expandedChange`; header `<button type="button">` with `aria-expanded` / `aria-controls`; **chevron que rota ~90° cuando expanded**; content region toggled on click.
- [X] T004 [P] Add `frontend/src/app/components/collapsible-section/collapsible-section.component.spec.ts` — toggle click flips `expandedChange`; `aria-expanded` matches state; chevron CSS class toggles (constitution V for shared UI primitive).

**Checkpoint**: Component importable and unit-tested.

---

## Phase 3: User Story 1 — Admin con paneles plegables (Priority: P1) 🎯 MVP

**Goal**: Each Admin section is collapsible; only Moderación expanded on load; badges on Moderación (pendientes) and Historial (**total global**); no auto-expand on new pending; SSE refreshes history across tabs.

**Independent Test**: Login → `/admin` → only Moderación expanded; Historial badge shows global total even when list filter is «Reproducidas»; new pending updates badge without expanding panel; second Admin tab syncs history after vaciar.

### Implementation for US1

- [X] T005 [US1] Add panel expanded state map in `frontend/src/app/admin/admin.component.ts` (`moderation: true`, `history`/`reserve`/`apiKeys`/`event`/`tokens`: `false`); helper `togglePanel(id)`; preserve state for session (no localStorage).
- [X] T006 [US1] Wrap Moderación, Historial, Reserva, API Keys, Evento and Tokens sections in `app-collapsible-section` in `frontend/src/app/admin/admin.component.html`; keep `app-live-status` and header/logout outside panels.
- [X] T007 [US1] In `frontend/src/app/admin/admin.component.ts`, maintain **`historyTotalAll`** via `GET /api/queue/history?page_size=1` **without** `status` filter (for Historial badge and Vaciar disabled state); keep paginated `historyEntries` / `historyTotal` respecting `historyStatusFilter` for the table only. Bind badge in `admin.component.html`: Moderación → `pending().length`; Historial → `historyTotalAll`.
- [X] T008 [US1] In `frontend/src/app/admin/admin.component.ts`, extend `displayState.state$` subscription to call `refreshHistory()` and refresh `historyTotalAll` (not only `refreshPending()`), so multi-tab Admin stays in sync after `bump_revision` (e.g. vaciar historial in another tab).
- [X] T009 [US1] Verify SSE/pending refresh does **not** set `moderation` panel to expanded when collapsed (only updates `pending()` badge).

**Checkpoint**: US1 independently testable per [quickstart.md](./quickstart.md) Phases 1 and 6.

---

## Phase 4: User Story 2 — Participación reordenada con paneles plegables (Priority: P1)

**Goal**: Order: fixed «Sonando ahora» strip → votos (expanded) → enviar canciones (collapsed) → mis canciones (collapsed).

**Independent Test**: Login `/participar` → votes panel first and expanded; submit block includes search + URL + Enviar; mis canciones last; Sonando ahora between header and votes when playing.

### Implementation for US2

- [X] T010 [US2] Add panel state defaults in `frontend/src/app/participate/participate.component.ts` (`votes: true`, `submit: false`, `mySongs: false`) and toggle helpers.
- [X] T011 [US2] Reorder `frontend/src/app/participate/participate.component.html`: move `now_playing` block to fixed strip after header/live-status and before collapsible panels; hide when no `now_playing`.
- [X] T012 [US2] Wrap Cola votable, Enviar canciones (merge Buscar + Pegar enlace + `submit-footer` button), and Mis canciones in `app-collapsible-section` in `frontend/src/app/participate/participate.component.html`.
- [X] T013 [P] [US2] Update `frontend/src/app/participate/participate.component.spec.ts` smoke assertions for new section order.

**Checkpoint**: US2 independently testable per [quickstart.md](./quickstart.md) Phases 2 and 2b.

---

## Phase 5: User Story 3 — Vaciar historial completo (Priority: P2)

**Goal**: Operator clears all terminal history (`played` + `rejected`); modal confirm; participants lose those rows from «Mis canciones» via SSE; filter active in UI does not limit delete scope.

**Independent Test**: Historial with mixed terminal rows → filter «Reproducidas» → Vaciar historial → confirm → all terminal rows gone including rejected; active queue untouched; participant submissions updated.

### Tests for US3 (write first, must fail) ⚠️

- [X] T014 [P] [US3] Add `test_clear_history_operator_success` in `backend/tests/test_queue_history.py` — operator DELETE → 204; terminal rows deleted; `pending_review`/`queued`/`playing` remain.
- [X] T015 [P] [US3] Add `test_clear_history_forbidden_for_participant` in `backend/tests/test_queue_history.py` — participant session → 401.
- [X] T016 [P] [US3] Add `test_clear_history_idempotent` and `test_clear_history_participant_submissions` in `backend/tests/test_queue_history.py` — second DELETE 204; `/api/participant/submissions` excludes deleted terminal entries.
- [X] T017 [P] [US3] Add `test_clear_history_with_active_filter_deletes_all_terminal` in `backend/tests/test_queue_history.py` — mix played+rejected; simulate operator clearing while only `played` would match a filter; assert **both** statuses deleted (FR-011).

### Implementation for US3

- [X] T018 [US3] Implement `clear_history(db)` in `backend/app/services/queue_service.py` — `DELETE` rows where `status IN TERMINAL_STATUSES`; `commit`; `bump_revision`.
- [X] T019 [US3] Add `DELETE /api/queue/history` (204) in `backend/app/routers/queue.py` calling `clear_history`.
- [X] T020 [US3] Add `clearHistory(): Observable<void>` in `frontend/src/app/services/queue-admin.service.ts` → `DELETE ${baseUrl}/queue/history`.
- [X] T021 [US3] Add «Vaciar historial» button (disabled when `historyTotalAll === 0`), confirm modal (Cancelar/Confirmar, same pattern as re-encolar), and `clearHistory()` handler in `frontend/src/app/admin/admin.component.ts` and `frontend/src/app/admin/admin.component.html`.
- [X] T022 [US3] On successful clear: reset `historyEntries`, `historyTotal`, `historyPage`, `historyTotalAll` in `frontend/src/app/admin/admin.component.ts`; participant updates via existing SSE `state` → `refreshSubmissions()` (T008 covers Admin cross-tab).

**Checkpoint**: US3 tests green (T014–T017); quickstart Phases 3–4 pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation, contracts finalization, build.

- [X] T023 [P] Run `pytest backend/tests/test_queue_history.py -k clear`, `npm --prefix frontend test -- --include='**/collapsible-section*' --include='**/participate.component.spec.ts'`, and `npm --prefix frontend run build`.
- [ ] T024 Execute manual validation per `specs/021-collapsible-panels-reset/quickstart.md` (Phases 1–6, including 2b mobile keyboard and multi-tab Admin) — **explicit constitution V coverage for US1/US2 UI**.
- [X] T025 [P] Set change `021-collapsible-panels-reset` to `status: implemented` in `specs/manifest.yml`; finalize merged contract sections in `specs/contracts/backend-api/contract.md` and `specs/contracts/app-core/contract.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks US1 and US2 UI**.
- **US1 (Phase 3)** and **US2 (Phase 4)**: Depend on T003–T004; **independent of each other**.
- **US3 (Phase 5)**: Backend T014–T019 after Phase 1; Admin UI T021–T022 best after T006–T007 (Historial panel).
- **Polish (Phase 6)**: After desired user stories complete.

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 | T003–T004 | Admin panels + badges + SSE history refresh |
| US2 | T003–T004 | Participate layout only |
| US3 | Phase 1 | API + Historial button (integrates with US1 Historial) |

### Parallel Opportunities

- **Phase 1**: T001 ∥ T002
- **Phase 2**: T004 ∥ (wait for T003)
- **After T004**: US1 (T005–T009) ∥ US2 (T010–T013)
- **US3 tests**: T014 ∥ T015 ∥ T016 ∥ T017
- **US3 backend**: T018–T019 parallel to US1/US2 frontend after tests written
- **Polish**: T023 ∥ T025

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 → Phase 2 → Phase 3 (T005–T009)
2. **STOP and VALIDATE** quickstart Phases 1 and 6

### Incremental Delivery

1. Setup + Foundational
2. US1 → US2 → US3 → Polish (T024 manual)

---

## Notes

- **`historyTotalAll`** (unfiltered) vs **`historyTotal`** (filtered pagination) — do not conflate (FR-013).
- Vaciar historial uses **modal** confirm, not `window.confirm`.
- Panel state is **in-memory only**; reload resets defaults.
- No Alembic migration for this feature.

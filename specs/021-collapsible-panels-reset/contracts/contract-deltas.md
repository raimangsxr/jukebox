# Contract Deltas: 021-collapsible-panels-reset

**Status**: merged into active contracts (2026-08-04).

Modifies: `backend-api`, `app-core`. Unless **changed** or **new**, prior contract behavior is unchanged.

---

## backend-api

### Clear queue history (new)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| DELETE | `/api/queue/history` | operator session | **204 No Content** |

**Behavior**:

- Permanently deletes **all** `queue_entries` with status `played` or `rejected`.
- Does **not** delete `pending_review`, `queued`, `playing`, or filler reserve rows.
- Ignores any UI filter state (always full history wipe).
- Associated `votes` rows removed via FK `ON DELETE CASCADE`.
- On success: `bump_revision`, SSE `state` event (participants refresh submissions via existing client logic).

| Case | Status | `detail` |
|------|--------|----------|
| Not authenticated | 401 | `not authenticated` |
| Participant session (no operator) | 401 | `not authenticated` |
| Success (≥0 rows deleted) | 204 | — |

Idempotent: empty history → 204.

### History (unchanged endpoints)

`GET /api/queue/history` and `POST /api/queue/history/{id}/requeue` behavior unchanged.

---

## app-core

### Shared collapsible section (new)

Standalone component `CollapsibleSectionComponent`:

- Inputs: `title`, `expanded`, optional `badge` (string shown in header when collapsed or always).
- Output: `expandedChange` on header toggle.
- Header: keyboard-focusable button, `aria-expanded`, `aria-controls` linked to content region.
- Visual: chevron icon en cabecera que **rota ~90°** cuando `expanded=true`; transición CSS opcional; contraste suficiente en tema oscuro.

### Admin (`/admin`) — changed layout

**Collapsible panels** (default expanded noted):

| Section | Default | Header badge |
|---------|---------|--------------|
| Moderación | expanded | `{n} pendiente(s)` |
| Historial | collapsed | `{historyTotalAll} entrada(s)` — **sin** filtro de estado |
| Reserva de relleno | collapsed | — |
| Uso de API Keys | collapsed | — |
| Evento | collapsed | — |
| Tokens de iframe | collapsed | — |

- Live status bar and logout header remain **outside** panels.
- New pending submissions while Moderación collapsed: update badge only; **do not** auto-expand (clarification).
- On SSE `state` event: refresh `pending()` **and** `historyTotalAll` + paginated history list (keeps multi-tab Admin in sync).
- **Historial**: button «Vaciar historial»; disabled when `historyTotalAll === 0`; confirm modal (Cancelar / Confirmar) before `DELETE /api/queue/history`; refresh list, `historyTotalAll`, and pagination after success.

### Participate (`/participar`) — changed layout

Authenticated main view order (top → bottom):

1. Header + live status (unchanged)
2. **Sonando ahora** — fixed strip, visible only when `now_playing`; **not** inside a collapsible panel
3. Panel **Cola votable** — default expanded
4. Panel **Enviar canciones** — search + paste URL + «Enviar canción»; default collapsed
5. Panel **Mis canciones** — default collapsed

Panels toggle independently (not exclusive accordion).

Onboarding and login sections unchanged (not collapsible).

### Services

- `QueueAdminService.clearHistory(): Observable<void>` → `DELETE /api/queue/history`

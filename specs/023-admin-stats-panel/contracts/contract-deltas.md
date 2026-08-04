# Contract Deltas: 023-admin-stats-panel

**Status**: merged at implement (023-admin-stats-panel).

Modifies: `backend-api`, `app-core`. Unless **changed** or **new**, prior contract behavior is unchanged.

---

## backend-api

### `GET /api/admin/stats` (**new**)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/admin/stats` | operator session | 200 `AdminStatsResponse` |

Participant session → 401 `not authenticated`.

**Refresh semantics**: On-demand only (client calls on panel expand or manual refresh). No SSE payload for stats.

### `AdminStatsResponse` (**new**)

| Field | Type | Description |
|-------|------|-------------|
| `participants_active_count` | int | Unique participants with ≥1 submission or ≥1 vote |
| `total_submissions` | int | Participant-attributed queue entries (all statuses) |
| `total_votes_cast` | int | Total vote rows |
| `distinct_voted_songs_count` | int | Distinct YouTube videos with ≥1 vote (aggregated) |
| `queue_counts` | `QueueStatusCounts` | Per-status entry counts |
| `top_submitters` | `ParticipantRankingItem[]` | ≤10, by submission count DESC |
| `top_voters` | `ParticipantRankingItem[]` | ≤10, by votes cast DESC |
| `top_songs` | `SongRankingItem[]` | ≤10, by aggregated votes DESC |

### `QueueStatusCounts` (**new**)

| Field | Type |
|-------|------|
| `pending_review` | int |
| `queued` | int |
| `playing` | int |
| `played` | int |
| `rejected` | int |

### `ParticipantRankingItem` (**new**)

| Field | Type |
|-------|------|
| `participant_id` | string |
| `display_name` | string | `display_name`, else email local-part, else `«Participante»` |
| `count` | int |

### `SongRankingItem` (**new**)

| Field | Type |
|-------|------|
| `youtube_video_id` | string |
| `title` | string |
| `vote_count` | int |

**Tie-break**: at most 10 rows; ties at rank 10 broken alphabetically by `display_name` or `title`.

**Post-clear-history**: aggregates reflect surviving rows only.

---

## app-core

### Admin `/admin` — Estadísticas panel (**new**)

- Collapsible section **Estadísticas**, **collapsed by default**, positioned **after Historial** and before Reserva de relleno.
- No badge on collapsed header.
- On **expand**: `GET /api/admin/stats` (loading + error states).
- **Actualizar** button while expanded re-fetches stats.
- **No** auto-refresh via SSE or polling while panel stays open.

**Layout sections** (Spanish), top to bottom:
1. Resumen (totales + participantes activos)
2. Estado de cola (5 contadores)
3. Top 10 — Más canciones enviadas
4. Top 10 — Más votos emitidos
5. Top 10 — Canciones más votadas

Mobile (SC-002): full v1 visible within **≤2 viewport heights** on a standard phone.

Empty rankings: explicit «Sin datos aún» (or equivalent).

### Services (**new**)

- `AdminStatsService` (or `QueueAdminService.getStats()`) — `GET /api/admin/stats`

### Out of scope

- Export CSV / charts
- Stats on kiosk or `/participar`
- Persisted snapshot between events

---

## ops-platform

No compose/K8s changes.

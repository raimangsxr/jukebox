# Research: 004-kiosk-display-queue

**Date**: 2026-07-18

## Decision: Display layout proportions

**Decision**: CSS flex column on kiosk root — top region `flex: 1 1 90%` (min-height 0), queue strip `flex: 0 0 10%` (clamp 8–12% via `min-height`/`max-height` on 720px baseline). Top row uses CSS grid `grid-template-columns: 2fr 1fr`.

**Rationale**: Matches clarified spec (~10% queue strip); avoids brittle pixel math while SC-001 remains testable at 720px.

**Alternatives considered**:
- Keep 001 three-row grid with full-width panel C — rejected per clarify session
- Fixed `72px` strip — rejected; percentage scales better across embed heights

## Decision: State snapshot + SSE revision

**Decision**: `GET /api/state` returns full kiosk snapshot (`revision`, `now_playing`, `queue`, `event_config` subset). `GET /api/events/stream` emits SSE `state` events when `jukebox_runtime.revision` increments. Display loads snapshot first, then subscribes via `EventSource` with credentials.

**Rationale**: Matches bull sibling pattern (`GET /api/state` + SSE); single payload keeps player, QR, and strip in sync; revision dedupes redundant renders.

**Alternatives considered**:
- Polling every N seconds — rejected; spec requires server-push (FR-P03)
- Separate SSE channels per panel — rejected; unnecessary complexity for v1

## Decision: Queue ordering and positions

**Decision**: `queued` entries ordered by `vote_count DESC`, `created_at ASC`. `position` is 1-based among `queued` only, recomputed on approve, vote change (future), and skip. At most one `playing` entry referenced by `jukebox_runtime.now_playing_entry_id`.

**Rationale**: Product rules from 001 baseline; denormalized `vote_count` on `queue_entries` avoids join hot path on display.

**Alternatives considered**:
- FIFO only — rejected; contradicts FR-P05 popularity ordering

## Decision: YouTube metadata enrichment

**Decision**: On create/approve paths that receive a `youtube_video_id`, backend fetches public oEmbed (`https://www.youtube.com/oembed?url=...&format=json`) to populate `title` and `thumbnail_url`. Failures store video id + fallback title `"Video de YouTube"`.

**Rationale**: No YouTube Data API key required for v1; sufficient for display and admin preview context.

**Alternatives considered**:
- Require client-sent title — rejected for test seeds; operator-only dev submit still benefits from server fetch
- YouTube Data API search — deferred to v1.1 per 001

## Decision: Test submissions without participant OAuth

**Decision**: No public submit endpoint in 004. Tests and quickstart use pytest fixtures / `POST /api/queue/dev-submit` when `JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT=true` (default false) or pytest client direct DB inserts. Production OpenAPI omits dev route.

**Rationale**: Spec defers participant submit to 006; moderators still need seeded `pending_review` rows for validation.

**Alternatives considered**:
- Operator UI to paste YouTube URL in admin — useful but out of minimal scope; quickstart uses dev-submit or fixtures only

## Decision: YouTube player (frontend)

**Decision**: Load YouTube IFrame API script; standalone `YoutubePlayerComponent` wraps player with `videoId` input, `onStateChange` for ended → optional callback (skip/advance handled server-side via moderator skip in 004; natural end can call `POST /api/queue/advance` in later polish or same change).

**Rationale**: Standard embed approach; sibling bull uses iframe protocol — player is self-contained in jukebox SPA.

**Note for implementation**: Natural video end advancing queue is in scope via FR-008 skip; auto-advance on `ENDED` event should call backend advance endpoint (same as skip semantics for next track) — include in tasks.

**Alternatives considered**:
- Raw `<iframe src="...">` only — rejected; ENDED events need IFrame API

## Decision: QR generation

**Decision**: `qrcode` (or `angularx-qrcode`) generates SVG/PNG for `window.location.origin + '/participar'`. Panel shows `event_config.name`, `subtitle`, and short Spanish instructions.

**Rationale**: Lightweight; no server round-trip for QR bitmap.

## Decision: SSE auth

**Decision**: SSE endpoint requires `get_current_user` (embed-established `jukebox_session`). Browser `EventSource` sends cookies on same origin. On 401, display sets `session_expired` via existing interceptor pattern if initial snapshot fails; SSE reconnect with exponential backoff (1s → 30s cap).

**Rationale**: Consistent with FR-010; kiosk already has operator session from embed token.

## Decision: Alembic 0003

**Decision**: Single migration adding `queue_entries`, `jukebox_runtime` (singleton id=1), enum/type for `queue_entry_status`.

**Rationale**: Atomic schema for queue feature; `participants` table deferred until 006 — `submitted_by_participant_id` nullable UUID without FK constraint in 004 or FK optional with no table yet — use nullable column without FK until 006.

## Decision: Admin moderation UI

**Decision**: Add "Moderación" section to existing `AdminComponent` (tabs or stacked sections below tokens): pending list, approve/reject, skip now playing, YouTube preview link per FR-012.

**Rationale**: Matches 002 pattern (tokens in admin, no new route); keeps operator surface consolidated.

## Decision: Skip / advance (idle start)

**Decision**: `POST /api/queue/skip` handles both skip and start: if `playing`, advance to next `queued`; if idle with `queued`, promote top entry to `playing`; 409 only when idle and queue empty.

**Rationale**: Resolves first-playback gap without a separate endpoint; moderator uses **Iniciar reproducción** in admin (same API call).

**Alternatives considered**:
- Auto-play on first approve — rejected; keeps approve semantics (`queued` only) cleaner
- Separate `POST /api/queue/start` — rejected; redundant with idle skip

## Open questions

None blocking — layout, SSE, and scope resolved in spec clarify session 2026-07-18.

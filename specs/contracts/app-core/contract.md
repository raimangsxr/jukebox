# app-core Contract

Status: active. Consolidated from changes **001-foundation-jukebox**, **002-operator-auth-embed-tokens**, **004-kiosk-display-queue**, **005-participant-voting**, **006-participant-oauth-submit**, **007-participant-notifications**, **008-youtube-text-search**, **009-admin-api-key-usage**, **010-hardening-and-polish**, **014-youtube-player-autostart** (2026-07-30).

## Purpose

Angular 22 standalone SPA for amrn-jukebox: kiosk display, mobile participation, and operator admin. Spanish UI (`lang="es"`). Follows amrn-bull responsive and iframe conventions.

## Stack

- Angular 22, TailwindCSS, RxJS, TypeScript ~6.0
- `bootstrapApplication` with `provideRouter`, `provideHttpClient(withInterceptors)`, `provideAnimations`
- Build: `@angular/build:application` → `dist/amrn-jukebox/browser/`
- QR: `qrcode` npm package
- YouTube: IFrame API (dynamic script load)

## Routes

| Path | Component | Guard | Notes |
|------|-----------|-------|-------|
| `/` | `DisplayComponent` | `displayGuard` | Kiosk display; embed `?token=` bootstrap |
| `/participar` | `ParticipateComponent` | none | Google OAuth, submit, vote, Mis canciones |
| `/login` | `LoginComponent` | `guestGuard` | Operator login; authed → `/admin` |
| `/admin` | `AdminComponent` | `authGuard` | Moderation + tokens + logout |
| `**` | redirect → `/` | | |

## AuthService

- `bootstrap()` — strips `?token=`, exchanges via `POST /api/auth/token` or calls `/me`
- `login`, `logout`, `me`, `exchangeToken`
- `displayError`: `'token_invalid' | 'session_expired' | null` for kiosk display UX

## Guards

| Guard | Behavior |
|-------|----------|
| `authGuard` | Unauthed → `/login?returnUrl=…` |
| `guestGuard` | Authed → `/admin` |
| `displayGuard` | Authed or `displayError` → allow `/`; unauthed → `/login` |

## Display error states (kiosk)

| Trigger | UI on `/` | Redirect `/login` |
|---------|-----------|-------------------|
| Invalid/revoked `?token=` | `"Token inválido o revocado"` | No |
| 401 on protected API while on `/` | `"Sesión caducada"` | No |
| Unauthenticated, no `?token=` | — | Yes |

## authInterceptor

- All requests: `withCredentials: true`
- 401 on `/` (display): set `displayError = 'session_expired'`; no navigation
- 401 on `/participar` for `/api/participant/*` or `/api/votes`: no `/login` redirect (handled in component)
- 401 elsewhere: `logout()` + navigate `/login`
- Exempt: `/api/auth/login`, `/api/auth/me`, `/api/auth/token`, `/api/participant/dev-auth`, `/api/participant/me`

## Display layout (004)

| Region | Size | Component |
|--------|------|-----------|
| Top row | ~90% height | Grid 2fr / 1fr |
| Player panel | 2/3 top width | `YoutubePlayerComponent` |
| QR panel | 1/3 top width | `QrPanelComponent` |
| Queue strip | ~10% height, full width | `QueueStripComponent` |

CSS variable `--jukebox-app-height` from `event_config.app_height_px` (default 720). Error panel from 002 replaces entire layout when `displayError` set.

## Display services (004)

- `DisplayStateService` — `GET /api/state`, SSE `/api/events/stream`, `state$`, `apiKeyUsage$`, `playbackStatus$`, `advancePlayback()`, `reportPlaybackStatus()`
- Child components: `YoutubePlayerComponent`, `QrPanelComponent`, `QueueStripComponent`

### YoutubePlayerComponent (014, 015)

- Loads YouTube IFrame API; creates player when `videoId` is set.
- On load, probes browser autoplay-with-sound capability (`detectAutoplayWithSound`); caches result in `sessionStorage` key `jukebox.autoplayCapable`.
- When autoplay with sound is allowed (kiosk Chromium flags / PWA), `playerVars` use `mute: 0` and no overlay.
- Otherwise `mute: 1` with overlay **Activar sonido**; tap calls `unMute()` + `playVideo()` inside user gesture; `sessionStorage` key `jukebox.playerActivated` persists manual unlock.
- `playerVars`: `autoplay: 1`, `playsinline: 1`, `rel: 0`, `modestbranding: 1`; `mute` per capability above.
- On sound activation, if queue non-empty and idle, calls `advancePlayback()` to promote top queued entry.
- Retries `playVideo()` when player remains `CUED` or `PAUSED` after load.
- Reports kiosk audio health to backend via `POST /api/display/playback-status` (`idle` | `sound` | `muted`).

## Admin UI

### Tokens + logout (002)

- Logout button (clears session → `/login`)
- Tokens panel: list, create (label), revoke, copy-once plaintext

### Moderación (004, 013)

- Pending review table with approve/reject
- **Modo de cola** selector above pending table: **Moderado** / **Libre** (Spanish labels); in-app confirmation dialog before `PUT /api/event-config/queue-mode`; when **Libre**, info message that new submissions skip review (legacy pendings may remain)
- **Iniciar reproducción** when idle + queued; **Saltar canción** when playing
- Playback status line: **Sonando con audio: {title}** / **Sonando sin audio: {title}** when `now_playing` (from SSE `playback_status`); **Cola lista — {n} canciones en espera** when idle + queued; idle empty message otherwise
- When `playback_status.audio_mode` is `muted` while playing, show amber hint to check kiosk Chromium autoplay policy or parent iframe `allow="autoplay"`
- YouTube preview opens `https://www.youtube.com/watch?v={id}` in new tab
- Spanish error messages for queue conflicts

### Uso de API Keys (009)

- Section between **Moderación** and **Evento**
- Table: Clave (label + masked suffix), Usados, Restantes, Límite (100), Estado (Activa/Agotada)
- Global label: **Próximo reinicio:** formatted `next_reset_at` (Pacific)
- Empty state: `No hay API keys de YouTube configuradas.`
- Initial load: `GET /api/youtube/api-keys/usage`
- Live updates: SSE `api_key_usage` via `DisplayStateService.apiKeyUsage$` (no polling)

## Bootstrap

`AppComponent` calls `AuthService.bootstrap()` on init.

## Environment

- Dev: `apiBaseUrl: 'http://localhost:8000/api'`, `allowDevParticipantAuth: true`
- Prod: `apiBaseUrl: '/api'`, `allowDevParticipantAuth: false`

## Styling

- TailwindCSS with `jukebox-*` color tokens
- Dark background (`#0f172a`), accent purple (`#a855f7`)

## Participate submit UX (006 + 008)

Dual first-class submit paths on `/participar`:

| Rule | Value |
|------|-------|
| Layout | Stacked: **search block above URL block**; both always visible |
| Search trigger | **Buscar** + **Enter**; no auto-search while typing |
| Result row | Title + thumbnail + channel; tap selects (highlight) |
| Active path | Last interaction: row select → search; URL text edit → URL; **focus alone does not switch** |
| Active section | Visual highlight (border/background) |
| Submit button | **Single** **Enviar canción** — **sticky footer** at viewport bottom |
| Search disabled | Section visible, controls disabled, Spanish message when `config.enabled=false` |
| URL path | Unchanged 006 when `activePath='url'` |

Spanish search strings: see change 008 contract deltas (`search_heading`, `search_disabled`, `search_empty`, `search_rate_limit`, `search_unavailable`, `query_too_short`).

## Participate UI (005 + 006 + 008)

- Unauthenticated: **Iniciar sesión con Google**; vote/submit/search disabled; dev button hidden unless `environment.allowDevParticipantAuth` or `?dev=1`
- Authenticated header: display name, avatar, votes remaining
- **Search** (when enabled): query + **Buscar**; results list; select row + sticky **Enviar canción**
- **URL submit**: paste link; same sticky **Enviar canción** (dual path)
- Spanish errors mapped from API `detail` (`mapSubmitError`, `mapSearchError`)
- **Mis canciones**: status badges (Pendiente de revisión, En cola, Sonando, Reproducida, Rechazada) + rejection reason; refreshes on SSE revision
- Cola votable: unchanged from 005
- `ParticipantService` — `startGoogleLogin()`, `parseOAuthReturnQuery()`, `getSearchConfig()`, `searchYoutube()`, `submitSong(url, searchQuery?)`, `getSubmissions()`, `mapSubmitError()`, `mapSearchError()`, `loadMe()`, `castVote()`, `devAuth()`
- `ParticipantStateService` — `GET /api/participant/state`, `refreshSubmissions()`, SSE `/api/events/stream` (`state` + `notification`), preserves `votes_remaining` on SSE merge; forwards `notification` to toast service when `participant_id` matches session
- `NotificationToastService` — FIFO toast queue, dedupe `type:queue_entry_id`, 8s auto-dismiss, manual dismiss, Spanish copy
- `NotificationToastComponent` — fixed bottom toast on `/participar` (authenticated only)

### Notification toast UX (007)

| Rule | Value |
|------|-------|
| Position | Fixed bottom (safe area) |
| Queue | FIFO, one visible |
| Auto-dismiss | 8 seconds |
| Manual dismiss | Always available |
| Dedupe | `type:queue_entry_id` per page session |
| Retroactive | None |

| `type` | Spanish template |
|--------|------------------|
| `song.approved` | «{title}» ha sido aprobada y está en cola. |
| `song.up_next` | «{title}» es la siguiente canción. |

Kiosk `/` (`DisplayStateService`) ignores `notification` SSE events.

## Deferred (kiosk iframe protocol)

- `bull:config`, `bull:resize`, `bull:ping` postMessage — dedicated kiosk-screen change

## Hardening & polish (010)

- **Evento editor**: the admin "Evento" section is an editable Spanish form (Nombre, Subtítulo, Altura del display, Tema, Canciones visibles) bound to `GET/PUT /api/event-config` via `EventConfigService`; validation and success feedback. Replaces the previous "próximamente" placeholder.
- **Theme**: `event_config.theme` is applied to the document root (`data-theme`) on kiosk and `/participar` via `theme.util`; only `dark` is supported, unknown values fall back to `dark`.
- **Kiosk layout**: responsive shell — `app_height_px` is a target (`min(100dvh, …)`), not a hard clip; renders 720p–4K without clipping.
- **Moderation**: per-row busy state (acting on one pending entry does not disable the others); playback buttons use a separate flag.
- **QR**: regenerated only when the participation URL changes.
- **Routing**: unknown routes render a Spanish `NotFoundComponent` (was a silent redirect to `/`).
- **Dependencies**: unused `@angular/material` and `@angular/cdk` removed.
- **Dev affordances**: `AuthService.resetForTesting()` is a no-op in production builds.
- **Tests**: vitest specs for the three guards, the auth interceptor's 401 branching, theme util, and `EventConfigService` (including `updateQueueMode`).

## Queue approval mode (013)

- Admin **Moderación**: mode selector + confirm dialog; Libre informational banner; bound to `GET/PUT /api/event-config/queue-mode` via `EventConfigService.updateQueueMode`
- `/participar`: no mode indicator; submit response `status` reflects mode (`pending_review` vs `queued`); free submit triggers existing `song.approved` toast via SSE

## Participant limits UX (016)

### Live connection status

- `LiveStatusComponent` — fixed top-right badge on `/`, `/admin`, authenticated `/participar` (post-rules)
- States: hidden when SSE connected; **Reconectando…** during reconnect; **Modo respaldo** during polling fallback (single label, no overlap)
- `LiveConnectionManager` shared by `DisplayStateService` and `ParticipantStateService`; `connectionStatus$` observable

### Admin moderation mobile

- Pending table on `md+`; card layout below `md` with title, duration, submitter, preview link, reject reason, approve/reject buttons
- `.admin-main { overflow-x: hidden }`

### Participant rules onboarding

- After auth, if `sessionStorage` lacks `jukebox.participantRulesAccepted`, show **Normas de participación** with limits from `GET /api/participant/state` (`max_pending_submissions`, `max_searches_10_minutes`, `max_votes_10_minutes`)
- **Entendido, participar** sets session flag and starts full participate UI + SSE
- `votesRemainingLabel` uses dynamic `max_votes_10_minutes` (10-minute window)

## Admin queue history and filler reserve (017)

### Admin `/admin`

- **Historial**: paginated played/rejected list with status filter; re-encolar with confirm; 409 handling
- **Reserva de relleno**: ordered reserve list, add URL, reorder (↑↓), enqueue to active queue, delete, **Añadir directo a cola** (`operator-submit`), **Exportar CSV** / **Importar CSV** (validate → shared preview modal → confirm → append), **Añadir playlist** (URL input → validate → shared preview modal → confirm → append), **Vaciar** (confirm → `DELETE /api/filler-reserve`)
- **Inyección automática** toggle bound to `PUT /api/event-config/filler-auto-inject`
- Services: `QueueAdminService` (`getHistory`, `requeue`, `operatorSubmit`), `FillerReserveService`, `EventConfigService.updateFillerAutoInject`

### Participar / kiosk

- No historial or reserve UI; filler songs in queue are votable with no visual distinction; order from server SSE `state`

## Change history

- **001-foundation-jukebox** — Angular scaffold, four routes, placeholder layouts
- **002-operator-auth-embed-tokens** — AuthService, guards, interceptor, login, tokens panel, display errors
- **004-kiosk-display-queue** — functional kiosk display, queue strip, QR, SSE, admin moderation
- **005-participant-voting** — `/participar` vote UI, ParticipantService, ParticipantStateService
- **006-participant-oauth-submit** — Google OAuth, submit form, Mis canciones
- **007-participant-notifications** — in-app notification toasts on `/participar`
- **008-youtube-text-search** — YouTube text search UI, dual-path submit, sticky footer
- **009-admin-api-key-usage** — Admin per-key YouTube API usage table with SSE updates
- **010-hardening-and-polish** — editable Evento config + theme, responsive kiosk, per-row moderation, QR caching, 404 page, dead-dep removal, guard/interceptor/service tests
- **013-queue-approval-mode** — queue mode selector in Moderación (Moderado/Libre), confirm before mode change, free-mode direct enqueue UX
- **016-participant-limits-ux** — live connection badge, admin mobile moderation cards, participant rules screen, ENV-driven search/vote limits
- **017-admin-queue-history-filler** — admin Historial + Reserva de relleno sections, filler auto-inject toggle, queue-admin/filler-reserve services
- **018-filler-reserve-csv** — Exportar CSV / Importar CSV on Reserva de relleno; import preview modal with line errors; `exportCsv`, `validateImport`, `importReserve` on `FillerReserveService`
- **019-filler-reserve-playlist** — shared batch preview modal (`add_count`, `skipped_*`); CSV append; playlist URL + **Añadir playlist**; **Vaciar** with confirm; `validatePlaylist`, `addPlaylist`, `clearReserve` on `FillerReserveService`

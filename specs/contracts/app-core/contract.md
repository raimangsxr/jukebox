# app-core Contract

Status: active. Consolidated from changes **001-foundation-jukebox**, **002-operator-auth-embed-tokens**, **004-kiosk-display-queue**, **005-participant-voting**, **006-participant-oauth-submit**, **007-participant-notifications**, **008-youtube-text-search** (2026-07-18).

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

- `DisplayStateService` — `GET /api/state`, SSE `/api/events/stream`, `state$`, `advancePlayback()`
- Child components: `YoutubePlayerComponent`, `QrPanelComponent`, `QueueStripComponent`

## Admin UI

### Tokens + logout (002)

- Logout button (clears session → `/login`)
- Tokens panel: list, create (label), revoke, copy-once plaintext

### Moderación (004)

- Pending review table with approve/reject
- **Iniciar reproducción** when idle + queued; **Saltar canción** when playing
- YouTube preview opens `https://www.youtube.com/watch?v={id}` in new tab
- Spanish error messages for queue conflicts

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

## Change history

- **001-foundation-jukebox** — Angular scaffold, four routes, placeholder layouts
- **002-operator-auth-embed-tokens** — AuthService, guards, interceptor, login, tokens panel, display errors
- **004-kiosk-display-queue** — functional kiosk display, queue strip, QR, SSE, admin moderation
- **005-participant-voting** — `/participar` vote UI, ParticipantService, ParticipantStateService
- **006-participant-oauth-submit** — Google OAuth, submit form, Mis canciones
- **007-participant-notifications** — in-app notification toasts on `/participar`
- **008-youtube-text-search** — YouTube text search UI, dual-path submit, sticky footer

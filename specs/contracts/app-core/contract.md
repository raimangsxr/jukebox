# app-core Contract

Status: active. Consolidated from changes **001-foundation-jukebox**, **002-operator-auth-embed-tokens** (2026-07-17).

## Purpose

Angular 22 standalone SPA for amrn-jukebox: kiosk display, mobile participation, and operator admin. Spanish UI (`lang="es"`). Follows amrn-bull responsive and iframe conventions.

## Stack

- Angular 22, TailwindCSS, RxJS, TypeScript ~6.0
- `bootstrapApplication` with `provideRouter`, `provideHttpClient(withInterceptors)`, `provideAnimations`
- Build: `@angular/build:application` → `dist/amrn-jukebox/browser/`

## Routes

| Path | Component | Guard | Notes |
|------|-----------|-------|-------|
| `/` | `DisplayComponent` | `displayGuard` | Kiosk display; embed `?token=` bootstrap |
| `/participar` | `ParticipateComponent` | none | Public participation |
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
- 401 elsewhere: `logout()` + navigate `/login`
- Exempt: `/api/auth/login`, `/api/auth/me`, `/api/auth/token`

## Admin UI (002)

- Logout button (clears session → `/login`)
- Tokens panel: list, create (label), revoke, copy-once plaintext

## Bootstrap

`AppComponent` calls `AuthService.bootstrap()` on init.

## Environment

- Dev: `apiBaseUrl: 'http://localhost:8000/api'`
- Prod: `apiBaseUrl: '/api'`

## Styling

- TailwindCSS with `jukebox-*` color tokens
- Dark background (`#0f172a`), accent purple (`#a855f7`)

## Planned (003+)

- Display: YouTube IFrame API, QR, SSE queue panel
- Iframe protocol: `bull:resize`, `bull:ping`, `bull:config`, `embed_app_height_px`
- `--jukebox-app-height` CSS variable from `event_config` + embed override
- Google OAuth UI on `/participar`

## Change history

- **001-foundation-jukebox** — Angular scaffold, four routes, placeholder layouts
- **002-operator-auth-embed-tokens** — AuthService, guards, interceptor, login, tokens panel, display errors

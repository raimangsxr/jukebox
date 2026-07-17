# Research: 002-operator-auth-embed-tokens

**Date**: 2026-07-17 (updated after clarify session)

## Decision: Mirror amrn-bull auth API surface

**Decision**: Reuse bull endpoint shapes under `/api/*` with `jukebox_session` cookie.

**Rationale**: Sibling apps share kiosk-screen embed patterns; operators already know bull token workflow.

**Alternatives considered**: Custom JWT bearer tokens — rejected; session cookies match bull and simplify iframe same-origin auth.

## Decision: Token storage

**Decision**: Bcrypt hash of plaintext in `api_tokens.token_hash`; `find_active_token` scans non-revoked rows (acceptable for handful of tokens).

**Alternatives**: SHA-256 index lookup — rejected for v1 to match bull.

## Decision: Route guards

| Route | Guard | Unauthenticated behavior |
|-------|-------|--------------------------|
| `/login` | `guestGuard` | Allow; authed → `/admin` |
| `/admin` | `authGuard` | Redirect `/login?returnUrl=…` |
| `/` | `displayGuard` | **US1 stub**: unauthed → `/login`. **US2**: embed bootstrap + static errors on token/session failure |
| `/participar` | none | Always public |

## Decision: Admin logout

**Decision**: Logout button ships in **US1** (`admin.component.ts`), not deferred to token-management US3.

**Rationale**: US1 acceptance scenario 3 requires logout from admin UI; tokens panel (US3) is independent.

## Decision: Login redirect

**Decision**: Successful login navigates to `returnUrl` query param if safe (same-origin path), else `/admin`.

**Rationale**: Moderator primary surface is admin; display uses embed token not password login.

## Decision: Kiosk display error UX (jukebox-specific)

**Decision**: On `/` only — failed embed token exchange shows `"Token inválido o revocado"`; expired session (401 on protected API) shows `"Sesión caducada"`. Neither case redirects to `/login`.

**Rationale**: Kiosk iframe must never expose operator credentials form (clarify Q7–Q8). amrn-bull redirects to `/login` on auth failure; jukebox display diverges intentionally.

**Implementation pattern**:
- `AuthService.displayError: 'token_invalid' | 'session_expired' | null`
- `displayGuard` allows `/` when `displayError` is set (component renders error panel)
- `authInterceptor` on 401: if `router.url === '/'` or navigating within display, set `session_expired` instead of `router.navigate(['/login'])`

**Alternatives considered**:
- Match bull (redirect `/login`) — rejected; bad kiosk UX
- Redirect only when not in iframe — rejected; harder to detect reliably; static error is simpler

## Decision: Users table

**Decision**: Reuse `users` from 001; migration 0002 adds only `api_tokens`.

## Decision: Token query parameter

**Decision**: `token` (same as amrn-bull / kiosk-screen).

## Decision: Embed token permissions

**Decision**: `POST /api/auth/token` sets identical `jukebox_session` as password login (full operator session).

## Open questions

None blocking — all resolved in clarify session 2026-07-17.

---
id: 009-admin-api-key-usage
type: change
status: implemented
modifies:
  - backend-api
  - app-core
depends_on:
  - 001-foundation-jukebox
  - 002-operator-auth-embed-tokens
  - 008-youtube-text-search
requires_contract_update: true
read_by_default: true
---

# Feature Specification: Admin YouTube API Key Usage

**Feature Branch**: `006-admin-api-key-usage` (git) | **Change id**: `009-admin-api-key-usage` | **Date**: 2026-07-19

**Created**: 2026-07-19

**Status**: Implemented

**Input**: Añadir en Admin la visualización del uso de cada API Key de YouTube configurada. Mostrar una lista con el consumo y lo restante de los 100 usos diarios por clave, trackeando el uso de cada una de forma exacta.

## Clarifications

### Session 2026-07-19

- Q: ¿Cuándo incrementar el contador si la petición a YouTube falla (red, cuota, clave inválida)? → A: **Siempre** que se envía una petición saliente atribuida a esa clave (conteo por intento), independientemente del resultado.
- Q: Si Google devuelve quota-exhausted antes de que el contador local llegue a 100, ¿qué muestra `used`? → A: **`used = 100`** y **`remaining = 0`** de inmediato; clave marcada como agotada.
- Q: ¿Dónde ubicar la visualización de uso en `/admin`? → A: **Nueva sección dedicada** "Uso de API Keys", separada de Moderación y Tokens.
- Q: ¿Mostrar cuándo se reinicia la cuota diaria? → A: **Sí**, indicación global del próximo reset a **medianoche Pacífico** en la sección.
- Q: ¿Cómo actualizar los datos de uso en pantalla? → A: **SSE** (Server-Sent Events) para reflejar cambios en tiempo real sin polling.

## SDD Context

- Depends on: **002-operator-auth-embed-tokens** (operator session on `/admin`)
- Depends on: **008-youtube-text-search** (YouTube Data API key pool, search, and metadata fetches)
- Modifies contracts: `backend-api`, `app-core`
- Product baseline: each YouTube Data API project key has a **daily quota of 100 uses** for jukebox operations (search and video metadata)

## Problem

Operators cannot see how much of each YouTube API key’s daily quota has been consumed. When search or metadata calls fail due to quota exhaustion, there is no visibility into which keys are depleted, how many uses remain, or when counts reset. This makes it hard to plan events, rotate keys, or diagnose participant-facing search errors.

## Goals

- Operators with an active admin session can see **all configured YouTube API keys** and each key’s **exact daily usage** (consumed vs remaining out of 100).
- The system **increments usage precisely** every time a configured key is used for an outbound YouTube Data API request attributed to the pool (participant search and video metadata on submit).
- Usage counts **reset once per calendar day** on the same schedule already used for quota exhaustion (Pacific time), so displayed numbers match operational expectations from change 008.
- **No API key secrets** are exposed in the admin UI or to unauthenticated clients.

## Non-Goals

- Creating, editing, or deleting API keys from the admin UI (keys remain deployment configuration).
- Historical usage reports beyond the **current quota day**.
- Changing round-robin or failover behavior of the key pool (008 unchanged except for counting).
- HTTP polling for usage updates (SSE is required instead).
- Participant-visible usage or quota UI on `/participar`.
- Billing or Google Cloud Console integration.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View daily usage per API key (Priority: P1)

As an operator on `/admin`, I want to see a list of all configured YouTube API keys with how many of the 100 daily uses each key has consumed and how many remain, so I can monitor quota before and during an event.

**Why this priority**: Core value of the feature — without this list, operators gain no new capability.

**Independent Test**: Sign in as operator → open the new usage section → verify each configured key appears with `used`, `remaining`, and `daily_limit` (100) matching backend state.

**Acceptance Scenarios**:

1. **Given** three API keys are configured and key A has been used 12 times today while keys B and C have 0 uses, **When** I open the **Uso de API Keys** section in `/admin`, **Then** I see three entries with used counts 12, 0, and 0 and remaining counts 88, 100, and 100 respectively.
2. **Given** I am not signed in as an operator, **When** I try to access usage information, **Then** I am denied (same protection as other admin APIs).
3. **Given** keys are configured, **When** I view the list, **Then** each row shows a **masked identifier** (e.g. position label and/or last four characters) and **never** the full secret key, and the section shows **when the daily quota resets** (Pacific midnight).

---

### User Story 2 - Usage updates after API activity (Priority: P1)

As an operator, I want usage numbers to **update in real time** when API activity occurs so I can trust the dashboard during a live event without manual refresh or polling.

**Why this priority**: “Exact tracking” is a stated requirement; stale counts or polling would not meet the goal during active events.

**Independent Test**: Open `/admin` with usage section visible → trigger a participant search → verify the count for the key that served the request increases by exactly one **via SSE** without page reload.

**Acceptance Scenarios**:

1. **Given** a key has 40 uses today and I have the **Uso de API Keys** section open, **When** a participant search sends an outbound request with that key, **Then** the used count updates to 41 and remaining to 59 **via SSE without manual refresh**.
2. **Given** a key has 99 uses today, **When** one more attributed API request completes, **Then** used shows 100, remaining shows 0, and the key is indicated as **quota exhausted** for the rest of the quota day (consistent with pool behavior).
3. **Given** a participant search fails due to network error **before** any key is selected, **When** I view usage, **Then** no key’s count increases.
4. **Given** a key is selected and an outbound YouTube API request is sent but returns an error (network timeout after send, quota exceeded, or invalid key), **When** I view usage, **Then** that key’s used count increased by exactly 1.
5. **Given** the backend process restarts, **When** I view usage, **Then** today’s counts are unchanged from before the restart.

---

### User Story 3 - Empty and edge states (Priority: P2)

As an operator, I want clear feedback when no keys exist or all keys are exhausted, so I know why search may be unavailable to participants.

**Why this priority**: Prevents confusion during setup and at quota exhaustion without blocking P1.

**Independent Test**: Unset keys → verify empty state; exhaust all keys → verify exhausted messaging.

**Acceptance Scenarios**:

1. **Given** no YouTube API keys are configured, **When** I open the **Uso de API Keys** section, **Then** I see a Spanish message that no keys are configured (no table rows).
2. **Given** all keys show 100/100 used, **When** I view the section, **Then** each key is marked exhausted and I can infer participant search will fail until the daily reset.
3. **Given** a key has 47 local uses but Google returns quota-exhausted on the next request, **When** I view the section, **Then** that key shows used 100, remaining 0, and status exhausted.
4. **Given** a new key is added to deployment configuration during the day, **When** I reload usage, **Then** the new key appears with used 0 and remaining 100.

---

### Edge Cases

- Key removed from configuration → it no longer appears in the list; its prior-day counts are not required in admin.
- Google returns quota-exhausted before local count reaches 100 → key is marked exhausted; displayed **`used` MUST be set to 100** and **`remaining` to 0** (may reflect external quota consumption outside jukebox).
- Concurrent searches across keys → each **attributed outbound request** increments exactly one key by one (no double-count or lost counts under normal load).
- Quota day boundary (Pacific midnight) → all keys reset to used 0 / remaining 100 without operator action.
- Submit metadata fetch and text search both consume quota → both increment the key that served the request.
- Outbound request sent but fails (any error response or timeout after send) → counter still increments by 1 for the attributed key.
- Failover retries another key → each key that sends an outbound request increments its own counter (e.g. quota error on key A then success on key B → A +1, B +1).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST maintain an **exact per-key daily usage counter** for every key listed in the YouTube API key configuration.
- **FR-002**: Each counter MUST increment by **exactly 1** when that key sends an **outbound YouTube Data API request** through the shared key pool (including participant text search and video metadata resolution on submit), **regardless of whether the request succeeds or fails** (attempt-based counting).
- **FR-003**: Counters MUST **not** increment when no outbound request is sent (e.g. validation failure, participant rate limit rejection before pool access, or pool has no available key).
- **FR-004**: The **daily limit** for display and exhaustion logic MUST be **100 uses per key per quota day**.
- **FR-005**: Quota day boundaries MUST align with the **Pacific timezone daily reset** already used for marking keys exhausted in change 008.
- **FR-006**: When a key’s used count reaches 100 **or** Google returns a quota-exhausted error for that key, the system MUST treat that key as **quota exhausted** for the remainder of the quota day; displayed **`used` MUST be 100** and **`remaining` MUST be 0**.
- **FR-007**: Usage counters MUST **persist across process restarts** so operators see accurate totals for the current quota day.
- **FR-008**: The system MUST expose usage data **only to authenticated operators** (same authorization model as other `/admin` moderation APIs).
- **FR-009**: The admin UI MUST show a dedicated **"Uso de API Keys"** section on `/admin` (separate from Moderación and Tokens) listing configured keys with, at minimum: masked identifier, uses consumed today, uses remaining today, and daily limit (100). The section MUST display a **global next reset indicator** for the Pacific-time quota day (e.g. reset at midnight Pacific).
- **FR-009a**: Usage counts in the admin UI MUST update in **real time via SSE** when any attributed API request changes per-key usage; the operator MUST NOT need to poll or manually refresh to see current counts while `/admin` is open.
- **FR-010**: The admin UI MUST use **Spanish** labels and messages consistent with the rest of `/admin`.
- **FR-011**: Full API key values MUST NOT be returned in any API response or rendered in the UI.
- **FR-012**: When no keys are configured, the admin UI MUST show an explanatory **Spanish empty state** instead of an error.
- **FR-013**: The backend MUST broadcast an `api_key_usage` SSE event on `/api/events/stream` whenever per-key usage changes (increment, exhaustion, or daily reset); `/admin` consumes it; kiosk and participant clients ignore unknown event types.
- **FR-014**: Existing participant search, URL submit, moderation, voting, and notification flows from changes 004–008 MUST continue to work (**regression**).

### Key Entities

- **API key usage record**: Per configured key for the current quota day — masked identifier, used count, remaining count (derived: `100 - used`, floored at 0), exhaustion flag, quota day identifier.
- **Quota day**: Calendar date in Pacific time that bounds when counters reset to zero.
- **Attributed API request**: A single outbound YouTube Data API call for which the pool selected a specific key and the request was sent (search or videos metadata); counts on attempt, not on success.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can view all configured keys and their used/remaining counts in **under 10 seconds** from opening the admin usage section (with a valid session); subsequent usage changes appear via SSE within **5 seconds** of the attributed API request.
- **SC-002**: **100%** of attributed YouTube Data API requests in automated tests increment exactly one key’s counter by 1.
- **SC-003**: After a backend restart during the same quota day, displayed counts match pre-restart values (**100%** in persistence tests).
- **SC-004**: At Pacific midnight boundary tests, all keys reset to 0 used / 100 remaining (**100%** in time-boundary tests).
- **SC-005**: Unauthenticated or participant sessions cannot read usage data (**100%** authorization test pass).
- **SC-006**: No full API key material appears in admin UI or operator API payloads (**100%** inspection / automated assertion).
- **SC-007**: Core regression scenarios for 004–008 (moderation, search, URL submit, voting) pass without functional degradation.

## Assumptions

- The daily limit of **100 uses per key** matches the Google free-tier budget already assumed in change 008 for jukebox operations.
- Both **search** and **video metadata** requests count as one use each when they consume a key from the pool.
- Keys are identified in the UI by **stable order** in configuration (e.g. “Clave 1”, “Clave 2”) plus a masked suffix; operators map these to Google Cloud projects out of band.
- Usage visibility is **read-only**; key provisioning stays in ops/deployment (`JUKEBOX_YOUTUBE_API_KEYS`).
- A shared persistent store is available so concurrent requests do not corrupt counts and totals survive restarts.
- The **Uso de API Keys** section shows a single global **next reset** time aligned to Pacific midnight (same quota day as counters).
- Real-time updates reuse the **SSE pattern** already used elsewhere in jukebox (display queue, participant notifications); no HTTP polling for usage counts.

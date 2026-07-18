---
id: 008-youtube-text-search
type: change
status: implemented
modifies:
  - backend-api
  - app-core
depends_on:
  - 001-foundation-jukebox
  - 004-kiosk-display-queue
  - 005-participant-voting
  - 006-participant-oauth-submit
  - 007-participant-notifications
requires_contract_update: true
read_by_default: true
---

# Feature Specification: Participant YouTube Text Search

**Feature Branch**: `005-youtube-text-search` (git) | **Change id**: `008-youtube-text-search` | **Date**: 2026-07-18

**Created**: 2026-07-18

**Status**: Draft

**Input**: Búsqueda por texto de canciones en YouTube en `/participar` para que participantes encuentren y envíen canciones sin pegar URL o ID manualmente. Baseline producto 001 v1.1 (YouTube Data API). Mantiene envío por enlace de 006, moderación de 004, votación y notificaciones de 005–007.

## Clarifications

### Session 2026-07-18 (defaults from product baseline 001)

- Q: ¿Dónde aplica la búsqueda? → A: Solo en **`/participar`** para participantes autenticados; el moderador en `/admin` sigue con enlace de previsualización en nueva pestaña (sin búsqueda integrada en este cambio).
- Q: ¿Sustituye el campo de URL? → A: **No**; convive con el envío por enlace/ID de 006; el participante elige buscar o pegar enlace.
- Q: ¿Qué API? → A: **YouTube Data API** búsqueda de vídeos (`type=video`), alineado con baseline 001 v1.1.
- Q: ¿Aprobación automática? → A: **No**; el resultado seleccionado crea `pending_review` igual que un envío manual; moderación obligatoria (baseline FR-P02).
- Q: ¿Límites de envío? → A: Los mismos que 006 (2 `pending_review`, 1 activa `queued`+`playing`, sin duplicados activos).
- Q: ¿Idioma? → A: UI en **español**; errores API estables en inglés en backend con mapeo a español en frontend (patrón 006).
- Q: ¿Cómo se dispara la búsqueda? → A: Botón **Buscar** y tecla **Enter** en el campo; **sin** búsqueda automática mientras se escribe.
- Q: ¿Qué muestra cada resultado? → A: **Título + miniatura + canal** en cada fila (los tres obligatorios).
- Q: ¿Cómo se envía desde un resultado? → A: Tocar fila **selecciona** (resaltado); botón **Enviar canción** confirma el envío a `pending_review`.
- Q: ¿Límite de búsquedas por participante? → A: **10 búsquedas / 5 minutos** (ventana rodante); al superar, error en español y sin llamada a YouTube.
- Q: ¿UI sin API key de YouTube? → A: Mostrar sección de búsqueda **deshabilitada** con mensaje explicativo en español; envío por URL sigue activo.
- Q: ¿Coste y anuncios? → A: YouTube Data API **sin coste por llamada** dentro de cuota gratuita; la búsqueda **no muestra anuncios** (solo metadatos). La reproducción en kiosk (004) puede tener anuncios de YouTube en vídeos monetizados — independiente de este cambio.
- Q: ¿Varias API keys? → A: Pool de **4–5 API keys** (proyectos Google distintos); **round-robin** por búsqueda; si una key devuelve cuota agotada, **reintentar con la siguiente** de forma transparente; error al participante solo si **todas** las keys están agotadas.
- Q: ¿Búsqueda vs URL? → A: **Ambas opciones son válidas** y de primer nivel en `/participar`; el participante elige buscar **o** pegar enlace; ninguna reemplaza a la otra; mismos límites y moderación en ambos caminos.

### Session 2026-07-18 (clarify pass 2)

- Q: ¿URL y búsqueda activas a la vez? → A: **Un solo camino activo**; seleccionar resultado o editar el campo URL define cuál se envía; **un** botón **Enviar canción** para el camino activo.
- Q: ¿Cómo se indica el camino activo? → A: **Resaltar la sección activa** (borde/fondo en bloque búsqueda o URL según última interacción).
- Q: ¿Enfocar URL activa el camino? → A: **No**; solo edición de texto (escribir, pegar, borrar) activa el camino URL; el foco solo no cambia el camino activo.
- Q: ¿Disposición búsqueda y URL? → A: **Apilado** — bloque búsqueda arriba, bloque URL abajo; ambos siempre visibles.
- Q: ¿Posición de Enviar canción? → A: **Sticky al pie** — botón fijo en la parte inferior de la pantalla.

## SDD Context

- Depends on: **006-participant-oauth-submit** (OAuth, submit API, Mis canciones, límites)
- Depends on: **005-participant-voting**, **007-participant-notifications** (regresión en `/participar`)
- Depends on: **004-kiosk-display-queue** (`queue_entries`, moderación)
- Modifies contracts: `backend-api`, `app-core`
- Product baseline **001**: v1 URL/ID; **v1.1** búsqueda por texto vía YouTube Data API

## Problem

Participants who do not have a YouTube link handy must leave `/participar`, search elsewhere, and copy a URL — friction that slows submissions at live events. The product baseline promises text search in v1.1 so attendees can find songs by title or artist and submit in one flow.

## Goals

- Authenticated participants can submit songs via **two equivalent paths**: YouTube **text search** (select result + **Enviar canción**) or **URL/ID paste** (006).
- Both paths create `pending_review` entries under the same moderation and per-participant limits.
- Search does not replace URL submit; **both remain visible and usable** whenever the participant is signed in (search may be disabled only when no API keys are configured).
- **Zero monetary cost** target: use YouTube Data API free quotas only; no paid tier required for v1.
- **Quota resilience**: distribute searches across a pool of API keys with automatic failover before user-visible failure.
- Voting, Mis canciones, notifications, and moderator workflows from 004–007 remain unchanged.

## Non-Goals

- Web Push notifications (separate v1.1 item).
- YouTube search for operators in `/admin`.
- Replacing URL/ID paste submit.
- Audio preview or in-app YouTube playback on `/participar`.
- Playlist or channel submit (single video selection only).
- Changing vote limits, notification rules, or kiosk layout.
- Offline search or cached catalog without live API.
- Charging participants or operators for search (monetary billing is out of scope; API remains free-tier).
- Showing ads inside the `/participar` search UI (search returns metadata only).

## User Scenarios & Testing

### User Story 1 — Search and submit a song (Priority: P1)

As a signed-in participant on `/participar`, I search by song or artist name, pick a result, and submit it for moderator review without pasting a URL.

**Why this priority**: Core v1.1 value; removes the main friction after OAuth submit (006).

**Independent Test**: Sign in → enter search query → select a result → song appears in **Mis canciones** as **Pendiente de revisión**; moderator sees it in pending list.

**Acceptance Scenarios**:

1. **Given** I am signed in, **When** I enter a search query and tap **Buscar** or press **Enter**, **Then** I see a list of video results; each row shows **title**, **thumbnail**, and **channel name** (FR-005).
2. **Given** results are shown, **When** I tap a row to select it and tap **Enviar canción**, **Then** the entry is created in `pending_review` and **Mis canciones** updates.
3. **Given** I am not signed in, **When** I try to search, **Then** search is unavailable and I see the sign-in prompt (same as vote/submit).
4. **Given** I am signed in, **When** I view the submit area, **Then** I see **both** text search and URL paste as active options in a **stacked layout** (search block above URL block; both always visible), unless search is disabled for missing API keys.
5. **Given** I already pasted a URL in the submit field, **When** I use search instead, **Then** both paths remain available; only one submit action applies per intentional user action.
6. **Given** I have text in the URL field **and** a search result selected, **When** I tap **Enviar canción**, **Then** the system submits only the **active** path (last interaction: URL text edit → URL; result selection → search).
7. **Given** both submit paths are available, **When** I last interacted with search or URL, **Then** the **active** section (search block or URL block) is visually highlighted (e.g. border or background) so I know what **Enviar canción** will submit.
8. **Given** I am on `/participar`, **When** I scroll the page, **Then** **Enviar canción** remains visible as a **sticky footer** at the bottom of the screen.

---

### User Story 2 — Understand search results (Priority: P1)

As a participant, I can tell results apart before submitting so I pick the correct recording.

**Why this priority**: Wrong picks cause moderator rejections and poor event experience.

**Independent Test**: Search a popular song → multiple results show distinguishable titles (and channel or thumbnail) → user can identify the intended video.

**Acceptance Scenarios**:

1. **Given** a search returns multiple videos, **When** I view the list, **Then** each row shows **title**, **thumbnail**, and **channel name**.
2. **Given** a search returns one result, **When** I view the list, **Then** I can still submit that single result.
3. **Given** results are loading, **When** I wait, **Then** I see a clear loading state in Spanish without blocking the rest of `/participar`.

---

### User Story 3 — Search errors and empty results (Priority: P2)

As a participant, I get clear feedback when search fails or finds nothing so I can try another query or paste a URL.

**Why this priority**: API limits and typos are common at events.

**Independent Test**: Empty query blocked → no results message → API failure shows Spanish error; URL submit still works.

**Acceptance Scenarios**:

1. **Given** my query is too short (below minimum length), **When** I try to search, **Then** I see a Spanish hint to refine the query and no API call is made.
2. **Given** the API returns zero videos, **When** results load, **Then** I see an empty state in Spanish suggesting another query or pasting a link.
3. **Given** one API key in the pool has exhausted its daily quota but another key is available, **When** I search, **Then** I still receive results (failover is transparent to me).
4. **Given** all API keys in the pool have exhausted quota or are invalid, **When** I search, **Then** I see a friendly Spanish error and can still use URL submit.
5. **Given** I select a video that violates submit limits (duplicate active, pending limit, active song limit), **When** I tap **Enviar canción**, **Then** I see the same Spanish errors as 006 URL submit.
6. **Given** I have used 10 searches in the last 5 minutes, **When** I try again, **Then** I see a Spanish rate-limit message and no new API call is made.

---

### User Story 4 — No regression on participate flows (Priority: P1)

As a participant, voting, URL submit, Mis canciones, and notifications still work after search is added.

**Why this priority**: `/participar` is a single surface; search must not break 005–007.

**Independent Test**: OAuth → vote → URL submit → receive notification toast → search submit; all behaviors match prior changes.

**Acceptance Scenarios**:

1. **Given** I am signed in, **When** I vote after using search UI, **Then** vote limits and queue order behave per 005.
2. **Given** I submit via URL, **When** I do not use search, **Then** behavior is unchanged from 006.
3. **Given** notifications are enabled, **When** my searched song is approved, **Then** I still receive the approval toast per 007.

---

### Edge Cases

- Tocar un resultado sin pulsar **Enviar canción** → no crea `pending_review`; solo resalta la selección.
- Búsqueda con caracteres especiales o solo espacios → trim en cliente; solo espacios → rechazar con mensaje claro sin llamada API; caracteres especiales pasan a la API tras trim.
- Resultado ya en cola activa (`pending_review`, `queued`, `playing`) → mismo error de duplicado que 006.
- Participante alcanza 2 `pending_review` → no puede enviar otro resultado de búsqueda hasta liberar cupo.
- API devuelve vídeo no disponible / metadata falla al enviar → rechazo con mensaje comprensible (no `pending_review` silencioso).
- Varias búsquedas seguidas → cada búsqueda reemplaza la lista anterior; no acumular listas confusas; solo tras **Buscar** o **Enter** (no al escribir).
- Conexión lenta → loading visible; el usuario puede cancelar o ignorar y usar URL.
- Participante supera **10 búsquedas / 5 min** → mensaje en español; puede seguir usando envío por URL y votación.
- Una API key del pool agota cuota diaria → backend marca esa key temporalmente no disponible y reintenta con la siguiente; el participante no ve error si queda alguna key usable.
- Todas las API keys del pool agotadas o inválidas → error en español; URL submit sigue activo.
- Pool con una sola key configurada → comportamiento válido (sin round-robin útil, pero sí failover si se añaden más keys después).
- Participante autenticado puede alternar entre búsqueda y URL en la misma sesión; ambos caminos siguen válidos.
- URL con texto y resultado de búsqueda seleccionado → **un solo camino activo** (última interacción); **Enviar canción** envía solo ese camino.
- La sección activa (búsqueda o URL) debe verse **resaltada** (borde/fondo) para que el participante sepa qué se enviará.
- Tocar/enfocar el campo URL **sin** editar texto → **no** cambia el camino activo.
- Layout **apilado**: búsqueda arriba, URL abajo; ambos bloques siempre visibles (sin pestañas ni acordeón).
- **Enviar canción** en **footer sticky** al pie de pantalla; visible al hacer scroll; envía solo el camino activo.
- Sin ninguna API key en el pool → solo se deshabilita **búsqueda**; **envío por URL permanece activo** como opción principal alternativa.

## Requirements

### Functional Requirements

- **FR-001**: Authenticated participants on `/participar` MUST be able to search YouTube videos by text query (via **Buscar** button or **Enter** in the search field; no auto-search while typing) and view a bounded list of results.
- **FR-002**: Selecting a search result (row highlight) and confirming with **Enviar canción** MUST create a `pending_review` `queue_entry` with the same validation and limits as **006** URL submit (`submitted_by_participant_id`, duplicate rules, pending/active caps). `original_query` MUST be `search:{query}` where `{query}` is the participant's last search text for that selection.
- **FR-003**: The existing **URL/ID paste** submit path from **006** MUST remain **fully available, unchanged in behavior, and first-class** alongside search on `/participar` (same limits, same `pending_review` flow, same Spanish errors).
- **FR-003a**: Participants MUST be able to submit via **either** search **or** URL in the same session; disabling search (no API keys or all keys exhausted) MUST NOT disable URL submit.
- **FR-003b**: When both a URL value and a search selection exist, **exactly one submit path is active** at a time: the **last user interaction** (URL field **text edit** — type, paste, or clear → URL path; search row selection → search path). **Focus alone** on the URL field MUST NOT change the active path. A **single** **Enviar canción** control MUST submit only the active path.
- **FR-003c**: The UI MUST **visually highlight the active submit section** (search block vs URL block), e.g. via border or background, updated on each interaction that changes the active path.
- **FR-003d**: On `/participar`, search and URL submit MUST use a **stacked layout**: search block **above** URL block; **both blocks remain visible** at all times (no tabs or accordion that hide either path).
- **FR-003e**: A **single** **Enviar canción** button MUST be **sticky at the bottom** of the viewport on `/participar` (fixed footer position); it submits only the active path per FR-003b.
- **FR-004**: Search MUST require a minimum query length (default **2** characters after trim) before calling the external API.
- **FR-005**: Each search result row MUST show **title**, **thumbnail**, and **channel name** so participants can choose the correct video.
- **FR-006**: The system MUST cap the number of results shown per search (default **10**) to keep mobile UI usable.
- **FR-007**: The system MUST enforce a per-participant search rate limit of **10 searches per 5-minute rolling window**; further searches return a clear Spanish error without calling the YouTube API.
- **FR-008**: The backend MUST support a **pool of YouTube Data API keys** (target **4–5** keys via deployment config). Each search request MUST use **round-robin** key selection. If a key returns quota-exhausted (or equivalent non-retryable quota error), the system MUST **automatically retry** the same search with the next key in the pool. The participant sees an error **only when all keys** in the pool are exhausted or unusable.
- **FR-009**: When the YouTube API is unavailable for reasons other than per-key quota (e.g. network), `/participar` MUST show understandable **Spanish** feedback and MUST NOT block URL submit. When **no** API keys are configured, the search section MUST remain **visible but disabled** with an explanatory Spanish message.
- **FR-010**: When search returns no videos, `/participar` MUST show an empty state in Spanish.
- **FR-011**: Unauthenticated users MUST NOT be able to search (same gating as vote/submit).
- **FR-012**: Voting, Mis canciones, OAuth, notifications, and operator moderation from **004–007** MUST remain unchanged.
- **FR-013**: Active contracts MUST document the search API, **multi-key pool**, failover behavior, rate limits, and `/participar` search UX.

### Key Entities

- **`search_query`**: Ephemeral user input (text) for one search action; not persisted server-side beyond request handling.
- **`search_result`**: Ephemeral item with `youtube_video_id`, `title`, `channel_title`, `thumbnail_url` (all required on the wire for UI).
- **`youtube_api_key_pool`**: Ordered list of API keys (conceptual **4–5** entries) with runtime state per key (`available` / `quota_exhausted` until daily reset). Not exposed to clients.
- **`queue_entry`**: Unchanged lifecycle from 004; search submit is another entry path to `pending_review`; `original_query` = `search:{query}` when submitted from search selection.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A signed-in participant can search, select a result, and see it in **Mis canciones** as pending within **5 seconds** on typical event Wi‑Fi.
- **SC-002**: **95%** of successful search submits respect the same limit and duplicate rules as URL submit (automated tests mirror 006 cases).
- **SC-003**: Participants can still complete URL submit and vote successfully after search UI is present (**100%** regression pass on 005–006 core scenarios).
- **SC-004**: When the API returns no results, participants see an empty state within **3 seconds** without application errors.
- **SC-005**: With no API keys in the pool, search section is visible-but-disabled with Spanish message and URL submit remains **100%** functional.
- **SC-006**: **100%** of search attempts beyond the 10-per-5-minute participant limit are rejected with Spanish feedback (automated test coverage).
- **SC-007**: When at least one key in the pool has quota remaining, search succeeds without participant-visible error (**100%** in tests simulating single-key exhaustion with failover).
- **SC-008**: Participant-visible search failure occurs **only** when all keys in the pool are exhausted (automated test coverage).

## Assumptions

- **No monetary cost** for search in v1: YouTube Data API is used within each project's **free daily quota** only; operators are not required to enable paid Google Cloud billing for search.
- **No ads in search UI**: search returns metadata (title, thumbnail, channel) only; no YouTube player or ad slots on `/participar` search results.
- **Kiosk playback ads** (if any) come from the existing YouTube IFrame player on `/` (004), not from this change.
- Operator provisions **4–5 Google Cloud projects** (or equivalent) each with a YouTube Data API key; exact env/config naming in plan/contracts (`JUKEBOX_` prefix).
- Default per-project search quota is on the order of **~100 searches/day** per key (Google bucket for `search.list`); **4–5 keys** ≈ **~400–500 searches/day** combined before global exhaustion — sufficient for small/medium events with participant rate limits.
- Operator is responsible for complying with [YouTube API Services Terms](https://developers.google.com/youtube/terms/api-services-terms-of-service) when operating multiple projects/keys.
- Round-robin and per-key `quota_exhausted` state are maintained in the **backend process** (plan addresses multi-replica consistency if needed).
- Submit metadata for URL paste continues to use **oEmbed** (006) without API keys.
- Spanish UI throughout `/participar`.
- Backend returns stable English `detail` for programmatic errors; frontend maps to Spanish (006 pattern).
- Search is video-only (`type=video`); music videos and live performances are acceptable results.
- Moderator approval still required before `queued`.
- Mobile-first layout: **stacked** search block above URL block on `/participar`; both always visible; fits without hiding vote list.

## Scope boundary vs downstream changes

| Topic | This change (008) | Later |
|-------|-------------------|-------|
| Dual submit on `/participar` | **Search** + **URL paste** (both valid) | — |
| Multi-key pool + round-robin failover | Yes | — |
| URL/ID submit | Unchanged (006), always available when authenticated | — |
| Operator search in `/admin` | No | Optional |
| Web Push | No | v1.1+ |
| Playlist/channel submit | No | Optional |
| Search analytics / trending | No | Optional |

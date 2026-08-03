# Research: 016-participant-limits-ux

**Date**: 2026-08-03

## R1 — Connection status bug root cause

**Decision**: Single state machine with mutually exclusive UI labels; `onopen` clears reconnecting/fallback; polling only when SSE exhausted.

**Rationale**: User reported overlapping «Reconectando…» + truncated «Modo respaldo: actuali…» — classic symptom of missing `onopen` handler and dual visible layers.

**Alternatives considered**:
- Always show «En vivo» when connected — rejected; spec prefers hidden badge when healthy
- HTTP polling only — rejected; SSE remains primary per 004/010

## R2 — Fallback polling interval

**Decision**: 15 seconds poll + SSE retry each interval while in fallback.

**Rationale**: Balances battery/mobile data with operator trust during live events; aligns with admin API key SSE “within 5s” spirit without hammering server.

## R3 — Vote/search window alignment

**Decision**: 10-minute rolling window for both, driven by ENV names `*_10MINUTES_*`.

**Rationale**: User explicitly named ENV vars with 10 minutes; previous 5-minute vote window and 5-minute search window diverged from requested config surface.

**Migration note**: Vote rollover test updated from 6→11 minutes idle.

## R4 — Rules acceptance persistence

**Decision**: `sessionStorage` only (per browser tab session).

**Rationale**: Spec FR-010; no DB migration; sufficient for event UX; re-shown on new session matches “first connect” intent.

## R5 — Admin mobile layout

**Decision**: Tailwind `md:hidden` cards + `hidden md:block` table.

**Rationale**: Minimal diff; preserves desktop density; avoids fragile `overflow-x-auto` on narrow screens.

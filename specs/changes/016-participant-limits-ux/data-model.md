# Data Model: 016-participant-limits-ux

**Change**: 016-participant-limits-ux

## No new database tables

This change is configuration + client session only.

## Configuration (backend settings)

| Setting | ENV | Default | Min |
|---------|-----|---------|-----|
| Max pending/queued submissions per participant | `JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT` | 2 | 1 |
| Max searches per 10 min | `JUKEBOX_MAX_SEARCHS_10MINUTES_PER_PARTICIPANT` | 10 | 1 |
| Max votes per 10 min | `JUKEBOX_MAX_VOTES_10MINUTES_PER_PARTICIPANT` | 2 | 1 |

## API response extension

`ParticipantStateResponse` adds:

| Field | Type | Description |
|-------|------|-------------|
| `max_searches_10_minutes` | int | Configured search cap |
| `max_votes_10_minutes` | int | Configured vote cap |

Existing `max_pending_submissions` unchanged.

## Client session

| Key | Storage | Value |
|-----|---------|-------|
| `jukebox.participantRulesAccepted` | `sessionStorage` | `"1"` after user accepts rules |

## In-memory (unchanged)

Search rate limiter buckets and vote window counts remain in-process per 010 single-replica model.

## Connection state (client only)

| State | UI label |
|-------|----------|
| `connected` | (hidden) |
| `reconnecting` | Reconectando… |
| `fallback` | Modo respaldo |

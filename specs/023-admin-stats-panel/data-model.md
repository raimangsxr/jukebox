# Data Model: 023-admin-stats-panel

**Feature**: `023-admin-stats-panel`  
**Migration**: No

## Overview

Statistics are **derived at read time** from existing tables. No new tables or columns.

## Source tables (unchanged)

| Table | Use in stats |
|-------|----------------|
| `participants` | `display_name`; ranking label fallback: email local-part → «Participante» |
| `queue_entries` | Submissions by participant; `status` counts; `vote_count` + `youtube_video_id` + `title` for song rankings |
| `votes` | Per-participant vote totals; contributes to «ha participado» |

## Derived aggregates (API response, not stored)

### Summary totals

| Field | Computation |
|-------|-------------|
| `participants_active_count` | Distinct participants with ≥1 submission (`submitted_by_participant_id`) OR ≥1 row in `votes` |
| `total_submissions` | `COUNT(queue_entries)` where `submitted_by_participant_id IS NOT NULL` (all statuses) |
| `total_votes_cast` | `COUNT(votes)` |
| `distinct_voted_songs_count` | Distinct `youtube_video_id` with `SUM(vote_count) > 0` across entries |

### Queue status counts

| Field | `queue_entries.status` |
|-------|------------------------|
| `pending_review` | `pending_review` |
| `queued` | `queued` |
| `playing` | `playing` |
| `played` | `played` |
| `rejected` | `rejected` |

### Rankings (max 10 each)

| Ranking | Group by | Order | Tie-break |
|---------|----------|-------|-----------|
| `top_submitters` | `submitted_by_participant_id` | submission count DESC | `display_name` ASC |
| `top_voters` | `votes.participant_id` | vote count DESC | `display_name` ASC |
| `top_songs` | `youtube_video_id` | `SUM(vote_count)` DESC | `title` ASC |

**Submission count**: all participant-attributed entries regardless of status (incl. pending, rejected).

**Operator entries**: `submitted_by_participant_id IS NULL` excluded from participant submission rankings and `total_submissions` (operator/filler only).

**Song title**: pick `MAX(title)` or first non-null title per `youtube_video_id` for display.

## Lifecycle / vaciar historial

When `DELETE /api/queue/history` removes terminal rows (and cascaded votes if applicable), subsequent `GET /api/admin/stats` excludes deleted submissions/votes from all aggregates (FR-011).

## Validation rules

- Operator session required; participants receive 401.
- Ranking `display_name`: `participants.display_name`, else email local-part before `@`, else `«Participante»`.
- Empty event: all counts `0`, rankings `[]`, no error.
- Rankings omit participants with zero count in that category.

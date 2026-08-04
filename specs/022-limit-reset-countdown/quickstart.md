# Quickstart: 022-limit-reset-countdown

Validation after implementation.

## Prerequisites

- Branch `022-limit-reset-countdown`
- Migration applied (`participants` columns + `participant_searches`)
- Participant dev session on `/participar` (post-normas)
- Default limits: 2 votes / 10 searches per 10 min (or known ENV values)

## Phase 1 — Votes: no countdown at full quota (US1, SC-002)

1. Open `/participar` with **full votes**, never voted in current window
2. **Expected**: Header shows «X de Y votos disponibles» **without** «Cupo completo en» and **without** «cada 10 min»

## Phase 2 — Votes: countdown after first vote (US1, FR-004)

1. Cast **one** vote (still has votes left if max > 1)
2. **Expected**: Header shows «X de Y votos disponibles · Cupo completo en MM:SS» (e.g. `09:5x`)
3. Counter ticks down each second
4. With 2 votes max: can still cast second vote before expiry

## Phase 3 — Votes: expiry auto-refresh (US1, FR-014, SC-006)

1. Exhaust votes or wait until countdown nears zero (test env: shorten WINDOW in test only)
2. At `00:00`, **without** manual reload
3. **Expected**: Countdown disappears; `votes_remaining` = max; label returns to «X de Y votos disponibles» only

## Phase 3b — Vote limit error + countdown (FR-009)

1. Exhaust votes in window (0 remaining) with countdown visible
2. Attempt another vote
3. **Expected**: Error message appears **and** countdown still shows the **same** recovery time (does not reset or disappear)

## Phase 4 — Searches: symmetric behavior (US2)

1. Expand «Enviar canciones» → Buscar en YouTube
2. **Expected**: «X de Y búsquedas disponibles» without countdown before any search
3. Run one successful search
4. **Expected**: «X de Y búsquedas disponibles · Cupo completo en MM:SS»
5. Paste URL only (no search) → search countdown unchanged

## Phase 4b — Search limit error + countdown (FR-009)

1. Exhaust searches with countdown visible
2. Attempt another search
3. **Expected**: Rate-limit message **and** same countdown instant as before rejection

## Phase 5 — Server coherence (US3)

1. With active vote countdown, reload page
2. **Expected**: MM:SS within ~2s of pre-reload value
3. Open second tab, vote in first tab
4. **Expected**: Second tab updates countdown/cupo **within a few seconds** (SSE `state` triggers full `refresh()`, not 15s poll wait)

## Phase 6 — Fixed window does not reset on second consume (US3)

1. At full quota, cast first vote → note countdown (e.g. `09:59`)
2. Within 30s cast second vote
3. **Expected**: Countdown **does not** jump back to `09:59` (same end instant)

## Phase 7 — Errors do not start window (FR-011)

1. Full quota, vote on non-queued entry (if reproducible) or search `q=a`
2. **Expected**: No countdown appears; quota unchanged

## Phase 8 — Normas screen copy (optional polish)

1. Clear `sessionStorage` rules acceptance; re-login to `/participar`
2. **Expected**: Normas text does not contradict live countdown behavior (no misleading «solo cada 10 min» without mentioning timer when window active)

## Automated

```bash
pytest backend/tests/test_limit_windows.py backend/tests/test_votes.py backend/tests/test_youtube_search.py backend/tests/test_participant_submit.py -q
npm --prefix frontend test -- src/app/limit-countdown.util.spec.ts src/app/participant-limits.util.spec.ts src/app/participate/participate.component.spec.ts
npm --prefix frontend run build
```

## Sign-off

- [ ] Phases 1–8 pass
- [ ] Automated commands green
- [ ] Contract deltas merged to active contracts

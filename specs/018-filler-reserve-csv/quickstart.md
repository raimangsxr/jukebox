# Quickstart: 018-filler-reserve-csv

Validation after implementation. Requires **017** filler reserve in Admin.

## Prerequisites

- Branch `018-filler-reserve-csv`
- Operator session on `/admin`
- `JUKEBOX_YOUTUBE_API_KEYS` for import metadata validation
- At least 3 songs in filler reserve (from 017 UI or API)

## Phase 1 — Export (US1)

1. Open **Reserva de relleno** in Admin
2. Click **Exportar CSV** → file downloads
3. Open file: line 1 is `url`; following lines are `https://www.youtube.com/watch?v=…` in same order as UI
4. Empty reserve → export yields only `url` header

## Phase 2 — Import validate (US3 / SC-006)

1. Edit exported file in a text editor: reorder two rows
2. **Importar CSV** → select file
3. Preview shows correct `valid_count` and replace warning; **Confirmar** disabled until acknowledged
4. Add an invalid line `not-a-url` → preview lists line number + error; **Confirmar** disabled (`can_confirm: false`)
5. Cancel → reserve unchanged
6. File with only `url` header → preview says reserve will be empty; confirm → reserve cleared

## Phase 3 — Import commit (US2 / FR-011)

1. Import valid reordered file → confirm
2. Reserve order matches file (top to bottom = position 1..N)
3. **Without reloading the page**, reserve list in Admin updates (FR-011)
4. Export again → same order as step 1 edit (SC-005 round-trip)

## Phase 4 — Edge cases

1. Duplicate same video on two lines → validate errors; reserve unchanged
2. Video already in **active queue** → validate errors with clear message
3. Video only in **current reserve** (re-import same export) → validate **succeeds**
4. 51 URLs in file → validate rejects (limit 50)
5. Participant `POST /api/filler-reserve/import` → 401

## Phase 5 — Automated

```bash
pytest backend/tests/test_filler_reserve.py -k "import or export or csv"
npm --prefix frontend run build
```

## Manual API probe

```bash
# Export
curl -s -b operator.txt -o reserve.csv \
  -H 'Accept: text/csv' \
  http://localhost:8000/api/filler-reserve/export

# Validate
curl -s -b operator.txt -F file=@reserve.csv \
  http://localhost:8000/api/filler-reserve/import/validate | jq

# Commit
curl -s -b operator.txt -F file=@reserve.csv \
  http://localhost:8000/api/filler-reserve/import | jq
```

## SC gates

| ID | Gate |
|----|------|
| SC-001 | Export 20-item reserve; verify order in < 1 min |
| SC-002 | Import 50 URLs with preview + confirm in < 3 min |
| SC-003 | Invalid row → reserve unchanged (100%) |
| SC-005 | Export → edit order → import → position 1 matches |
| SC-006 | Invalid preview row → line + reason shown; confirm blocked |
| FR-011 | After import, Admin reserve list updates without page reload |

Document results in PR notes.

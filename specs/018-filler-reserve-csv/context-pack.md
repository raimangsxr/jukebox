# Context Pack: 018-filler-reserve-csv

**Change id**: `018-filler-reserve-csv`  
**Branch**: `018-filler-reserve-csv`  
**Status**: planned  
**Modifies**: `backend-api`, `app-core`  
**Depends on**: `017-admin-queue-history-filler` (filler reserve)

## Read order

1. [spec.md](./spec.md) — requirements + clarifications (2026-08-04)
2. [plan.md](./plan.md) — implementation plan
3. [data-model.md](./data-model.md) — DTOs and file format
4. [contracts/contract-deltas.md](./contracts/contract-deltas.md) — export/import endpoints
5. [research.md](./research.md) — validate/commit, line parsing

## Summary

Operator can **export** filler reserve as CSV (`url` header + canonical YouTube watch URLs in order) and **import** CSV to **replace** the reserve. Import uses **validate → confirm → commit** with full YouTube/duplicate/queue validation in preview. One URL per line; UTF-8; empty file clears reserve on explicit confirm.

## Key files (expected touch)

```text
backend/app/schemas.py                           # import validation DTOs
backend/app/services/filler_reserve_service.py   # parse, validate, replace, export
backend/app/routers/filler_reserve.py            # export + import routes
backend/tests/test_filler_reserve.py             # export/import tests

frontend/src/app/services/filler-reserve.service.ts
frontend/src/app/admin/admin.component.{ts,html}
```

## Clarifications locked

- Empty import → clear reserve with explicit confirm
- Export always full watch URL + `url` header
- Import: one URL per line (not strict CSV columns)
- Preview runs full validation before confirm
- Import validate: within-file dupes + active queue only (not current reserve rows)

## Constitution reminders

- Merge contract deltas before implement
- Set `active.change` in `specs/manifest.yml`
- Extend `test_filler_reserve.py`; no new migration

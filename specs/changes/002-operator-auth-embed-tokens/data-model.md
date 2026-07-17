# Data Model Delta: 002-operator-auth-embed-tokens

## New table: `api_tokens`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid string PK | `str(uuid4())` |
| user_id | int FK → users.id | CASCADE delete |
| label | string(64) | operator label, e.g. "Kiosk sala"; required, 1–64 chars |
| token_hash | string(255) unique | bcrypt(plaintext) |
| created_at | timestamptz | server default |
| last_used_at | timestamptz nullable | updated on exchange |
| revoked_at | timestamptz nullable | soft revoke |

## Existing: `users` (unchanged)

Used by login and `api_tokens.user_id`.

## Session payload

`request.session["user_id"]` → `users.id` (int).

## Alembic

- `0002_api_tokens.py` — creates `api_tokens` only

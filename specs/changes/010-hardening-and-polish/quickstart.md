# Quickstart: 010-hardening-and-polish

Manual validation for the hardening/completion/polish change. Run after deploying the new backend + frontend.

## Pre-rollout operations (US2 / US4)

1. **Rotate the session secret** (invalidates all sessions once):
   ```bash
   NEW=$(python3 -c "import secrets; print(secrets.token_hex(32))")
   # k8s: patch jukebox-secrets JUKEBOX_SESSION_SECRET, then rollout restart backend
   ```
2. **Reissue embed/API tokens**: old tokens (no prefix) stop validating. In `/admin` → Tokens de iframe, create new tokens and update kiosk `?token=` URLs; revoke the old ones.
3. Confirm `.env` is not tracked: `git ls-files .env` → empty.

## US1 — SSE audience isolation

1. Open `/admin` (operator) and `/participar` (participant, dev-auth) in two browsers.
2. Trigger a participant search → the **operator** admin "Uso de API Keys" updates live; the participant stream receives **no** `api_key_usage`.
3. As operator, approve participant A's song → only A sees the toast; a second participant B sees none.
4. Backend tests: `pytest tests/test_sse.py tests/test_notifications.py`.

## US3 — responsiveness / single replica

1. `deploy/k8s/backend.yaml` has `replicas: 1`; README documents the constraint.
2. Under concurrent searches the app stays responsive (outbound calls run in the FastAPI threadpool).

## US4 — robustness

- Token exchange with a regenerated token succeeds; a pre-010 token returns `401 invalid or revoked token`.
- `pytest tests/test_token_prefix.py tests/test_rate_limiter.py tests/test_quota_reset.py tests/test_queue_submitter_fk.py tests/test_submit_metadata_consistency.py`.

## US5 — event configuration

1. In `/admin` → **Evento**, edit Nombre/Subtítulo/Altura/Tema/Canciones visibles and **Guardar cambios**.
2. On the kiosk `/`, the header/QR subtitle and visible-queue count update within a few seconds (SSE), no reload.
3. Invalid values (height 0, visible 0, empty name, theme ≠ dark) → Spanish validation error, config unchanged.
4. `pytest tests/test_event_config.py`.

## US6 — visual/UX

1. Kiosk renders without clipping at 720p, 1080p, and 2160p.
2. Approving one pending row disables only that row's buttons.
3. Unknown route (e.g. `/nope`) shows the Spanish 404 page.
4. Production bundle within budget: `npm --prefix frontend run build`.

## US7 — tests

- Frontend: `npm --prefix frontend test` (guards, interceptor, theme, event-config, plus existing specs).

## Regression (US8 / SC-011)

```bash
pytest backend/tests            # full backend suite
npm --prefix frontend test      # full frontend suite
npm --prefix frontend run build # bundle + budgets
./scripts/compose-smoke.sh      # /api/health + CSP (operator-run)
```

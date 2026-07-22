"""Search rate-limiter eviction (010, FR-010)."""

from datetime import datetime, timedelta, timezone

from app.services import search_rate_limiter as rl


def test_expired_buckets_are_evicted():
    rl.reset_for_tests()
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)
    assert rl.check_and_record("ghost", now=past) is True
    assert "ghost" in rl._timestamps

    # Drive enough later calls to trigger a sweep; the idle "ghost" bucket
    # (window fully expired) must be dropped so memory stays bounded.
    future = past + timedelta(days=1)
    for i in range(rl._SWEEP_EVERY):
        rl.check_and_record(f"live-{i}", now=future)

    assert "ghost" not in rl._timestamps
    rl.reset_for_tests()


def test_limit_still_enforced_within_window():
    rl.reset_for_tests()
    now = datetime(2021, 6, 1, 12, 0, tzinfo=timezone.utc)
    for _ in range(rl._LIMIT):
        assert rl.check_and_record("p1", now=now) is True
    assert rl.check_and_record("p1", now=now) is False
    rl.reset_for_tests()

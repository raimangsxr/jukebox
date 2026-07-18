"""YouTube metadata helpers."""

from app.services.youtube_meta import parse_iso8601_duration


def test_parse_iso8601_duration_minutes_seconds():
    assert parse_iso8601_duration("PT4M13S") == 253


def test_parse_iso8601_duration_hours():
    assert parse_iso8601_duration("PT1H2M3S") == 3723


def test_parse_iso8601_duration_seconds_only():
    assert parse_iso8601_duration("PT45S") == 45


def test_parse_iso8601_duration_invalid():
    assert parse_iso8601_duration("not-a-duration") is None

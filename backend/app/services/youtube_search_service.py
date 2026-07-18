from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from fastapi import HTTPException, status

from ..config import get_settings
from ..schemas import SearchResultItem
from .youtube_api_key_pool import get_youtube_api_key_pool

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
QUOTA_ERROR_REASONS = frozenset(
    {"quotaExceeded", "dailyLimitExceeded", "userRateLimitExceeded"}
)


def _validate_query(query: str) -> str:
    trimmed = query.strip()
    min_len = get_settings().youtube_search_min_query_length
    if len(trimmed) < min_len:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid search query",
        )
    return trimmed


def _parse_quota_error(body: str) -> bool:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False
    for err in payload.get("error", {}).get("errors", []):
        if err.get("reason") in QUOTA_ERROR_REASONS:
            return True
    return False


def _fetch_with_key(query: str, api_key: str) -> dict:
    params = urllib.parse.urlencode(
        {
            "part": "snippet",
            "type": "video",
            "maxResults": str(get_settings().youtube_search_max_results),
            "q": query,
            "key": api_key,
        }
    )
    url = f"{YOUTUBE_SEARCH_URL}?{params}"
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_items(payload: dict) -> list[SearchResultItem]:
    results: list[SearchResultItem] = []
    for item in payload.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet") or {}
        title = snippet.get("title")
        channel = snippet.get("channelTitle")
        thumbnails = snippet.get("thumbnails") or {}
        thumb = (
            thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )
        if (
            not isinstance(video_id, str)
            or not video_id
            or not isinstance(title, str)
            or not title.strip()
            or not isinstance(channel, str)
            or not channel.strip()
            or not isinstance(thumb, str)
            or not thumb
        ):
            continue
        results.append(
            SearchResultItem(
                youtube_video_id=video_id,
                title=title.strip(),
                channel_title=channel.strip(),
                thumbnail_url=thumb,
            )
        )
    return results


def validate_search_query(query: str) -> str:
    return _validate_query(query)


def search_videos(query: str) -> list[SearchResultItem]:
    trimmed = _validate_query(query)
    settings = get_settings()
    if not settings.youtube_api_keys.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="youtube search unavailable",
        )

    pool = get_youtube_api_key_pool()
    keys = [k.strip() for k in settings.youtube_api_keys.split(",") if k.strip()]
    attempts = 0
    while attempts < len(keys):
        api_key = pool.acquire_key()
        if api_key is None:
            break
        attempts += 1
        try:
            payload = _fetch_with_key(trimmed, api_key)
            return _parse_items(payload)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 403 and _parse_quota_error(body):
                pool.mark_exhausted(api_key)
                continue
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="youtube search unavailable",
            ) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="youtube search unavailable",
            ) from None

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="youtube search unavailable",
    )

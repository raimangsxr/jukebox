import json
import re
import urllib.error
import urllib.parse
import urllib.request

from sqlalchemy.orm import Session

from .youtube_api_key_pool import get_youtube_api_key_pool
from .youtube_api_key_usage_service import mark_google_exhausted, record_attempt
from ..config import get_settings

YOUTUBE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")
YOUTUBE_URL_PATTERNS = [
    re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})"),
]


YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
MAX_PLAYLIST_PROCESSING_ITEMS = 500
QUOTA_ERROR_REASONS = frozenset(
    {"quotaExceeded", "dailyLimitExceeded", "userRateLimitExceeded"}
)
_ISO8601_DURATION_RE = re.compile(
    r"^PT"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+)S)?$"
)


def parse_iso8601_duration(value: str) -> int | None:
    match = _ISO8601_DURATION_RE.match(value.strip())
    if not match:
        return None
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    total = hours * 3600 + minutes * 60 + seconds
    return total if total > 0 else None


def _parse_quota_error(body: str) -> bool:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False
    for err in payload.get("error", {}).get("errors", []):
        if err.get("reason") in QUOTA_ERROR_REASONS:
            return True
    return False


def fetch_youtube_duration_sec(video_id: str, db: Session | None = None) -> int | None:
    if not get_settings().youtube_api_keys.strip():
        return None

    pool = get_youtube_api_key_pool()
    keys = [key.strip() for key in get_settings().youtube_api_keys.split(",") if key.strip()]
    attempts = 0
    while attempts < len(keys):
        api_key = pool.acquire_key(db=db)
        if api_key is None:
            break
        attempts += 1
        if db is not None:
            record_attempt(db, api_key)
        try:
            params = urllib.parse.urlencode(
                {
                    "part": "contentDetails",
                    "id": video_id,
                    "key": api_key,
                }
            )
            url = f"{YOUTUBE_VIDEOS_URL}?{params}"
            with urllib.request.urlopen(url, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
            items = payload.get("items") or []
            if not items:
                return None
            duration = items[0].get("contentDetails", {}).get("duration")
            if not isinstance(duration, str):
                return None
            return parse_iso8601_duration(duration)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 403 and _parse_quota_error(body):
                if db is not None:
                    mark_google_exhausted(db, api_key)
                pool.mark_exhausted(api_key)
                continue
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
            return None
    return None


def fetch_youtube_videos_details_batch(
    video_ids: list[str], db: Session | None = None
) -> dict[str, tuple[str, str | None, int | None]]:
    """Return title, thumbnail, duration per video id. Omitted ids were not found."""
    if not video_ids:
        return {}

    unique_ids = list(dict.fromkeys(video_ids))
    details: dict[str, tuple[str, str | None, int | None]] = {}

    if get_settings().youtube_api_keys.strip():
        pool = get_youtube_api_key_pool()
        keys = [key.strip() for key in get_settings().youtube_api_keys.split(",") if key.strip()]
        attempts = 0
        while attempts < len(keys):
            api_key = pool.acquire_key(db=db)
            if api_key is None:
                break
            attempts += 1
            if db is not None:
                record_attempt(db, api_key)
            try:
                params = urllib.parse.urlencode(
                    {
                        "part": "snippet,contentDetails",
                        "id": ",".join(unique_ids),
                        "key": api_key,
                    }
                )
                url = f"{YOUTUBE_VIDEOS_URL}?{params}"
                with urllib.request.urlopen(url, timeout=10) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                for item in payload.get("items") or []:
                    video_id = item.get("id")
                    snippet = item.get("snippet") or {}
                    title = snippet.get("title")
                    if not isinstance(video_id, str) or not isinstance(title, str) or not title.strip():
                        continue
                    thumbnails = snippet.get("thumbnails") or {}
                    thumb = None
                    for key in ("maxres", "high", "medium", "default"):
                        candidate = thumbnails.get(key, {}).get("url")
                        if isinstance(candidate, str):
                            thumb = candidate
                            break
                    duration_raw = item.get("contentDetails", {}).get("duration")
                    duration = (
                        parse_iso8601_duration(duration_raw)
                        if isinstance(duration_raw, str)
                        else None
                    )
                    details[video_id] = (title.strip(), thumb, duration)
                return details
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code == 403 and _parse_quota_error(body):
                    if db is not None:
                        mark_google_exhausted(db, api_key)
                    pool.mark_exhausted(api_key)
                    continue
                break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
                break

    for video_id in unique_ids:
        if video_id in details:
            continue
        try:
            title, thumbnail = fetch_youtube_metadata_strict(video_id)
        except ValueError:
            continue
        details[video_id] = (
            title,
            thumbnail,
            fetch_youtube_duration_sec(video_id, db),
        )
    return details


def parse_youtube_playlist_id(value: str) -> str | None:
    text = value.strip()
    if not text:
        return None
    parsed = urllib.parse.urlparse(text)
    query = urllib.parse.parse_qs(parsed.query)
    list_values = query.get("list")
    if list_values and list_values[0].strip():
        return list_values[0].strip()
    return None


def fetch_playlist_video_ids(playlist_id: str, db: Session | None = None) -> list[str]:
    if not get_settings().youtube_api_keys.strip():
        raise ValueError("playlist unavailable")

    pool = get_youtube_api_key_pool()
    keys = [key.strip() for key in get_settings().youtube_api_keys.split(",") if key.strip()]
    video_ids: list[str] = []
    page_token: str | None = None

    while True:
        fetched_page = False
        attempts = 0
        while attempts < len(keys):
            api_key = pool.acquire_key(db=db)
            if api_key is None:
                break
            attempts += 1
            if db is not None:
                record_attempt(db, api_key)
            try:
                params: dict[str, str] = {
                    "part": "contentDetails",
                    "playlistId": playlist_id,
                    "maxResults": "50",
                    "key": api_key,
                }
                if page_token:
                    params["pageToken"] = page_token
                url = f"{YOUTUBE_PLAYLIST_ITEMS_URL}?{urllib.parse.urlencode(params)}"
                with urllib.request.urlopen(url, timeout=15) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                for item in payload.get("items") or []:
                    video_id = item.get("contentDetails", {}).get("videoId")
                    if isinstance(video_id, str) and video_id:
                        video_ids.append(video_id)
                        if len(video_ids) > MAX_PLAYLIST_PROCESSING_ITEMS:
                            raise ValueError("playlist too large")
                page_token = payload.get("nextPageToken")
                fetched_page = True
                break
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code == 403 and _parse_quota_error(body):
                    if db is not None:
                        mark_google_exhausted(db, api_key)
                    pool.mark_exhausted(api_key)
                    continue
                raise ValueError("playlist unavailable") from exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
                raise ValueError("playlist unavailable") from None

        if not fetched_page:
            raise ValueError("playlist unavailable")
        if not page_token:
            break

    return video_ids


def resolve_playlist_or_video_ids(
    url: str, db: Session | None = None
) -> list[tuple[int, str, str]]:
    """Return (1-based index, video_id, original_query) in playlist order."""
    playlist_id = parse_youtube_playlist_id(url)
    if playlist_id:
        video_ids = fetch_playlist_video_ids(playlist_id, db)
        if not video_ids:
            raise ValueError("playlist empty")
        return [(index, video_id, url) for index, video_id in enumerate(video_ids, start=1)]

    video_id = parse_youtube_video_id(url)
    if video_id:
        return [(1, video_id, url)]

    raise ValueError("playlist unavailable")


def parse_youtube_video_id(value: str) -> str | None:
    text = value.strip()
    if YOUTUBE_ID_RE.match(text):
        return text
    for pattern in YOUTUBE_URL_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def fetch_youtube_metadata(video_id: str) -> tuple[str, str | None]:
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        title = data.get("title") or "Video de YouTube"
        thumbnail = data.get("thumbnail_url")
        return title, thumbnail
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return "Video de YouTube", f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def fetch_youtube_metadata_strict(video_id: str) -> tuple[str, str | None]:
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        title = data.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("missing title")
        thumbnail = data.get("thumbnail_url")
        return title.strip(), thumbnail if isinstance(thumbnail, str) else None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
        raise ValueError("metadata unavailable") from None

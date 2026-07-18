import json
import re
import urllib.error
import urllib.request

YOUTUBE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")
YOUTUBE_URL_PATTERNS = [
    re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})"),
]


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

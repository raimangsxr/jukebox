from datetime import datetime, timezone
from typing import Literal

from ..schemas import PlaybackStatusRead

PlaybackAudioMode = Literal["idle", "sound", "muted"]

_status = PlaybackStatusRead(audio_mode="idle", updated_at=datetime.now(timezone.utc))


def get_playback_status() -> PlaybackStatusRead:
    return _status.model_copy()


def update_playback_status(audio_mode: PlaybackAudioMode) -> PlaybackStatusRead:
    global _status
    _status = PlaybackStatusRead(
        audio_mode=audio_mode,
        updated_at=datetime.now(timezone.utc),
    )
    return _status.model_copy()


def reset_for_tests() -> None:
    global _status
    _status = PlaybackStatusRead(
        audio_mode="idle",
        updated_at=datetime.now(timezone.utc),
    )

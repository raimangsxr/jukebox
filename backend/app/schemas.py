from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=255)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class MeResponse(BaseModel):
    user: UserRead


class TokenExchangeRequest(BaseModel):
    token: str = Field(min_length=10, max_length=255)


class TokenCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=64)


class ApiTokenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class ApiTokenWithSecret(ApiTokenRead):
    token: str


class TokenCreateResponse(BaseModel):
    token: ApiTokenWithSecret


class TokenListResponse(BaseModel):
    tokens: list[ApiTokenRead]


class EventConfigSummary(BaseModel):
    name: str
    subtitle: str
    app_height_px: int
    theme: str
    queue_visible_count: int


class QueueEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    youtube_video_id: str
    title: str
    thumbnail_url: str | None = None
    vote_count: int
    position: int | None = None
    status: str
    rejection_reason: str | None = None
    duration_sec: int | None = None
    created_at: datetime


class PendingQueueEntryRead(QueueEntryRead):
    submitted_by_display_name: str | None = None


class StateResponse(BaseModel):
    revision: int
    now_playing: QueueEntryRead | None = None
    queue: list[QueueEntryRead]
    event_config: EventConfigSummary


class PendingListResponse(BaseModel):
    entries: list[PendingQueueEntryRead]


class RejectBody(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


class DevSubmitRequest(BaseModel):
    youtube_url_or_id: str = Field(min_length=1, max_length=500)


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    email: str | None = None
    avatar_url: str | None = None
    created_at: datetime


class ParticipantMeResponse(BaseModel):
    participant: ParticipantRead


class ParticipantDevAuthRequest(BaseModel):
    display_name: str = Field(default="Participante", min_length=1, max_length=120)


class ParticipantStateResponse(BaseModel):
    revision: int
    now_playing: QueueEntryRead | None = None
    queue: list[QueueEntryRead]
    votes_remaining: int
    event_config: EventConfigSummary


class VoteCreateRequest(BaseModel):
    queue_entry_id: str = Field(min_length=1, max_length=36)


class VoteResponse(BaseModel):
    id: str
    votes_remaining: int
    state: ParticipantStateResponse | None = None


class SubmitRequest(BaseModel):
    youtube_url_or_id: str = Field(min_length=1, max_length=500)
    search_query: str | None = Field(default=None, max_length=500)


class SearchConfigResponse(BaseModel):
    enabled: bool


class OAuthConfigResponse(BaseModel):
    enabled: bool


class SearchResultItem(BaseModel):
    youtube_video_id: str
    title: str
    channel_title: str
    thumbnail_url: str


class SearchResponse(BaseModel):
    results: list[SearchResultItem]


class SubmissionListResponse(BaseModel):
    entries: list[QueueEntryRead]


class NotificationEventRead(BaseModel):
    type: Literal["song.approved", "song.up_next"]
    queue_entry_id: str
    participant_id: str
    title: str

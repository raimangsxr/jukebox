from datetime import datetime
from typing import Literal

QueueModeLiteral = Literal["moderated", "free"]

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


class EventConfigRead(EventConfigSummary):
    model_config = ConfigDict(from_attributes=True)

    queue_mode: QueueModeLiteral
    filler_auto_inject_enabled: bool
    updated_at: datetime


class QueueModeUpdate(BaseModel):
    queue_mode: QueueModeLiteral


class FillerAutoInjectUpdate(BaseModel):
    filler_auto_inject_enabled: bool


class EventConfigUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    subtitle: str = Field(default="", max_length=200)
    app_height_px: int = Field(ge=240, le=4320)
    theme: str = Field(min_length=1, max_length=8)
    queue_visible_count: int = Field(ge=1, le=50)


QueueEntryPriorityLiteral = Literal["normal", "low"]
QueueEntrySourceLiteral = Literal[
    "participant",
    "operator_filler",
    "operator_direct",
    "auto_inject",
    "operator_requeue",
]


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
    priority: QueueEntryPriorityLiteral = "normal"


class PendingQueueEntryRead(QueueEntryRead):
    submitted_by_display_name: str | None = None


class ActiveQueueEntryRead(QueueEntryRead):
    submitted_by_display_name: str | None = None
    source: QueueEntrySourceLiteral


class ActiveQueueListResponse(BaseModel):
    now_playing: ActiveQueueEntryRead | None = None
    queued: list[ActiveQueueEntryRead] = Field(default_factory=list)


class VoteCountUpdateRequest(BaseModel):
    vote_count: int = Field(ge=0)


class ParticipantLimitsRead(BaseModel):
    max_pending_submissions: int
    max_searches_10_minutes: int
    max_votes_10_minutes: int


class StateResponse(BaseModel):
    revision: int
    now_playing: QueueEntryRead | None = None
    queue: list[QueueEntryRead]
    event_config: EventConfigSummary
    participant_limits: ParticipantLimitsRead


PlaybackAudioMode = Literal["idle", "sound", "muted"]


class PlaybackStatusRead(BaseModel):
    audio_mode: PlaybackAudioMode
    updated_at: datetime


class PlaybackStatusUpdate(BaseModel):
    audio_mode: PlaybackAudioMode


class PendingListResponse(BaseModel):
    entries: list[PendingQueueEntryRead]


class HistoryQueueEntryRead(QueueEntryRead):
    finished_at: datetime
    submitted_by_display_name: str | None = None
    source: QueueEntrySourceLiteral


class HistoryListResponse(BaseModel):
    entries: list[HistoryQueueEntryRead]
    total: int
    page: int
    page_size: int


class FillerReserveEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    youtube_video_id: str
    title: str
    thumbnail_url: str | None = None
    duration_sec: int | None = None
    position: int
    created_at: datetime


class FillerReserveListResponse(BaseModel):
    entries: list[FillerReserveEntryRead]


class FillerReserveAddRequest(BaseModel):
    youtube_url_or_id: str = Field(min_length=1, max_length=500)
    search_query: str | None = Field(default=None, max_length=500)


class OperatorQueueSubmitRequest(BaseModel):
    youtube_url_or_id: str = Field(min_length=1, max_length=500)
    search_query: str | None = Field(default=None, max_length=500)


class FillerReserveReorderRequest(BaseModel):
    ordered_ids: list[str] = Field(min_length=1)


class FillerReserveEnqueueBatchRequest(BaseModel):
    ids: list[str] = Field(min_length=1)


class FillerReserveBatchLineError(BaseModel):
    line: int = Field(ge=1)
    detail: str


class FillerReserveBatchValidation(BaseModel):
    add_count: int = Field(ge=0)
    skipped_in_reserve: int = Field(ge=0)
    skipped_in_queue: int = Field(ge=0)
    skipped_unresolvable: int = Field(ge=0)
    skipped_capacity: int = Field(ge=0)
    can_confirm: bool
    errors: list[FillerReserveBatchLineError]


class FillerReservePlaylistRequest(BaseModel):
    youtube_playlist_url: str = Field(min_length=1, max_length=500)


# Backward-compatible aliases (deprecated)
FillerReserveImportLineError = FillerReserveBatchLineError
FillerReserveImportValidation = FillerReserveBatchValidation


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
    searches_remaining: int
    votes_quota_reset_at: datetime | None = None
    searches_quota_reset_at: datetime | None = None
    max_pending_submissions: int
    max_searches_10_minutes: int
    max_votes_10_minutes: int
    event_config: EventConfigSummary
    participant_limits: ParticipantLimitsRead


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


class ApiKeyUsageItem(BaseModel):
    index: int
    label: str
    masked_suffix: str
    used_count: int
    remaining_count: int
    daily_limit: int
    exhausted: bool


class ApiKeyUsageListResponse(BaseModel):
    keys: list[ApiKeyUsageItem]
    daily_limit: int
    quota_day: str
    next_reset_at: str


class QueueStatusCounts(BaseModel):
    pending_review: int
    queued: int
    playing: int
    played: int
    rejected: int


class ParticipantRankingItem(BaseModel):
    participant_id: str
    display_name: str
    count: int


class SongRankingItem(BaseModel):
    youtube_video_id: str
    title: str
    vote_count: int


class AdminStatsResponse(BaseModel):
    participants_active_count: int
    total_submissions: int
    total_votes_cast: int
    distinct_voted_songs_count: int
    queue_counts: QueueStatusCounts
    top_submitters: list[ParticipantRankingItem]
    top_voters: list[ParticipantRankingItem]
    top_songs: list[SongRankingItem]

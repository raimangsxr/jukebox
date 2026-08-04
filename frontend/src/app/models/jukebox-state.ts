export interface EventConfigSummary {
  name: string;
  subtitle: string;
  app_height_px: number;
  theme: string;
  queue_visible_count: number;
}

export interface ParticipantLimits {
  max_pending_submissions: number;
  max_searches_10_minutes: number;
  max_votes_10_minutes: number;
}

export interface QueueEntryRead {
  id: string;
  youtube_video_id: string;
  title: string;
  thumbnail_url: string | null;
  vote_count: number;
  position: number | null;
  status: string;
  rejection_reason?: string | null;
  duration_sec?: number | null;
  created_at: string;
  priority?: 'normal' | 'low';
}

export interface HistoryQueueEntryRead extends QueueEntryRead {
  finished_at: string;
  submitted_by_display_name?: string | null;
  source: string;
}

export interface HistoryListResponse {
  entries: HistoryQueueEntryRead[];
  total: number;
  page: number;
  page_size: number;
}

export interface PendingQueueEntryRead extends QueueEntryRead {
  submitted_by_display_name?: string | null;
}

export interface StateResponse {
  revision: number;
  now_playing: QueueEntryRead | null;
  queue: QueueEntryRead[];
  event_config: EventConfigSummary;
  participant_limits: ParticipantLimits;
}

export interface ParticipantStateResponse extends StateResponse {
  votes_remaining: number;
  searches_remaining: number;
  votes_quota_reset_at: string | null;
  searches_quota_reset_at: string | null;
  max_pending_submissions: number;
  max_searches_10_minutes: number;
  max_votes_10_minutes: number;
}

export type NotificationEventType = 'song.approved' | 'song.up_next';

export interface NotificationEventRead {
  type: NotificationEventType;
  queue_entry_id: string;
  participant_id: string;
  title: string;
}

export interface PendingListResponse {
  entries: PendingQueueEntryRead[];
}

export interface ActiveQueueEntryRead extends QueueEntryRead {
  submitted_by_display_name?: string | null;
  source: string;
}

export interface ActiveQueueListResponse {
  now_playing: ActiveQueueEntryRead | null;
  queued: ActiveQueueEntryRead[];
}

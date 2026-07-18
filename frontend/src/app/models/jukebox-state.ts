export interface EventConfigSummary {
  name: string;
  subtitle: string;
  app_height_px: number;
  theme: string;
  queue_visible_count: number;
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
  created_at: string;
}

export interface StateResponse {
  revision: number;
  now_playing: QueueEntryRead | null;
  queue: QueueEntryRead[];
  event_config: EventConfigSummary;
}

export interface ParticipantStateResponse extends StateResponse {
  votes_remaining: number;
}

export type NotificationEventType = 'song.approved' | 'song.up_next';

export interface NotificationEventRead {
  type: NotificationEventType;
  queue_entry_id: string;
  participant_id: string;
  title: string;
}

export interface PendingListResponse {
  entries: QueueEntryRead[];
}

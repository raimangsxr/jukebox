export interface QueueStatusCounts {
  pending_review: number;
  queued: number;
  playing: number;
  rejected: number;
  played: number;
}

export interface ParticipantRankingItem {
  participant_id: string;
  display_name: string;
  count: number;
}

export interface SongRankingItem {
  youtube_video_id: string;
  title: string;
  vote_count: number;
}

export interface AdminStatsResponse {
  participants_active_count: number;
  total_submissions: number;
  total_votes_cast: number;
  distinct_voted_songs_count: number;
  queue_counts: QueueStatusCounts;
  top_submitters: ParticipantRankingItem[];
  top_voters: ParticipantRankingItem[];
  top_songs: SongRankingItem[];
}

export interface SearchConfigResponse {
  enabled: boolean;
}

export interface SearchResultItem {
  youtube_video_id: string;
  title: string;
  channel_title: string;
  thumbnail_url: string;
}

export interface SearchResponse {
  results: SearchResultItem[];
}

export interface EventConfigRead {
  name: string;
  subtitle: string;
  app_height_px: number;
  theme: string;
  queue_visible_count: number;
  updated_at: string;
}

export interface EventConfigUpdate {
  name: string;
  subtitle: string;
  app_height_px: number;
  theme: string;
  queue_visible_count: number;
}

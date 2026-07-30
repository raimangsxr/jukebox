export type QueueMode = 'moderated' | 'free';

export interface EventConfigRead {
  name: string;
  subtitle: string;
  app_height_px: number;
  theme: string;
  queue_visible_count: number;
  queue_mode: QueueMode;
  updated_at: string;
}

export interface EventConfigUpdate {
  name: string;
  subtitle: string;
  app_height_px: number;
  theme: string;
  queue_visible_count: number;
}

export interface QueueModeUpdate {
  queue_mode: QueueMode;
}

export type PlaybackAudioMode = 'idle' | 'sound' | 'muted';

export interface PlaybackStatusRead {
  audio_mode: PlaybackAudioMode;
  updated_at: string;
}

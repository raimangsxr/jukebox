export type { ParticipantStateResponse, StateResponse } from './jukebox-state';

export interface ParticipantRead {
  id: string;
  display_name: string;
  email?: string | null;
  avatar_url?: string | null;
  created_at: string;
}

export interface ParticipantMeResponse {
  participant: ParticipantRead;
}

export interface VoteResponse {
  id: string;
  votes_remaining: number;
  state?: import('./jukebox-state').ParticipantStateResponse;
}

import { ParticipantLimits } from './models/jukebox-state';

export type { ParticipantLimits };

export function votesRemainingLabel(remaining: number, maxVotes: number): string {
  return `${remaining} de ${maxVotes} votos disponibles (cada 10 min)`;
}

export function voteLimitExceededMessage(maxVotes: number): string {
  return `Has agotado tus ${maxVotes} votos. Espera unos minutos para votar de nuevo.`;
}

export function searchRateLimitMessage(maxSearches: number): string {
  return `Has alcanzado el límite de ${maxSearches} búsquedas cada 10 minutos. Espera un poco o pega un enlace.`;
}

export function pendingSubmissionLimitMessage(maxPending: number): string {
  return `Has alcanzado el límite de canciones pendientes (${maxPending}).`;
}

export function qrPanelVoteHint(maxVotes: number): string {
  return `${maxVotes} voto${maxVotes === 1 ? '' : 's'} cada 10 minutos`;
}

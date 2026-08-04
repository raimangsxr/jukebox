import { ParticipantLimits } from './models/jukebox-state';
import {
  formatCountdownMmSs,
  secondsUntil,
  shouldShowQuotaCountdown,
} from './limit-countdown.util';

export type { ParticipantLimits };

export function votesRemainingLabel(
  remaining: number,
  maxVotes: number,
  resetAt?: string | null,
  nowMs?: number
): string {
  const base = `${remaining} de ${maxVotes} votos disponibles`;
  if (resetAt && shouldShowQuotaCountdown(resetAt, nowMs)) {
    const countdown = formatCountdownMmSs(secondsUntil(resetAt, nowMs));
    return `${base} · Cupo completo en ${countdown}`;
  }
  return base;
}

export function searchesRemainingLabel(
  remaining: number,
  maxSearches: number,
  resetAt?: string | null,
  nowMs?: number
): string {
  const base = `${remaining} de ${maxSearches} búsquedas disponibles`;
  if (resetAt && shouldShowQuotaCountdown(resetAt, nowMs)) {
    const countdown = formatCountdownMmSs(secondsUntil(resetAt, nowMs));
    return `${base} · Cupo completo en ${countdown}`;
  }
  return base;
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

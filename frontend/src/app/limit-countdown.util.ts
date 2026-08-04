export function secondsUntil(
  isoEndsAt: string | null | undefined,
  nowMs: number = Date.now()
): number {
  if (!isoEndsAt) {
    return 0;
  }
  const end = Date.parse(isoEndsAt);
  if (Number.isNaN(end)) {
    return 0;
  }
  return Math.max(0, Math.ceil((end - nowMs) / 1000));
}

export function formatCountdownMmSs(totalSeconds: number): string {
  const seconds = Math.max(0, totalSeconds);
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
}

export function shouldShowQuotaCountdown(
  resetAt: string | null | undefined,
  nowMs: number = Date.now()
): boolean {
  return secondsUntil(resetAt, nowMs) > 0;
}

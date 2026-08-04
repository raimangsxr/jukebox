import { describe, expect, it } from 'vitest';

import {
  formatCountdownMmSs,
  secondsUntil,
  shouldShowQuotaCountdown,
} from './limit-countdown.util';

describe('limit-countdown.util', () => {
  it('formats MM:SS with zero padding', () => {
    expect(formatCountdownMmSs(0)).toBe('00:00');
    expect(formatCountdownMmSs(65)).toBe('01:05');
    expect(formatCountdownMmSs(599)).toBe('09:59');
  });

  it('returns zero seconds for null or past reset_at', () => {
    const now = Date.parse('2026-01-01T12:00:00.000Z');
    expect(secondsUntil(null, now)).toBe(0);
    expect(secondsUntil('2026-01-01T11:59:00.000Z', now)).toBe(0);
    expect(shouldShowQuotaCountdown('2026-01-01T11:59:00.000Z', now)).toBe(false);
  });

  it('counts up to future reset_at', () => {
    const now = Date.parse('2026-01-01T12:00:00.000Z');
    const resetAt = '2026-01-01T12:10:30.000Z';
    expect(secondsUntil(resetAt, now)).toBe(630);
    expect(shouldShowQuotaCountdown(resetAt, now)).toBe(true);
  });

  it('treats zero boundary as expired', () => {
    const now = Date.parse('2026-01-01T12:10:00.000Z');
    const resetAt = '2026-01-01T12:10:00.000Z';
    expect(secondsUntil(resetAt, now)).toBe(0);
    expect(shouldShowQuotaCountdown(resetAt, now)).toBe(false);
  });
});

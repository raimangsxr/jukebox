import { describe, expect, it } from 'vitest';

import {
  searchesRemainingLabel,
  voteLimitExceededMessage,
  votesRemainingLabel,
} from './participant-limits.util';

const NOW = Date.parse('2026-01-01T12:00:00.000Z');
const RESET_AT = '2026-01-01T12:10:00.000Z';

describe('participant-limits.util', () => {
  it('shows vote label without countdown when no window', () => {
    expect(votesRemainingLabel(2, 2, null, NOW)).toBe('2 de 2 votos disponibles');
    expect(votesRemainingLabel(1, 2, null, NOW)).toBe('1 de 2 votos disponibles');
  });

  it('appends countdown when vote window is active', () => {
    const label = votesRemainingLabel(1, 2, RESET_AT, NOW);
    expect(label).toContain('1 de 2 votos disponibles');
    expect(label).toContain('Cupo completo en 10:00');
  });

  it('shows search label without countdown when no window', () => {
    expect(searchesRemainingLabel(10, 10, null, NOW)).toBe(
      '10 de 10 búsquedas disponibles'
    );
  });

  it('appends countdown when search window is active', () => {
    const label = searchesRemainingLabel(9, 10, RESET_AT, NOW);
    expect(label).toContain('9 de 10 búsquedas disponibles');
    expect(label).toContain('Cupo completo en 10:00');
  });

  it('keeps limit-exceeded message coherent with active countdown (FR-009)', () => {
    expect(voteLimitExceededMessage(2)).toContain('2 votos');
    const label = votesRemainingLabel(0, 2, RESET_AT, NOW);
    expect(label).toContain('0 de 2 votos disponibles');
    expect(label).toContain('Cupo completo en');
  });
});

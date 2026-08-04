import { describe, expect, it } from 'vitest';

import {
  activeQueueEmptyCopy,
  parseVoteCountInput,
  queueSourceLabel,
  queueStatusLabel,
} from './admin-queue.util';

describe('admin-queue.util', () => {
  it('maps known sources to Spanish labels', () => {
    expect(queueSourceLabel('participant')).toBe('Participante');
    expect(queueSourceLabel('operator_filler')).toBe('Relleno');
  });

  it('labels playing and queued statuses', () => {
    expect(queueStatusLabel('playing', true)).toBe('Sonando');
    expect(queueStatusLabel('queued', false)).toBe('En cola');
  });

  it('provides empty queue copy', () => {
    expect(activeQueueEmptyCopy()).toContain('No hay canciones');
  });

  it('validates vote count input', () => {
    expect(parseVoteCountInput('3')).toEqual({ valid: true, value: 3 });
    expect(parseVoteCountInput('')).toEqual({
      valid: false,
      message: 'Introduce un número de votos.',
    });
    expect(parseVoteCountInput('abc')).toEqual({
      valid: false,
      message: 'El valor debe ser un número entero.',
    });
    expect(parseVoteCountInput('-1')).toEqual({
      valid: false,
      message: 'Los votos deben ser un entero mayor o igual a 0.',
    });
  });
});

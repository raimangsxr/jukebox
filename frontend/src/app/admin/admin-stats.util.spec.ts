import { describe, expect, it } from 'vitest';

import {
  emptyRankingCopy,
  participantDisplayLabel,
  shouldFetchStatsOnPanelChange,
} from './admin-stats.util';

describe('admin-stats.util', () => {
  it('does not fetch stats when panel stays collapsed', () => {
    expect(shouldFetchStatsOnPanelChange('stats', false)).toBe(false);
    expect(shouldFetchStatsOnPanelChange('history', true)).toBe(false);
    expect(shouldFetchStatsOnPanelChange('history', false)).toBe(false);
  });

  it('fetches stats only when estadísticas panel expands', () => {
    expect(shouldFetchStatsOnPanelChange('stats', true)).toBe(true);
  });

  it('uses API display_name for ranking labels', () => {
    expect(
      participantDisplayLabel({
        participant_id: '1',
        display_name: 'Ana',
        count: 3,
      })
    ).toBe('Ana');
    expect(
      participantDisplayLabel({
        participant_id: '2',
        display_name: '   ',
        count: 1,
      })
    ).toBe('Participante');
  });

  it('provides Spanish empty-state copy', () => {
    expect(emptyRankingCopy()).toBe('Sin datos aún');
  });
});

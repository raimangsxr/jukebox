import { ParticipantRankingItem } from '../models/admin-stats';

export function shouldFetchStatsOnPanelChange(panelId: string, expanded: boolean): boolean {
  return panelId === 'stats' && expanded;
}

export function participantDisplayLabel(item: ParticipantRankingItem): string {
  const name = item.display_name?.trim();
  if (name) {
    return name;
  }
  return 'Participante';
}

export function emptyRankingCopy(): string {
  return 'Sin datos aún';
}

export function emptySummaryCopy(): string {
  return 'Sin actividad registrada';
}

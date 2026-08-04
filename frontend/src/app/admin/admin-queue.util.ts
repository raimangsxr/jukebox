export type QueueEntrySource =
  | 'participant'
  | 'operator_filler'
  | 'operator_direct'
  | 'auto_inject'
  | 'operator_requeue';

const SOURCE_LABELS: Record<QueueEntrySource, string> = {
  participant: 'Participante',
  operator_filler: 'Relleno',
  operator_direct: 'Operador directo',
  auto_inject: 'Inyección automática',
  operator_requeue: 'Re-encolado',
};

export function queueSourceLabel(source: string): string {
  return SOURCE_LABELS[source as QueueEntrySource] ?? source;
}

export function queueStatusLabel(status: string, isNowPlaying: boolean): string {
  if (isNowPlaying || status === 'playing') {
    return 'Sonando';
  }
  if (status === 'queued') {
    return 'En cola';
  }
  return status;
}

export function activeQueueEmptyCopy(): string {
  return 'No hay canciones en la cola de reproducción.';
}

export function parseVoteCountInput(raw: string): { valid: true; value: number } | { valid: false; message: string } {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { valid: false, message: 'Introduce un número de votos.' };
  }
  if (!/^-?\d+$/.test(trimmed)) {
    return { valid: false, message: 'El valor debe ser un número entero.' };
  }
  const value = Number(trimmed);
  if (!Number.isInteger(value) || value < 0) {
    return { valid: false, message: 'Los votos deben ser un entero mayor o igual a 0.' };
  }
  return { valid: true, value };
}

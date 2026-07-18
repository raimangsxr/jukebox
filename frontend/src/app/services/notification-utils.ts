import { NotificationEventRead } from '../models/jukebox-state';

export function notificationTargetsParticipant(
  participantId: string | null,
  event: NotificationEventRead
): boolean {
  return Boolean(participantId && event.participant_id === participantId);
}

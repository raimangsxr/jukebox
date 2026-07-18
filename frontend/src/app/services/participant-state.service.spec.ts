import { describe, expect, it, vi } from 'vitest';

import { NotificationEventRead } from '../models/jukebox-state';
import { NotificationToastService } from './notification-toast.service';
import { notificationTargetsParticipant } from './notification-utils';

const sampleEvent: NotificationEventRead = {
  type: 'song.up_next',
  queue_entry_id: 'entry-1',
  participant_id: 'participant-1',
  title: 'Next Song'
};

describe('notificationTargetsParticipant', () => {
  it('matches the current participant', () => {
    expect(notificationTargetsParticipant('participant-1', sampleEvent)).toBe(true);
  });

  it('ignores events for other participants', () => {
    expect(notificationTargetsParticipant('participant-2', sampleEvent)).toBe(false);
  });

  it('ignores events when not signed in', () => {
    expect(notificationTargetsParticipant(null, sampleEvent)).toBe(false);
  });
});

describe('ParticipantStateService notification listener', () => {
  it('forwards matching notifications to the toast service', () => {
    const toast = new NotificationToastService();
    const enqueueSpy = vi.spyOn(toast, 'enqueue');

    if (notificationTargetsParticipant('participant-1', sampleEvent)) {
      toast.enqueue(sampleEvent);
    }
    expect(enqueueSpy).toHaveBeenCalledWith(sampleEvent);

    enqueueSpy.mockClear();
    if (notificationTargetsParticipant('participant-2', sampleEvent)) {
      toast.enqueue(sampleEvent);
    }
    expect(enqueueSpy).not.toHaveBeenCalled();

    toast.ngOnDestroy();
  });
});

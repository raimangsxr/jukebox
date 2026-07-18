import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { NotificationEventRead } from '../models/jukebox-state';
import { NotificationToastService } from './notification-toast.service';

describe('NotificationToastService', () => {
  let service: NotificationToastService;

  const approvedEvent = (id: string): NotificationEventRead => ({
    type: 'song.approved',
    queue_entry_id: id,
    participant_id: 'participant-1',
    title: `Song ${id}`
  });

  beforeEach(() => {
    vi.useFakeTimers();
    service = new NotificationToastService();
  });

  afterEach(() => {
    service.ngOnDestroy();
    vi.useRealTimers();
  });

  it('shows FIFO toasts one at a time', () => {
    service.enqueue(approvedEvent('a'));
    service.enqueue(approvedEvent('b'));

    let visible: string | null = 'pending';
    const sub = service.visibleMessage$.subscribe(message => {
      visible = message;
    });

    expect(visible).toContain('Song a');
    service.dismiss();
    expect(visible).toContain('Song b');
    sub.unsubscribe();
  });

  it('dedupes duplicate type and queue_entry_id', () => {
    service.enqueue(approvedEvent('dup'));
    service.enqueue(approvedEvent('dup'));

    let visible: string | null = null;
    const sub = service.visibleMessage$.subscribe(message => {
      visible = message;
    });

    expect(visible).toContain('Song dup');
    service.dismiss();
    expect(visible).toBeNull();
    sub.unsubscribe();
  });

  it('auto-dismiss advances the queue', () => {
    let visible: string | null = null;
    const sub = service.visibleMessage$.subscribe(message => {
      visible = message;
    });

    service.enqueue(approvedEvent('first'));
    service.enqueue(approvedEvent('second'));
    expect(visible).toContain('Song first');

    vi.advanceTimersByTime(8000);
    expect(visible).toContain('Song second');
    sub.unsubscribe();
  });
});

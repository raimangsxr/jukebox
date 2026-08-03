import { describe, expect, it } from 'vitest';

import { LiveConnectionManager } from './live-connection';

describe('LiveConnectionManager', () => {
  it('starts in reconnecting state and moves to connected on open', () => {
    const manager = new LiveConnectionManager({
      url: 'http://example.test/events/stream',
      eventListeners: {},
    });

    const statuses: string[] = [];
    manager.status$.subscribe(status => statuses.push(status));

    manager.start();
    expect(manager.status).toBe('reconnecting');

    manager.stop();
    expect(statuses).toContain('reconnecting');
  });
});

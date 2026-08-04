import '@angular/compiler';
import { Injector, runInInjectionContext, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';

import { AdminComponent } from './admin.component';
import { AuthService } from '../services/auth.service';
import { DisplayStateService } from '../services/display-state.service';
import { EventConfigService } from '../services/event-config.service';
import { FillerReserveService } from '../services/filler-reserve.service';
import { QueueAdminService } from '../services/queue-admin.service';
import { AdminStatsService } from '../services/admin-stats.service';
import adminTemplate from './admin.component.html?raw';

function sectionBetween(title: string, nextTitle: string): string {
  const start = adminTemplate.indexOf(`title="${title}"`);
  const end = adminTemplate.indexOf(`title="${nextTitle}"`, start);
  return adminTemplate.slice(start, end);
}

function makeAdmin(): AdminComponent {
  const http = {
    get: vi.fn(() => of({ tokens: [] })),
    post: vi.fn(),
    delete: vi.fn(),
    put: vi.fn(),
  };
  const queueAdmin = {
    getPending: vi.fn(() => of({ entries: [] })),
    getHistory: vi.fn(() => of({ entries: [], total: 0, page: 1, page_size: 25 })),
    getActiveQueue: vi.fn(() => of({ now_playing: null, queued: [] })),
    skipOrStart: vi.fn(),
  };
  const displayState = {
    start: vi.fn(),
    stop: vi.fn(),
    state$: of(null),
    apiKeyUsage$: of(null),
    playbackStatus$: of(null),
    connectionStatus$: of('connected'),
    snapshot: null,
    applyState: vi.fn(),
  };
  const injector = Injector.create({
    providers: [
      { provide: HttpClient, useValue: http },
      { provide: AuthService, useValue: { logout: vi.fn(() => of(null)) } },
      { provide: Router, useValue: { navigate: vi.fn() } },
      { provide: QueueAdminService, useValue: queueAdmin },
      { provide: AdminStatsService, useValue: { getStats: vi.fn(() => of(null)) } },
      { provide: FillerReserveService, useValue: { list: vi.fn(() => of({ entries: [] })) } },
      { provide: DisplayStateService, useValue: displayState },
      {
        provide: EventConfigService,
        useValue: {
          getConfig: vi.fn(() =>
            of({
              name: 'Test',
              subtitle: '',
              app_height_px: 800,
              theme: 'dark',
              queue_visible_count: 5,
              queue_mode: 'moderated',
              filler_auto_inject_enabled: true,
              updated_at: '2026-01-01T00:00:00Z',
            })
          ),
        },
      },
      { provide: ChangeDetectorRef, useValue: { markForCheck: vi.fn() } },
    ],
  });
  return runInInjectionContext(injector, () => new AdminComponent());
}

describe('AdminComponent panel defaults', () => {
  it('expands Moderación only on init', () => {
    const component = makeAdmin();
    expect(component.panelExpanded.moderation).toBe(true);
    expect(component.panelExpanded.queue).toBe(false);
    expect(component.panelExpanded.history).toBe(false);
    expect(component.panelExpanded.stats).toBe(false);
    expect(component.panelExpanded.reserve).toBe(false);
    expect(component.panelExpanded.apiKeys).toBe(false);
    expect(component.panelExpanded.event).toBe(false);
    expect(component.panelExpanded.tokens).toBe(false);
  });
});

describe('AdminComponent playback controls placement', () => {
  it('keeps playback controls only in Cola de reproducción', () => {
    const moderation = sectionBetween('Moderación', 'Cola de reproducción');
    const queue = sectionBetween('Cola de reproducción', 'Historial');

    expect(moderation).not.toContain('Iniciar reproducción');
    expect(moderation).not.toContain('Saltar canción');
    expect(queue).toContain('Iniciar reproducción');
    expect(queue).toContain('Saltar canción');
  });
});

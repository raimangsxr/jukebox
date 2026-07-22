import '@angular/compiler';
import { HttpClient } from '@angular/common/http';
import { Injector } from '@angular/core';
import { firstValueFrom, of } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';

import { EventConfigService } from './event-config.service';

function makeService(http: Partial<HttpClient>): EventConfigService {
  const injector = Injector.create({
    providers: [
      { provide: HttpClient, useValue: http },
      { provide: EventConfigService, deps: [] as never }
    ]
  });
  return injector.get(EventConfigService);
}

describe('EventConfigService', () => {
  it('GETs the event-config endpoint', async () => {
    const http = { get: vi.fn(() => of({ name: 'Fiesta' })) } as Partial<HttpClient>;
    const service = makeService(http);
    const config = await firstValueFrom(service.getConfig());
    expect((http.get as ReturnType<typeof vi.fn>).mock.calls[0][0]).toContain(
      '/event-config'
    );
    expect(config).toEqual({ name: 'Fiesta' });
  });

  it('PUTs the update payload to the event-config endpoint', async () => {
    const http = {
      put: vi.fn(() => of({ name: 'Nuevo' }))
    } as Partial<HttpClient>;
    const service = makeService(http);
    const payload = {
      name: 'Nuevo',
      subtitle: 's',
      app_height_px: 800,
      theme: 'dark',
      queue_visible_count: 5
    };
    await firstValueFrom(service.updateConfig(payload));
    const putMock = http.put as ReturnType<typeof vi.fn>;
    expect(putMock.mock.calls[0][0]).toContain('/event-config');
    expect(putMock.mock.calls[0][1]).toEqual(payload);
  });
});

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  EventConfigRead,
  EventConfigUpdate,
  FillerAutoInjectUpdate,
  QueueMode,
  QueueModeUpdate
} from '../models/event-config';

@Injectable({ providedIn: 'root' })
export class EventConfigService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  getConfig(): Observable<EventConfigRead> {
    return this.http.get<EventConfigRead>(`${this.baseUrl}/event-config`);
  }

  updateConfig(payload: EventConfigUpdate): Observable<EventConfigRead> {
    return this.http.put<EventConfigRead>(`${this.baseUrl}/event-config`, payload);
  }

  updateQueueMode(queue_mode: QueueMode): Observable<EventConfigRead> {
    const payload: QueueModeUpdate = { queue_mode };
    return this.http.put<EventConfigRead>(`${this.baseUrl}/event-config/queue-mode`, payload);
  }

  updateFillerAutoInject(enabled: boolean): Observable<EventConfigRead> {
    const payload: FillerAutoInjectUpdate = { filler_auto_inject_enabled: enabled };
    return this.http.put<EventConfigRead>(
      `${this.baseUrl}/event-config/filler-auto-inject`,
      payload
    );
  }
}

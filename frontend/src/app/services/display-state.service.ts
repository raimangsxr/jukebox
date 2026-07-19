import { HttpClient } from '@angular/common/http';
import { Injectable, OnDestroy, inject } from '@angular/core';
import { BehaviorSubject, Observable, Subscription, firstValueFrom } from 'rxjs';

import { environment } from '../../environments/environment';
import { StateResponse } from '../models/jukebox-state';
import { ApiKeyUsageListResponse } from '../models/youtube-api-key-usage';

@Injectable({ providedIn: 'root' })
export class DisplayStateService implements OnDestroy {

  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  private readonly stateSubject = new BehaviorSubject<StateResponse | null>(null);
  private readonly apiKeyUsageSubject =
    new BehaviorSubject<ApiKeyUsageListResponse | null>(null);
  private eventSource: EventSource | null = null;
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private started = false;

  readonly state$: Observable<StateResponse | null> = this.stateSubject.asObservable();
  readonly apiKeyUsage$: Observable<ApiKeyUsageListResponse | null> =
    this.apiKeyUsageSubject.asObservable();

  ngOnDestroy(): void {
    this.stop();
  }

  get snapshot(): StateResponse | null {
    return this.stateSubject.value;
  }

  get apiKeyUsageSnapshot(): ApiKeyUsageListResponse | null {
    return this.apiKeyUsageSubject.value;
  }

  async start(): Promise<void> {
    if (this.started) {
      return;
    }
    this.started = true;
    await this.refresh();
    this.connectSse();
  }

  stop(): void {
    this.started = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  applyState(state: import('../models/jukebox-state').StateResponse): void {
    this.stateSubject.next(state);
  }

  async refresh(): Promise<StateResponse> {
    const state = await firstValueFrom(
      this.http.get<StateResponse>(`${this.baseUrl}/state`)
    );
    this.stateSubject.next(state);
    return state;
  }

  async advancePlayback(): Promise<void> {
    try {
      const state = await firstValueFrom(
        this.http.post<StateResponse>(`${this.baseUrl}/queue/skip`, {})
      );
      this.stateSubject.next(state);
    } catch {
      // 409 when nothing to advance — ignore on natural video end
    }
  }

  private connectSse(): void {
    if (this.eventSource) {
      this.eventSource.close();
    }
    const url = `${this.baseUrl}/events/stream`;
    this.eventSource = new EventSource(url, { withCredentials: true });

    this.eventSource.addEventListener('state', (event: MessageEvent<string>) => {
      try {
        const state = JSON.parse(event.data) as StateResponse;
        this.stateSubject.next(state);
        this.reconnectAttempt = 0;
      } catch {
        // ignore malformed payloads
      }
    });

    this.eventSource.addEventListener('api_key_usage', (event: MessageEvent<string>) => {
      try {
        const usage = JSON.parse(event.data) as ApiKeyUsageListResponse;
        this.apiKeyUsageSubject.next(usage);
        this.reconnectAttempt = 0;
      } catch {
        // ignore malformed payloads
      }
    });

    this.eventSource.onerror = () => {
      this.eventSource?.close();
      this.eventSource = null;
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    if (!this.started) {
      return;
    }
    const delay = Math.min(1000 * 2 ** this.reconnectAttempt, 30000);
    this.reconnectAttempt += 1;
    this.reconnectTimer = setTimeout(() => this.connectSse(), delay);
  }
}

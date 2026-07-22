import { HttpClient } from '@angular/common/http';
import { Injectable, OnDestroy, inject } from '@angular/core';
import { BehaviorSubject, Observable, firstValueFrom } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  NotificationEventRead,
  ParticipantStateResponse,
  QueueEntryRead,
  StateResponse
} from '../models/jukebox-state';
import { NotificationToastService } from './notification-toast.service';
import { notificationTargetsParticipant } from './notification-utils';
import { ParticipantService } from './participant.service';
import { applyTheme } from '../theme.util';

@Injectable({ providedIn: 'root' })
export class ParticipantStateService implements OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;
  private readonly participantService = inject(ParticipantService);
  private readonly notificationToast = inject(NotificationToastService);

  private readonly stateSubject = new BehaviorSubject<ParticipantStateResponse | null>(null);
  private readonly submissionsSubject = new BehaviorSubject<QueueEntryRead[]>([]);
  private eventSource: EventSource | null = null;
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private started = false;
  private votesRemaining = 2;

  readonly state$: Observable<ParticipantStateResponse | null> =
    this.stateSubject.asObservable();

  readonly submissions$: Observable<QueueEntryRead[]> =
    this.submissionsSubject.asObservable();

  ngOnDestroy(): void {
    this.stop();
  }

  get snapshot(): ParticipantStateResponse | null {
    return this.stateSubject.value;
  }

  async start(): Promise<void> {
    if (this.started) {
      return;
    }
    this.started = true;
    await this.refresh();
    await this.refreshSubmissions();
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

  async refresh(): Promise<ParticipantStateResponse> {
    const state = await firstValueFrom(
      this.http.get<ParticipantStateResponse>(`${this.baseUrl}/participant/state`)
    );
    this.votesRemaining = state.votes_remaining;
    applyTheme(state.event_config?.theme);
    this.stateSubject.next(state);
    return state;
  }

  async refreshSubmissions(): Promise<QueueEntryRead[]> {
    const response = await firstValueFrom(
      this.http.get<{ entries: QueueEntryRead[] }>(
        `${this.baseUrl}/participant/submissions`
      )
    );
    this.submissionsSubject.next(response.entries);
    return response.entries;
  }

  get submissionsSnapshot(): QueueEntryRead[] {
    return this.submissionsSubject.value;
  }

  applyVoteResponse(votesRemaining: number, state?: ParticipantStateResponse): void {
    this.votesRemaining = votesRemaining;
    if (state) {
      this.stateSubject.next(state);
    } else {
      const current = this.stateSubject.value;
      if (current) {
        this.stateSubject.next({ ...current, votes_remaining: votesRemaining });
      }
    }
  }

  handleNotificationEvent(
    event: NotificationEventRead,
    participantId: string | null
  ): void {
    if (!notificationTargetsParticipant(participantId, event)) {
      return;
    }
    this.notificationToast.enqueue(event);
  }

  private connectSse(): void {
    if (this.eventSource) {
      this.eventSource.close();
    }
    const url = `${this.baseUrl}/events/stream`;
    this.eventSource = new EventSource(url, { withCredentials: true });

    this.eventSource.addEventListener('state', (event: MessageEvent<string>) => {
      try {
        const sseState = JSON.parse(event.data) as StateResponse;
        const current = this.stateSubject.value;
        const merged: ParticipantStateResponse = {
          revision: sseState.revision,
          now_playing: sseState.now_playing,
          queue: sseState.queue,
          event_config: sseState.event_config,
          votes_remaining: current?.votes_remaining ?? this.votesRemaining,
          max_pending_submissions: current?.max_pending_submissions ?? 2,
        };
        applyTheme(merged.event_config?.theme);
        this.stateSubject.next(merged);
        void this.refreshSubmissions();
        this.reconnectAttempt = 0;
      } catch {
        // ignore malformed payloads
      }
    });

    this.eventSource.addEventListener('notification', (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as NotificationEventRead;
        this.handleNotificationEvent(
          payload,
          this.participantService.participant()?.id ?? null
        );
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
    this.reconnectTimer = setTimeout(async () => {
      try {
        await this.refresh();
      } catch {
        // keep last merged state; reconnect SSE anyway
      }
      this.connectSse();
    }, delay);
  }
}

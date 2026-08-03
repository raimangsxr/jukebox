import { HttpClient } from '@angular/common/http';
import { Injectable, OnDestroy, inject } from '@angular/core';
import { BehaviorSubject, Observable, firstValueFrom } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  NotificationEventRead,
  ParticipantStateResponse,
  QueueEntryRead,
  StateResponse,
} from '../models/jukebox-state';
import { NotificationToastService } from './notification-toast.service';
import { notificationTargetsParticipant } from './notification-utils';
import { ParticipantService } from './participant.service';
import { applyTheme } from '../theme.util';
import { LiveConnectionManager, LiveConnectionStatus } from './live-connection';

@Injectable({ providedIn: 'root' })
export class ParticipantStateService implements OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;
  private readonly participantService = inject(ParticipantService);
  private readonly notificationToast = inject(NotificationToastService);

  private readonly stateSubject = new BehaviorSubject<ParticipantStateResponse | null>(null);
  private readonly submissionsSubject = new BehaviorSubject<QueueEntryRead[]>([]);
  private readonly connectionStatusSubject =
    new BehaviorSubject<LiveConnectionStatus>('reconnecting');
  private liveConnection: LiveConnectionManager | null = null;
  private started = false;
  private votesRemaining = 2;

  readonly state$: Observable<ParticipantStateResponse | null> =
    this.stateSubject.asObservable();

  readonly submissions$: Observable<QueueEntryRead[]> =
    this.submissionsSubject.asObservable();

  readonly connectionStatus$: Observable<LiveConnectionStatus> =
    this.connectionStatusSubject.asObservable();

  ngOnDestroy(): void {
    this.stop();
  }

  get snapshot(): ParticipantStateResponse | null {
    return this.stateSubject.value;
  }

  get connectionStatus(): LiveConnectionStatus {
    return this.connectionStatusSubject.value;
  }

  async start(): Promise<void> {
    if (this.started) {
      return;
    }
    this.started = true;
    await this.refresh();
    await this.refreshSubmissions();
    this.startLiveConnection();
  }

  stop(): void {
    this.started = false;
    this.liveConnection?.stop();
    this.liveConnection = null;
    this.connectionStatusSubject.next('reconnecting');
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

  private startLiveConnection(): void {
    this.liveConnection?.stop();
    this.liveConnection = new LiveConnectionManager({
      url: `${this.baseUrl}/events/stream`,
      withCredentials: true,
      onPoll: async () => {
        await this.refresh();
        await this.refreshSubmissions();
      },
      eventListeners: {
        state: (event: MessageEvent<string>) => {
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
              max_searches_10_minutes: current?.max_searches_10_minutes ?? 10,
              max_votes_10_minutes: current?.max_votes_10_minutes ?? 2,
            };
            applyTheme(merged.event_config?.theme);
            this.stateSubject.next(merged);
            void this.refreshSubmissions();
          } catch {
            // ignore malformed payloads
          }
        },
        notification: (event: MessageEvent<string>) => {
          try {
            const payload = JSON.parse(event.data) as NotificationEventRead;
            this.handleNotificationEvent(
              payload,
              this.participantService.participant()?.id ?? null
            );
          } catch {
            // ignore malformed payloads
          }
        },
      },
    });
    this.liveConnection.status$.subscribe(status => {
      this.connectionStatusSubject.next(status);
    });
    this.liveConnection.start();
  }
}

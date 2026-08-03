import { BehaviorSubject } from 'rxjs';

export type LiveConnectionStatus = 'connected' | 'reconnecting' | 'fallback';

const MAX_SSE_RETRIES = 3;
const POLL_INTERVAL_MS = 15_000;

export interface LiveConnectionOptions {
  url: string;
  withCredentials?: boolean;
  onConnected?: () => void;
  onPoll?: () => void | Promise<void>;
  eventListeners?: Record<string, (event: MessageEvent<string>) => void>;
}

export class LiveConnectionManager {
  private eventSource: EventSource | null = null;
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private started = false;
  private readonly options: LiveConnectionOptions;

  readonly status$ = new BehaviorSubject<LiveConnectionStatus>('reconnecting');

  constructor(options: LiveConnectionOptions) {
    this.options = options;
  }

  get status(): LiveConnectionStatus {
    return this.status$.value;
  }

  start(): void {
    if (this.started) {
      return;
    }
    this.started = true;
    this.connectSse();
  }

  stop(): void {
    this.started = false;
    this.clearReconnectTimer();
    this.stopPolling();
    this.closeEventSource();
    this.status$.next('reconnecting');
  }

  private connectSse(): void {
    if (!this.started) {
      return;
    }
    this.closeEventSource();
    this.status$.next(this.reconnectAttempt > 0 ? 'reconnecting' : 'reconnecting');

    const source = new EventSource(this.options.url, {
      withCredentials: this.options.withCredentials ?? true,
    });
    this.eventSource = source;

    source.onopen = () => {
      if (!this.started || this.eventSource !== source) {
        return;
      }
      this.reconnectAttempt = 0;
      this.stopPolling();
      this.status$.next('connected');
      this.options.onConnected?.();
    };

    for (const [eventName, handler] of Object.entries(this.options.eventListeners ?? {})) {
      source.addEventListener(eventName, handler);
    }

    source.onerror = () => {
      if (!this.started || this.eventSource !== source) {
        return;
      }
      this.closeEventSource();
      if (this.pollTimer) {
        this.status$.next('fallback');
        this.clearReconnectTimer();
        this.reconnectTimer = setTimeout(() => {
          this.reconnectAttempt = 0;
          this.connectSse();
        }, POLL_INTERVAL_MS);
        return;
      }
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    if (!this.started) {
      return;
    }
    this.reconnectAttempt += 1;
    if (this.reconnectAttempt > MAX_SSE_RETRIES) {
      this.startPolling();
      return;
    }
    this.status$.next('reconnecting');
    const delay = Math.min(1000 * 2 ** (this.reconnectAttempt - 1), 30_000);
    this.clearReconnectTimer();
    this.reconnectTimer = setTimeout(() => this.connectSse(), delay);
  }

  private startPolling(): void {
    if (!this.started) {
      return;
    }
    if (!this.pollTimer) {
      this.status$.next('fallback');
      const poll = () => {
        void Promise.resolve(this.options.onPoll?.()).catch(() => {
          // keep last known state during fallback polling
        });
      };
      poll();
      this.pollTimer = setInterval(poll, POLL_INTERVAL_MS);
    }
    this.clearReconnectTimer();
    this.reconnectAttempt = 0;
    this.reconnectTimer = setTimeout(() => this.connectSse(), POLL_INTERVAL_MS);
  }

  private stopPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private closeEventSource(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

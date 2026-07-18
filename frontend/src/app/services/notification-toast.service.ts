import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

import { NotificationEventRead } from '../models/jukebox-state';

const AUTO_DISMISS_MS = 8000;

const TOAST_TEMPLATES: Record<NotificationEventRead['type'], (title: string) => string> = {
  'song.approved': title => `«${title}» ha sido aprobada y está en cola.`,
  'song.up_next': title => `«${title}» es la siguiente canción.`
};

@Injectable({ providedIn: 'root' })
export class NotificationToastService implements OnDestroy {
  private readonly visibleSubject = new BehaviorSubject<string | null>(null);
  private readonly pending: NotificationEventRead[] = [];
  private readonly shownKeys = new Set<string>();
  private dismissTimer: ReturnType<typeof setTimeout> | null = null;

  readonly visibleMessage$: Observable<string | null> = this.visibleSubject.asObservable();

  ngOnDestroy(): void {
    this.clearDismissTimer();
  }

  enqueue(event: NotificationEventRead): void {
    const key = this.dedupeKey(event);
    if (this.shownKeys.has(key)) {
      return;
    }
    this.shownKeys.add(key);
    this.pending.push(event);
    this.showNextIfIdle();
  }

  dismiss(): void {
    this.clearDismissTimer();
    this.visibleSubject.next(null);
    this.showNextIfIdle();
  }

  formatMessage(event: NotificationEventRead): string {
    return TOAST_TEMPLATES[event.type](event.title);
  }

  private dedupeKey(event: NotificationEventRead): string {
    return `${event.type}:${event.queue_entry_id}`;
  }

  private showNextIfIdle(): void {
    if (this.visibleSubject.value !== null || this.pending.length === 0) {
      return;
    }
    const next = this.pending.shift();
    if (!next) {
      return;
    }
    this.visibleSubject.next(this.formatMessage(next));
    this.dismissTimer = setTimeout(() => this.dismiss(), AUTO_DISMISS_MS);
  }

  private clearDismissTimer(): void {
    if (this.dismissTimer) {
      clearTimeout(this.dismissTimer);
      this.dismissTimer = null;
    }
  }
}

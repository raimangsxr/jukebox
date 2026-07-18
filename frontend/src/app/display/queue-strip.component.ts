import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

import { QueueEntryRead } from '../models/jukebox-state';

@Component({
  selector: 'app-queue-strip',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex h-full flex-col rounded-xl border border-white/10 bg-jukebox-surface px-3 py-2">
      <p class="mb-1 text-xs uppercase tracking-[0.15em] text-jukebox-muted">Próximas canciones</p>
      <div *ngIf="entries.length; else empty" class="flex min-h-0 flex-1 items-center gap-3 overflow-x-auto">
        <div
          *ngFor="let entry of entries"
          class="flex min-w-[10rem] max-w-[14rem] items-center gap-2 rounded-lg bg-jukebox-deep/60 px-2 py-1"
        >
          <img
            *ngIf="entry.thumbnail_url"
            [src]="entry.thumbnail_url"
            [alt]="entry.title"
            class="h-8 w-12 shrink-0 rounded object-cover"
          />
          <div class="min-w-0 flex-1">
            <p class="truncate text-xs font-medium">{{ entry.title }}</p>
          </div>
          <span class="shrink-0 rounded-full bg-jukebox-accent/20 px-2 py-0.5 text-xs font-semibold text-jukebox-primary">
            {{ entry.vote_count }}
          </span>
        </div>
      </div>
      <ng-template #empty>
        <p class="flex flex-1 items-center text-sm text-jukebox-muted">Cola vacía por ahora</p>
      </ng-template>
    </div>
  `,
})
export class QueueStripComponent {
  @Input() entries: QueueEntryRead[] = [];
}

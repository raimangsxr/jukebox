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
      <div class="mb-1 shrink-0">
        <p class="text-xs font-semibold uppercase tracking-[0.12em] text-jukebox-primary">
          Próximas canciones y votos en cada una
        </p>
        <p class="text-[10px] text-jukebox-muted">El número en cada tarjeta es el total de votos</p>
      </div>
      <div *ngIf="entries.length; else empty" class="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
        <div
          *ngFor="let entry of entries"
          class="flex items-center gap-2 rounded-lg bg-jukebox-deep/60 px-2 py-1.5"
        >
          <img
            *ngIf="entry.thumbnail_url"
            [src]="entry.thumbnail_url"
            [alt]="entry.title"
            class="h-10 w-16 shrink-0 rounded object-cover"
          />
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium">{{ entry.title }}</p>
          </div>
          <span
            class="shrink-0 rounded-full bg-jukebox-accent/25 px-2 py-0.5 text-xs font-bold text-jukebox-accent"
            [attr.aria-label]="'Votos: ' + entry.vote_count"
          >
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

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
      <div class="mb-2 shrink-0">
        <h2
          class="bg-gradient-to-r from-jukebox-accent via-fuchsia-400 to-violet-300 bg-clip-text text-2xl font-extrabold tracking-tight text-transparent md:text-3xl"
        >
          Próximas canciones
        </h2>
        <p class="text-[11px] leading-snug text-jukebox-muted md:text-xs">
          <span class="font-semibold text-jukebox-accent">Las más votadas suenan antes</span> — el número de cada tarjeta son sus votos.
        </p>
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

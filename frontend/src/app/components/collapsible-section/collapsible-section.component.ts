import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';

let nextContentId = 0;

@Component({
  selector: 'app-collapsible-section',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="min-w-0 rounded-xl border border-white/10 bg-jukebox-surface">
      <h2 class="m-0 text-base">
        <button
          type="button"
          class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-white/5"
          [attr.aria-expanded]="expanded"
          [attr.aria-controls]="contentId"
          (click)="onToggle()"
        >
          <span
            class="collapsible-chevron shrink-0 text-jukebox-muted transition-transform duration-200"
            [class.collapsible-chevron--expanded]="expanded"
            aria-hidden="true"
          >›</span>
          <span class="min-w-0 flex-1 font-semibold text-white">{{ title }}</span>
          @if (badge) {
            <span class="shrink-0 text-sm font-normal text-jukebox-muted">{{ badge }}</span>
          }
        </button>
      </h2>
      @if (expanded) {
        <div [id]="contentId" class="min-w-0 border-t border-white/10 p-4">
          <ng-content />
        </div>
      }
    </section>
  `,
  styles: [
    `
      :host {
        display: block;
        min-width: 0;
      }

      .collapsible-chevron {
        display: inline-block;
        transform: rotate(0deg);
        font-size: 1.25rem;
        line-height: 1;
      }

      .collapsible-chevron--expanded {
        transform: rotate(90deg);
      }
    `,
  ],
})
export class CollapsibleSectionComponent {
  @Input({ required: true }) title!: string;
  @Input() expanded = false;
  @Input() badge: string | null = null;
  @Output() readonly expandedChange = new EventEmitter<boolean>();

  readonly contentId = `collapsible-section-${++nextContentId}`;

  onToggle(): void {
    this.expandedChange.emit(!this.expanded);
  }
}

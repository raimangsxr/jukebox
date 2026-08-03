import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

import { LiveConnectionStatus } from '../services/live-connection';

@Component({
  selector: 'app-live-status',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (status !== 'connected') {
      <div
        class="live-status"
        [class.live-status--reconnecting]="status === 'reconnecting'"
        [class.live-status--fallback]="status === 'fallback'"
        role="status"
        [attr.aria-live]="status === 'reconnecting' ? 'assertive' : 'polite'"
      >
        @if (status === 'reconnecting') {
          <span>Reconectando…</span>
        } @else {
          <span>Modo respaldo</span>
        }
      </div>
    }
  `,
  styles: [
    `
      .live-status {
        position: fixed;
        top: calc(0.75rem + env(safe-area-inset-top));
        right: calc(0.75rem + env(safe-area-inset-right));
        z-index: 50;
        max-width: min(12rem, calc(100vw - 1.5rem));
        border-radius: 9999px;
        padding: 0.35rem 0.75rem;
        font-size: 0.75rem;
        font-weight: 600;
        line-height: 1.2;
        text-align: center;
        backdrop-filter: blur(8px);
      }

      .live-status--reconnecting {
        border: 1px solid rgb(251 191 36 / 0.35);
        background: rgb(251 191 36 / 0.12);
        color: rgb(253 224 71);
      }

      .live-status--fallback {
        border: 1px solid rgb(96 165 250 / 0.35);
        background: rgb(59 130 246 / 0.12);
        color: rgb(147 197 253);
      }
    `,
  ],
})
export class LiveStatusComponent {
  @Input({ required: true }) status: LiveConnectionStatus = 'connected';
}

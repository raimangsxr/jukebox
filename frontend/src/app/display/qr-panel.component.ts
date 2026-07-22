import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  Input,
  OnChanges,
  SimpleChanges,
} from '@angular/core';
import QRCode from 'qrcode';

import { EventConfigSummary } from '../models/jukebox-state';

@Component({
  selector: 'app-qr-panel',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="flex h-full min-h-0 items-center gap-3 overflow-y-auto rounded-xl border border-white/10 bg-jukebox-surface p-3 md:gap-4 md:p-4"
    >
      <img
        *ngIf="qrDataUrl"
        [src]="qrDataUrl"
        alt="QR para participar"
        class="h-32 w-32 shrink-0 rounded-xl bg-white p-2 shadow-lg shadow-jukebox-accent/20 md:h-40 md:w-40"
      />

      <div class="flex min-w-0 flex-1 flex-col gap-1 text-left md:gap-2">
        <h2
          class="bg-gradient-to-r from-jukebox-accent via-fuchsia-400 to-violet-300 bg-clip-text text-2xl font-extrabold tracking-tight text-transparent md:text-3xl"
        >
          Participa
        </h2>

        <p *ngIf="eventConfig?.subtitle" class="text-xs text-jukebox-muted md:text-sm">
          {{ eventConfig.subtitle }}
        </p>

        <ol class="list-decimal space-y-0.5 pl-4 text-[11px] leading-snug text-jukebox-muted md:text-xs">
          <li>Escanea el código QR con tu móvil.</li>
          <li>Identifícate.</li>
          <li>Envía una canción o búscala en YouTube.</li>
          <li>Vota tus favoritas en la cola.</li>
        </ol>

        <p class="text-[10px] text-jukebox-muted/90 md:text-xs">
          Tienes <span class="font-semibold text-jukebox-accent">2 votos cada 5 minutos</span>.
        </p>
      </div>
    </div>
  `,
})
export class QrPanelComponent implements OnChanges {

  @Input() eventConfig: EventConfigSummary | null = null;

  qrDataUrl: string | null = null;
  private renderedTarget: string | null = null;

  ngOnChanges(_changes: SimpleChanges): void {
    void this.renderQr();
  }

  private async renderQr(): Promise<void> {
    const target = `${window.location.origin}/participar`;
    // The participation URL is stable, so regenerate only when it actually
    // changes instead of on every change-detection cycle (FR-022).
    if (target === this.renderedTarget && this.qrDataUrl) {
      return;
    }
    this.renderedTarget = target;
    this.qrDataUrl = await QRCode.toDataURL(target, { margin: 1, width: 256 });
  }
}

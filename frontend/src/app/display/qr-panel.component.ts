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
      class="flex h-full min-h-0 flex-col items-center justify-center gap-2 overflow-y-auto rounded-xl border border-white/10 bg-jukebox-surface p-3 text-center md:gap-3 md:p-4"
    >
      <h2
        class="bg-gradient-to-r from-jukebox-accent via-fuchsia-400 to-violet-300 bg-clip-text text-2xl font-extrabold tracking-tight text-transparent md:text-3xl"
      >
        Participa
      </h2>

      <p *ngIf="eventConfig?.subtitle" class="text-xs text-jukebox-muted md:text-sm">
        {{ eventConfig.subtitle }}
      </p>

      <img
        *ngIf="qrDataUrl"
        [src]="qrDataUrl"
        alt="QR para participar"
        class="h-40 w-40 shrink-0 rounded-xl bg-white p-2 shadow-lg shadow-jukebox-accent/20 md:h-48 md:w-48"
      />

      <ol class="w-full max-w-[15rem] list-decimal space-y-1 pl-4 text-left text-[11px] leading-snug text-jukebox-muted md:max-w-none md:text-xs">
        <li>Escanea el código QR con tu móvil.</li>
        <li>Identifícate.</li>
        <li>Envía una canción o búscala en YouTube.</li>
        <li>Vota tus favoritas en la cola.</li>
      </ol>

      <p class="text-[10px] text-jukebox-muted/90 md:text-xs">
        Tienes <span class="font-semibold text-jukebox-accent">2 votos cada 5 minutos</span>.
      </p>
    </div>
  `,
})
export class QrPanelComponent implements OnChanges {

  @Input() eventConfig: EventConfigSummary | null = null;

  qrDataUrl: string | null = null;

  ngOnChanges(_changes: SimpleChanges): void {
    void this.renderQr();
  }

  private async renderQr(): Promise<void> {
    const target = `${window.location.origin}/participar`;
    this.qrDataUrl = await QRCode.toDataURL(target, { margin: 1, width: 256 });
  }
}

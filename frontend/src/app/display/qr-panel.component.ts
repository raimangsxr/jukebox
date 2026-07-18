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
    <div class="flex h-full flex-col items-center justify-center gap-3 rounded-xl border border-white/10 bg-jukebox-surface p-4 text-center">
      <p class="text-xs uppercase tracking-[0.15em] text-jukebox-muted">Participa</p>
      <h2 class="text-lg font-bold leading-tight">{{ eventConfig?.name || 'Jukebox' }}</h2>
      <p *ngIf="eventConfig?.subtitle" class="text-sm text-jukebox-muted">{{ eventConfig?.subtitle }}</p>
      <img
        *ngIf="qrDataUrl"
        [src]="qrDataUrl"
        alt="QR para participar"
        class="h-32 w-32 rounded-lg bg-white p-2"
      />
      <p class="text-sm text-jukebox-muted">Escanea el código para enviar y votar canciones desde tu móvil.</p>
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
    this.qrDataUrl = await QRCode.toDataURL(target, { margin: 1, width: 180 });
  }
}

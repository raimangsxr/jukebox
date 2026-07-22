import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
} from '@angular/core';

type YtPlayer = {
  loadVideoById: (id: string) => void;
  playVideo: () => void;
  destroy: () => void;
};

declare global {
  interface Window {
    YT?: {
      Player: new (
        elementId: string,
        options: {
          videoId?: string;
          playerVars?: Record<string, number | string>;
          events?: {
            onReady?: () => void;
            onStateChange?: (event: { data: number }) => void;
          };
        }
      ) => YtPlayer;
      PlayerState: { ENDED: number };
    };
    onYouTubeIframeAPIReady?: () => void;
  }
}

const YT_ENDED = 0;

@Component({
  selector: 'app-youtube-player',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex h-full flex-col overflow-hidden rounded-xl border border-white/10 bg-jukebox-surface">
      <div class="relative min-h-0 flex-1">
        <button
          *ngIf="!activated"
          type="button"
          (click)="activate()"
          class="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 bg-jukebox-surface p-6 text-center transition hover:bg-white/5"
        >
          <span
            class="flex h-16 w-16 items-center justify-center rounded-full bg-jukebox-primary text-3xl text-black"
          >▶</span>
          <span class="text-lg font-semibold">Activar reproducción</span>
          <span class="max-w-xs text-sm text-jukebox-muted">
            Toca una vez para habilitar el sonido. Después, las canciones se
            reproducirán solas cuando el moderador inicie la cola.
          </span>
        </button>
        <div
          *ngIf="activated && !videoId"
          class="absolute inset-0 z-10 flex flex-col items-center justify-center bg-jukebox-surface p-6 text-center"
        >
          <p class="text-sm text-jukebox-muted">Esperando canción</p>
          <p class="mt-2 text-lg font-semibold">
            La reproducción comenzará cuando el moderador inicie la cola
          </p>
        </div>
        <div [id]="playerElementId" class="h-full w-full"></div>
      </div>
      <div *ngIf="title" class="border-t border-white/10 px-3 py-2">
        <p class="truncate text-sm font-medium">{{ title }}</p>
      </div>
    </div>
  `,
})
export class YoutubePlayerComponent implements OnChanges {

  @Input() videoId: string | null = null;
  @Input() title: string | null = null;
  @Output() readonly ended = new EventEmitter<void>();

  readonly playerElementId = `yt-player-${Math.random().toString(36).slice(2)}`;

  /**
   * Los navegadores bloquean el autoplay con sonido hasta que la pestaña recibe
   * un gesto del usuario. La pantalla kiosk arranca con un overlay de activación;
   * al pulsarlo una vez, el navegador concede autoplay-con-sonido durante toda la
   * sesión, de modo que cada canción que inicie el moderador se reproduce sola.
   */
  activated = false;

  private player: YtPlayer | null = null;
  private apiReady = false;
  private pendingVideoId: string | null = null;

  ngOnChanges(changes: SimpleChanges): void {
    if ('videoId' in changes) {
      void this.syncVideo();
    }
  }

  activate(): void {
    if (this.activated) {
      return;
    }
    this.activated = true;
    // Precargamos la API de YouTube dentro del gesto del usuario y arrancamos el
    // vídeo actual (si lo hay); así el desbloqueo de autoplay queda asociado al click.
    void this.ensureApi();
    void this.syncVideo();
  }

  private async syncVideo(): Promise<void> {
    if (!this.activated) {
      // Esperamos al gesto de activación único antes de crear el player.
      return;
    }
    if (!this.videoId) {
      this.destroyPlayer();
      return;
    }
    await this.ensureApi();
    await this.waitForPlayerElement();
    if (!this.videoId) {
      return;
    }
    if (!this.player) {
      this.createPlayer(this.videoId);
      return;
    }
    this.player.loadVideoById(this.videoId);
    this.player.playVideo();
  }

  private waitForPlayerElement(): Promise<void> {
    return new Promise(resolve => {
      const check = () => {
        if (document.getElementById(this.playerElementId)) {
          resolve();
          return;
        }
        requestAnimationFrame(check);
      };
      requestAnimationFrame(check);
    });
  }

  private ensureApi(): Promise<void> {
    if (this.apiReady && window.YT?.Player) {
      return Promise.resolve();
    }
    return new Promise(resolve => {
      if (window.YT?.Player) {
        this.apiReady = true;
        resolve();
        return;
      }
      const existing = document.querySelector('script[data-yt-iframe-api]');
      if (!existing) {
        const script = document.createElement('script');
        script.src = 'https://www.youtube.com/iframe_api';
        script.async = true;
        script.dataset['ytIframeApi'] = 'true';
        document.body.appendChild(script);
      }
      const previous = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        previous?.();
        this.apiReady = true;
        resolve();
        if (this.pendingVideoId) {
          void this.syncVideo();
          this.pendingVideoId = null;
        }
      };
    });
  }

  private createPlayer(videoId: string): void {
    if (!window.YT?.Player) {
      this.pendingVideoId = videoId;
      return;
    }
    if (!document.getElementById(this.playerElementId)) {
      this.pendingVideoId = videoId;
      return;
    }
    this.destroyPlayer();
    this.player = new window.YT.Player(this.playerElementId, {
      videoId,
      playerVars: {
        autoplay: 1,
        rel: 0,
        modestbranding: 1,
      },
      events: {
        onReady: () => {
          this.player?.playVideo();
        },
        onStateChange: (event: { data: number }) => {
          if (event.data === YT_ENDED) {
            this.ended.emit();
          }
        },
      },
    });
  }

  private destroyPlayer(): void {
    this.player?.destroy();
    this.player = null;
  }
}

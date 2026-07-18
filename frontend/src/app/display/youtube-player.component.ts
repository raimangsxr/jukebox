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

declare global {
  interface Window {
    YT?: {
      Player: new (
        elementId: string,
        options: {
          videoId?: string;
          playerVars?: Record<string, number | string>;
          events?: { onStateChange?: (event: { data: number }) => void };
        }
      ) => { loadVideoById: (id: string) => void; destroy: () => void };
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
      <div *ngIf="videoId; else idle" class="relative min-h-0 flex-1">
        <div [id]="playerElementId" class="h-full w-full"></div>
      </div>
      <ng-template #idle>
        <div class="flex flex-1 flex-col items-center justify-center p-6 text-center">
          <p class="text-sm text-jukebox-muted">Esperando canción</p>
          <p class="mt-2 text-lg font-semibold">La reproducción comenzará cuando el moderador inicie la cola</p>
        </div>
      </ng-template>
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

  private player: { loadVideoById: (id: string) => void; destroy: () => void } | null = null;
  private apiReady = false;
  private pendingVideoId: string | null = null;

  ngOnChanges(changes: SimpleChanges): void {
    if ('videoId' in changes) {
      void this.syncVideo();
    }
  }

  private async syncVideo(): Promise<void> {
    if (!this.videoId) {
      this.destroyPlayer();
      return;
    }
    await this.ensureApi();
    if (!this.player) {
      this.createPlayer(this.videoId);
      return;
    }
    this.player.loadVideoById(this.videoId);
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
          this.createPlayer(this.pendingVideoId);
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
    this.destroyPlayer();
    this.player = new window.YT.Player(this.playerElementId, {
      videoId,
      playerVars: {
        autoplay: 1,
        rel: 0,
        modestbranding: 1,
      },
      events: {
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

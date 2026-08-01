import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges,
  inject,
} from '@angular/core';

import { PlaybackAudioMode } from '../models/playback-status';
import { DisplayStateService } from '../services/display-state.service';
import { detectAutoplayWithSound } from './autoplay-capability';

type YtPlayer = {
  loadVideoById: (id: string) => void;
  playVideo: () => void;
  destroy: () => void;
  unMute: () => void;
  isMuted: () => boolean;
  getPlayerState: () => number;
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
            onError?: (event: { data: number }) => void;
          };
        }
      ) => YtPlayer;
      PlayerState: {
        ENDED: number;
        PLAYING: number;
        PAUSED: number;
        CUED: number;
      };
    };
    onYouTubeIframeAPIReady?: () => void;
  }
}

const YT_ENDED = 0;
const YT_PLAYING = 1;
const YT_PAUSED = 2;
const YT_CUED = 5;
const SOUND_ACTIVATED_KEY = 'jukebox.playerActivated';

@Component({
  selector: 'app-youtube-player',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex h-full flex-col overflow-hidden rounded-xl border border-white/10 bg-jukebox-surface">
      <div class="relative min-h-0 flex-1">
        <button
          *ngIf="showSoundOverlay"
          type="button"
          (click)="activateSound()"
          class="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 bg-jukebox-surface/90 p-6 text-center transition hover:bg-white/5"
        >
          <span
            class="flex h-16 w-16 items-center justify-center rounded-full bg-jukebox-primary text-3xl text-black"
          >▶</span>
          <span class="text-lg font-semibold">Activar sonido</span>
          <span class="max-w-xs text-sm text-jukebox-muted">
            Toca una vez para habilitar el audio. El vídeo puede reproducirse en
            silencio hasta que actives el sonido.
          </span>
        </button>
        <div
          *ngIf="!videoId"
          class="absolute inset-0 z-10 flex flex-col items-center justify-center bg-jukebox-surface p-6 text-center"
        >
          <p class="text-sm text-jukebox-muted">Esperando canción</p>
          <p class="mt-2 text-lg font-semibold">
            La reproducción comenzará cuando haya una canción en cola
          </p>
        </div>
        <p
          *ngIf="playbackError"
          class="absolute bottom-2 left-2 right-2 z-30 rounded-lg bg-red-500/20 px-3 py-2 text-center text-sm text-red-300"
        >
          {{ playbackError }}
        </p>
        <div [id]="playerElementId" class="h-full w-full"></div>
      </div>
      <div *ngIf="title" class="border-t border-white/10 px-3 py-2">
        <p class="truncate text-sm font-medium">{{ title }}</p>
      </div>
    </div>
  `,
})
export class YoutubePlayerComponent implements OnChanges, OnInit {

  @Input() videoId: string | null = null;
  @Input() title: string | null = null;
  @Output() readonly ended = new EventEmitter<void>();

  private readonly displayState = inject(DisplayStateService);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly playerElementId = `yt-player-${Math.random().toString(36).slice(2)}`;

  soundActivated = false;
  playbackError: string | null = null;

  private player: YtPlayer | null = null;
  private apiReady = false;
  private pendingVideoId: string | null = null;
  private playRetryTimer: ReturnType<typeof setTimeout> | null = null;
  private soundCapabilityReady = false;
  private lastReportedMode: PlaybackAudioMode | null = null;

  get showSoundOverlay(): boolean {
    return this.soundCapabilityReady && !this.soundActivated && !!this.videoId;
  }

  ngOnInit(): void {
    if (sessionStorage.getItem(SOUND_ACTIVATED_KEY) === '1') {
      this.soundActivated = true;
    }
    void this.bootstrapSoundCapability();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if ('videoId' in changes) {
      this.playbackError = null;
      if (!this.videoId) {
        void this.reportPlaybackStatus('idle');
      }
      void this.syncVideoWhenReady();
    }
  }

  activateSound(): void {
    if (this.soundActivated) {
      return;
    }
    this.soundActivated = true;
    sessionStorage.setItem(SOUND_ACTIVATED_KEY, '1');
    this.cdr.markForCheck();
    this.tryUnmuteAndPlay();
  }

  private async bootstrapSoundCapability(): Promise<void> {
    if (!this.soundActivated) {
      this.soundActivated = await detectAutoplayWithSound();
      if (this.soundActivated) {
        sessionStorage.setItem(SOUND_ACTIVATED_KEY, '1');
      }
    }
    this.soundCapabilityReady = true;
    this.cdr.markForCheck();
    await this.syncVideoWhenReady();
    if (!this.videoId) {
      void this.reportPlaybackStatus('idle');
    }
  }

  private async syncVideoWhenReady(): Promise<void> {
    if (!this.soundCapabilityReady) {
      return;
    }
    await this.syncVideo();
  }

  private async maybeStartQueueFromGesture(): Promise<void> {
    const snapshot = this.displayState.snapshot;
    if (!snapshot || snapshot.now_playing || snapshot.queue.length === 0) {
      return;
    }
    await this.displayState.advancePlayback();
  }

  private tryUnmuteAndPlay(): void {
    if (this.player) {
      this.player.unMute();
      this.player.playVideo();
      this.reportPlaybackStatusFromPlayer();
    }
    void this.maybeStartQueueFromGesture();
  }

  private async syncVideo(): Promise<void> {
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
    this.playWithRetry();
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
        mute: this.soundActivated ? 0 : 1,
        playsinline: 1,
        rel: 0,
        modestbranding: 1,
      },
      events: {
        onReady: () => {
          if (this.soundActivated) {
            this.player?.unMute();
          }
          this.playWithRetry();
          this.reportPlaybackStatusFromPlayer();
        },
        onStateChange: (event: { data: number }) => {
          if (event.data === YT_ENDED) {
            this.ended.emit();
          }
          if (
            event.data === YT_PLAYING ||
            event.data === YT_PAUSED ||
            event.data === YT_CUED
          ) {
            this.reportPlaybackStatusFromPlayer();
          }
        },
        onError: () => {
          this.playbackError = 'No se pudo reproducir este vídeo.';
          this.cdr.markForCheck();
        },
      },
    });
  }

  private playWithRetry(): void {
    this.player?.playVideo();
    this.schedulePlayRetry();
  }

  private schedulePlayRetry(): void {
    if (this.playRetryTimer) {
      clearTimeout(this.playRetryTimer);
    }
    this.playRetryTimer = setTimeout(() => {
      this.playRetryTimer = null;
      if (!this.player) {
        return;
      }
      const state = this.player.getPlayerState();
      if (state === YT_PAUSED || state === YT_CUED) {
        this.player.playVideo();
      }
      this.reportPlaybackStatusFromPlayer();
    }, 1000);
  }

  private reportPlaybackStatusFromPlayer(): void {
    if (!this.videoId) {
      void this.reportPlaybackStatus('idle');
      return;
    }
    if (!this.player) {
      return;
    }
    const state = this.player.getPlayerState();
    if (state === YT_PLAYING && !this.player.isMuted()) {
      void this.reportPlaybackStatus('sound');
      return;
    }
    void this.reportPlaybackStatus('muted');
  }

  private reportPlaybackStatus(mode: PlaybackAudioMode): void {
    if (this.lastReportedMode === mode) {
      return;
    }
    this.lastReportedMode = mode;
    void this.displayState.reportPlaybackStatus(mode);
  }

  private destroyPlayer(): void {
    if (this.playRetryTimer) {
      clearTimeout(this.playRetryTimer);
      this.playRetryTimer = null;
    }
    this.player?.destroy();
    this.player = null;
  }
}

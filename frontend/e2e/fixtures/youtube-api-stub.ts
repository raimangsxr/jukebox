import type { Page } from '@playwright/test';

/** Stub YouTube IFrame API so e2e does not depend on googlevideo CDN. */
export async function installYoutubeApiStub(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const YT_ENDED = 0;
    const YT_PLAYING = 1;
    const YT_PAUSED = 2;
    const YT_CUED = 5;

    type PlayerOptions = {
      playerVars?: { mute?: number };
      events?: {
        onReady?: () => void;
        onStateChange?: (event: { data: number }) => void;
      };
    };

    class StubPlayer {
      private muted: boolean;
      private state = YT_CUED;

      constructor(_elementId: string, options: PlayerOptions) {
        this.muted = options.playerVars?.mute === 1;
        queueMicrotask(() => {
          options.events?.onReady?.();
          this.state = YT_PLAYING;
          options.events?.onStateChange?.({ data: YT_PLAYING });
        });
      }

      loadVideoById(_videoId: string): void {
        this.state = YT_PLAYING;
      }

      playVideo(): void {
        this.state = YT_PLAYING;
      }

      destroy(): void {}

      unMute(): void {
        this.muted = false;
      }

      isMuted(): boolean {
        return this.muted;
      }

      getPlayerState(): number {
        return this.state;
      }
    }

    window.YT = {
      Player: StubPlayer as unknown as typeof window.YT.Player,
      PlayerState: {
        ENDED: YT_ENDED,
        PLAYING: YT_PLAYING,
        PAUSED: YT_PAUSED,
        CUED: YT_CUED,
      },
    };
  });

  await page.route('**/youtube.com/iframe_api**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/javascript',
      body: 'window.onYouTubeIframeAPIReady && window.onYouTubeIframeAPIReady();',
    });
  });
}

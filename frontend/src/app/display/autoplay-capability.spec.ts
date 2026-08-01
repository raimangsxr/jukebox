import { describe, expect, it, beforeEach, vi } from 'vitest';

import {
  detectAutoplayWithSound,
  resetAutoplayCapabilityCacheForTests,
} from './autoplay-capability';

describe('detectAutoplayWithSound', () => {
  beforeEach(() => {
    resetAutoplayCapabilityCacheForTests();
  });

  it('returns cached true without probing audio', async () => {
    sessionStorage.setItem('jukebox.autoplayCapable', '1');
    const playSpy = vi.spyOn(window.HTMLMediaElement.prototype, 'play');

    await expect(detectAutoplayWithSound()).resolves.toBe(true);
    expect(playSpy).not.toHaveBeenCalled();
    playSpy.mockRestore();
  });

  it('returns cached false without probing audio', async () => {
    sessionStorage.setItem('jukebox.autoplayCapable', '0');
    const playSpy = vi.spyOn(window.HTMLMediaElement.prototype, 'play');

    await expect(detectAutoplayWithSound()).resolves.toBe(false);
    expect(playSpy).not.toHaveBeenCalled();
    playSpy.mockRestore();
  });
});

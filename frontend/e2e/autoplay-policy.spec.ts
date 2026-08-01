import { chromium, expect, test } from '@playwright/test';

const SILENT_WAV =
  'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';

async function probeAutoplayWithSound(page: import('@playwright/test').Page): Promise<boolean> {
  return page.evaluate(async (src: string) => {
    const audio = new Audio();
    audio.src = src;
    try {
      await audio.play();
      audio.pause();
      return true;
    } catch {
      return false;
    }
  }, SILENT_WAV);
}

test('kiosk Chromium flag allows unmuted programmatic play', async () => {
  const browser = await chromium.launch({
    args: ['--autoplay-policy=no-user-gesture-required'],
  });
  const page = await browser.newPage();
  try {
    await page.setContent('<!doctype html><title>jukebox autoplay probe</title>');
    await expect(probeAutoplayWithSound(page)).resolves.toBe(true);
  } finally {
    await browser.close();
  }
});

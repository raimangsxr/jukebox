const AUTOPLAY_CAPABLE_KEY = 'jukebox.autoplayCapable';

/** Tiny silent WAV for autoplay policy probing. */
const SILENT_WAV =
  'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';

export async function detectAutoplayWithSound(): Promise<boolean> {
  const cached = sessionStorage.getItem(AUTOPLAY_CAPABLE_KEY);
  if (cached === '1') {
    return true;
  }
  if (cached === '0') {
    return false;
  }

  const audio = new Audio();
  audio.src = SILENT_WAV;
  try {
    await audio.play();
    audio.pause();
    sessionStorage.setItem(AUTOPLAY_CAPABLE_KEY, '1');
    return true;
  } catch {
    sessionStorage.setItem(AUTOPLAY_CAPABLE_KEY, '0');
    return false;
  } finally {
    audio.removeAttribute('src');
    audio.load();
  }
}

export function resetAutoplayCapabilityCacheForTests(): void {
  sessionStorage.removeItem(AUTOPLAY_CAPABLE_KEY);
}

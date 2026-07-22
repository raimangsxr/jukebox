// Applies event_config.theme to the document root so the field is honored
// (010-hardening-and-polish, FR-019). Only the dark theme is supported for
// now; any unknown value falls back to dark.
const SUPPORTED_THEMES = new Set<string>(['dark']);
const DEFAULT_THEME = 'dark';

export function resolveTheme(theme: string | null | undefined): string {
  return theme && SUPPORTED_THEMES.has(theme) ? theme : DEFAULT_THEME;
}

export function applyTheme(theme: string | null | undefined): void {
  if (typeof document === 'undefined') {
    return;
  }
  document.documentElement.setAttribute('data-theme', resolveTheme(theme));
}

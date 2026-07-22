import { afterEach, describe, expect, it } from 'vitest';

import { applyTheme, resolveTheme } from './theme.util';

describe('theme.util', () => {
  afterEach(() => {
    document.documentElement.removeAttribute('data-theme');
  });

  it('resolves the supported dark theme', () => {
    expect(resolveTheme('dark')).toBe('dark');
  });

  it('falls back to dark for unknown or empty values', () => {
    expect(resolveTheme('neon')).toBe('dark');
    expect(resolveTheme(null)).toBe('dark');
    expect(resolveTheme(undefined)).toBe('dark');
  });

  it('applies the resolved theme to the document root', () => {
    applyTheme('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    applyTheme('bogus');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });
});

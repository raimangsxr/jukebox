import { describe, expect, it } from 'vitest';

import { SearchResultItem } from '../models/youtube-search';
import {
  SubmitActivePath,
  canSubmitFromActivePath,
  isSearchQueryValid,
  nextActivePathOnSearchSelect,
  nextActivePathOnUrlEdit,
  resolveActivePathOnUrlFocus
} from './participate-submit.util';

describe('participate-submit.util', () => {
  it('activates URL path on text edit', () => {
    expect(nextActivePathOnUrlEdit()).toBe('url');
  });

  it('activates search path on row select', () => {
    expect(nextActivePathOnSearchSelect()).toBe('search');
  });

  it('does not change active path on URL focus alone', () => {
    const current: SubmitActivePath = 'search';
    expect(resolveActivePathOnUrlFocus(current)).toBe('search');
    expect(resolveActivePathOnUrlFocus(null)).toBeNull();
  });

  it('submits search path only when a result is selected', () => {
    expect(canSubmitFromActivePath('search', '', null)).toBe(false);
    expect(canSubmitFromActivePath('search', '', 'abc123')).toBe(true);
    expect(canSubmitFromActivePath('url', 'https://youtu.be/abc', null)).toBe(true);
    expect(canSubmitFromActivePath('url', '   ', null)).toBe(false);
    expect(canSubmitFromActivePath(null, 'https://youtu.be/abc', 'abc')).toBe(false);
  });

  it('rejects whitespace-only and short search queries', () => {
    expect(isSearchQueryValid('a')).toBe(false);
    expect(isSearchQueryValid('   ')).toBe(false);
    expect(isSearchQueryValid('  ab  ')).toBe(true);
  });
});

describe('search result row shape', () => {
  it('includes title, thumbnail, and channel for distinguishable rows', () => {
    const item: SearchResultItem = {
      youtube_video_id: 'dQw4w9WgXcQ',
      title: 'Never Gonna Give You Up',
      channel_title: 'Rick Astley',
      thumbnail_url: 'https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg'
    };
    expect(item.title).toBeTruthy();
    expect(item.thumbnail_url).toMatch(/^https:\/\//);
    expect(item.channel_title).toBeTruthy();
  });

  it('allows submit when a single result is selected', () => {
    const selectedId = 'dQw4w9WgXcQ';
    expect(canSubmitFromActivePath('search', '', selectedId)).toBe(true);
  });
});

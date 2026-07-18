export type SubmitActivePath = 'search' | 'url' | null;

export function nextActivePathOnUrlEdit(): SubmitActivePath {
  return 'url';
}

export function nextActivePathOnSearchSelect(): SubmitActivePath {
  return 'search';
}

export function resolveActivePathOnUrlFocus(current: SubmitActivePath): SubmitActivePath {
  return current;
}

export function canSubmitFromActivePath(
  activePath: SubmitActivePath,
  url: string,
  selectedVideoId: string | null
): boolean {
  if (activePath === 'search') {
    return !!selectedVideoId;
  }
  if (activePath === 'url') {
    return !!url.trim();
  }
  return false;
}

export function isSearchQueryValid(query: string, minLength = 2): boolean {
  return query.trim().length >= minLength;
}

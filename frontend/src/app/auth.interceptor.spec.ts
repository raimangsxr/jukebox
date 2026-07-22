import '@angular/compiler';
import { HttpErrorResponse } from '@angular/common/http';
import { Injector, runInInjectionContext } from '@angular/core';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';

import { authInterceptor } from './auth.interceptor';
import { AuthService } from './services/auth.service';

function run(
  reqUrl: string,
  routerUrl: string,
  status: number,
  authMock: Partial<AuthService>
) {
  const router = { url: routerUrl, navigate: vi.fn() };
  const injector = Injector.create({
    providers: [
      { provide: AuthService, useValue: authMock },
      { provide: Router, useValue: router }
    ]
  });
  const req = { url: reqUrl, clone: () => req } as never;
  const next = () => throwError(() => new HttpErrorResponse({ status }));
  const result = runInInjectionContext(injector, () =>
    authInterceptor(req, next as never)
  );
  return { result, router };
}

describe('authInterceptor 401 handling', () => {
  it('marks the session expired on the kiosk route', () => {
    const setSessionExpired = vi.fn();
    const { result } = run('http://x/api/state', '/', 401, { setSessionExpired });
    result.subscribe({ error: () => {} });
    expect(setSessionExpired).toHaveBeenCalledOnce();
  });

  it('logs out and navigates to /login elsewhere', () => {
    const logout = vi.fn(() => of(undefined));
    const { result, router } = run('http://x/api/tokens', '/admin', 401, {
      logout
    });
    result.subscribe({ error: () => {} });
    expect(logout).toHaveBeenCalledOnce();
    expect(router.navigate).toHaveBeenCalledWith(['/login']);
  });

  it('does not log out on participant API 401 while on /participar', () => {
    const logout = vi.fn(() => of(undefined));
    const setSessionExpired = vi.fn();
    const { result, router } = run(
      'http://x/api/participant/state',
      '/participar',
      401,
      { logout, setSessionExpired }
    );
    result.subscribe({ error: () => {} });
    expect(logout).not.toHaveBeenCalled();
    expect(setSessionExpired).not.toHaveBeenCalled();
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('ignores non-401 errors', () => {
    const logout = vi.fn(() => of(undefined));
    const setSessionExpired = vi.fn();
    const { result } = run('http://x/api/state', '/admin', 500, {
      logout,
      setSessionExpired
    });
    result.subscribe({ error: () => {} });
    expect(logout).not.toHaveBeenCalled();
    expect(setSessionExpired).not.toHaveBeenCalled();
  });
});

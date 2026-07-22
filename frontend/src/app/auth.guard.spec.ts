import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { firstValueFrom, isObservable } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';

import { authGuard, displayGuard, guestGuard } from './auth.guard';
import { AuthService } from './services/auth.service';

const URL_TREE = { __urlTree: true };

function context(authMock: Partial<AuthService>, routerMock: Partial<Router>) {
  const injector = Injector.create({
    providers: [
      { provide: AuthService, useValue: authMock },
      { provide: Router, useValue: routerMock }
    ]
  });
  return injector;
}

async function resolve(result: unknown): Promise<unknown> {
  return isObservable(result) ? firstValueFrom(result) : result;
}

describe('authGuard', () => {
  it('allows an authenticated operator', () => {
    const injector = context(
      { isAuthenticated: () => true },
      { createUrlTree: vi.fn() }
    );
    const result = runInInjectionContext(injector, () =>
      authGuard({} as never, { url: '/admin' } as never)
    );
    expect(result).toBe(true);
  });

  it('redirects to /login with returnUrl when bootstrap yields no user', async () => {
    const createUrlTree = vi.fn(() => URL_TREE);
    const injector = context(
      { isAuthenticated: () => false, bootstrap: () => of(null) },
      { createUrlTree }
    );
    const result = await resolve(
      runInInjectionContext(injector, () =>
        authGuard({} as never, { url: '/admin' } as never)
      )
    );
    expect(result).toBe(URL_TREE);
    expect(createUrlTree).toHaveBeenCalledWith(['/login'], {
      queryParams: { returnUrl: '/admin' }
    });
  });
});

describe('guestGuard', () => {
  it('redirects an authenticated user to /admin', () => {
    const createUrlTree = vi.fn(() => URL_TREE);
    const injector = context({ isAuthenticated: () => true }, { createUrlTree });
    const result = runInInjectionContext(injector, () =>
      guestGuard({} as never, {} as never)
    );
    expect(result).toBe(URL_TREE);
    expect(createUrlTree).toHaveBeenCalledWith(['/admin']);
  });
});

describe('displayGuard', () => {
  it('allows the kiosk when a display error is present', () => {
    const injector = context(
      { isAuthenticated: () => false, getDisplayError: () => 'token_invalid' },
      { createUrlTree: vi.fn() }
    );
    const result = runInInjectionContext(injector, () =>
      displayGuard({} as never, {} as never)
    );
    expect(result).toBe(true);
  });

  it('redirects to /login when unauthenticated with no display error', async () => {
    const createUrlTree = vi.fn(() => URL_TREE);
    const injector = context(
      {
        isAuthenticated: () => false,
        getDisplayError: () => null,
        bootstrap: () => of(null)
      },
      { createUrlTree }
    );
    const result = await resolve(
      runInInjectionContext(injector, () =>
        displayGuard({} as never, {} as never)
      )
    );
    expect(result).toBe(URL_TREE);
    expect(createUrlTree).toHaveBeenCalledWith(['/login']);
  });
});

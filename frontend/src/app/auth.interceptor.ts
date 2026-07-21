import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthService } from './services/auth.service';

const EXEMPT_PATHS = [
  '/api/auth/login',
  '/api/auth/logout',
  '/api/auth/me',
  '/api/auth/token',
  '/api/participant/dev-auth',
  '/api/participant/me'
];

const apiPath = (url: string): string => {
  try {
    return new URL(url, 'http://local').pathname;
  } catch {
    return url.split('?')[0] ?? url;
  }
};

const isExempt = (url: string): boolean => {
  const path = apiPath(url);
  return EXEMPT_PATHS.some(p => path === p || path.endsWith(p));
};

const isLoginRoute = (url: string): boolean =>
  url === '/login' || url.startsWith('/login?') || url.startsWith('/login/');

const isParticipateRoute = (url: string): boolean =>
  url === '/participar' || url.startsWith('/participar?');

const isParticipantApi = (url: string): boolean =>
  url.includes('/api/participant/') || url.endsWith('/api/votes');

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const withCreds = req.clone({ withCredentials: true });
  return next(withCreds).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401 && !isExempt(req.url)) {
        if (router.url === '/' || router.url.startsWith('/?')) {
          auth.setSessionExpired();
        } else if (isParticipateRoute(router.url) && isParticipantApi(req.url)) {
          // /participar handles participant 401 locally
        } else if (isLoginRoute(router.url)) {
          // Login form handles invalid credentials locally
        } else {
          auth.logout().subscribe({
            complete: () => router.navigate(['/login'])
          });
        }
      }
      return throwError(() => err);
    })
  );
};

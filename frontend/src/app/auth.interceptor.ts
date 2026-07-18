import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthService } from './services/auth.service';

const EXEMPT_PATHS = [
  '/api/auth/login',
  '/api/auth/me',
  '/api/auth/token',
  '/api/participant/dev-auth',
  '/api/participant/me'
];

const isExempt = (url: string): boolean =>
  EXEMPT_PATHS.some(p => url.endsWith(p));

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

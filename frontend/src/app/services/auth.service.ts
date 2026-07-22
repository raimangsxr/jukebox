import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, of, ReplaySubject } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import { environment } from '../../environments/environment';

export type DisplayError = 'token_invalid' | 'session_expired' | null;

export interface User {
  id: number;
  username: string;
}

interface MeResponse {
  user: User;
}

const TOKEN_QUERY_PARAM = 'token';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  private user: User | null = null;
  private displayError: DisplayError = null;
  private tokenBootstrapAttempted = false;
  private readonly currentUser = new ReplaySubject<User | null>(1);
  private bootstrapStarted = false;
  private readonly baseUrl: string = environment.apiBaseUrl;

  private readonly http = inject(HttpClient);

  bootstrap(): Observable<User | null> {
    if (!this.bootstrapStarted) {
      this.bootstrapStarted = true;
      this.bootstrapInternal().subscribe(user => {
        this.user = user;
        this.currentUser.next(user);
      });
    }
    return this.currentUser.asObservable();
  }

  private bootstrapInternal(): Observable<User | null> {
    const params = new URLSearchParams(window.location.search);
    const token = params.get(TOKEN_QUERY_PARAM);

    if (token) {
      this.tokenBootstrapAttempted = true;
      params.delete(TOKEN_QUERY_PARAM);
      const remaining = params.toString();
      const newUrl =
        window.location.pathname +
        (remaining ? '?' + remaining : '') +
        window.location.hash;
      window.history.replaceState({}, '', newUrl);

      return this.exchangeToken(token).pipe(
        tap(u => {
          this.user = u;
          this.displayError = null;
        }),
        catchError(() => {
          this.user = null;
          this.displayError = 'token_invalid';
          return of(null);
        })
      );
    }

    return this.me().pipe(
      tap(u => {
        this.user = u;
        if (u) {
          this.displayError = null;
        }
      }),
      catchError(() => {
        this.user = null;
        return of(null);
      })
    );
  }

  login(username: string, password: string): Observable<User> {
    return this.http
      .post<MeResponse>(`${this.baseUrl}/auth/login`, { username, password })
      .pipe(
        map(r => r.user),
        tap(u => {
          this.user = u;
          this.displayError = null;
          this.currentUser.next(u);
        })
      );
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/auth/logout`, {}).pipe(
      tap(() => {
        this.user = null;
        this.displayError = null;
        this.currentUser.next(null);
      }),
      catchError(() => {
        this.user = null;
        this.displayError = null;
        this.currentUser.next(null);
        return of(undefined);
      }),
      map(() => undefined)
    );
  }

  me(): Observable<User | null> {
    return this.http.get<MeResponse>(`${this.baseUrl}/auth/me`).pipe(
      map(r => r.user),
      catchError(() => of(null))
    );
  }

  exchangeToken(token: string): Observable<User> {
    return this.http
      .post<MeResponse>(`${this.baseUrl}/auth/token`, { token })
      .pipe(
        map(r => r.user),
        tap(u => {
          this.user = u;
          this.displayError = null;
          this.currentUser.next(u);
        })
      );
  }

  getUser(): User | null {
    return this.user;
  }

  isAuthenticated(): boolean {
    return this.user !== null;
  }

  getDisplayError(): DisplayError {
    return this.displayError;
  }

  setSessionExpired(): void {
    this.user = null;
    this.displayError = 'session_expired';
    this.currentUser.next(null);
  }

  hadTokenBootstrapAttempt(): boolean {
    return this.tokenBootstrapAttempted;
  }

  resetForTesting(): void {
    // Test-only affordance; no-op in production builds (010, FR-030).
    if (environment.production) {
      return;
    }
    this.user = null;
    this.displayError = null;
    this.tokenBootstrapAttempted = false;
    this.bootstrapStarted = false;
    this.currentUser.next(null);
  }
}

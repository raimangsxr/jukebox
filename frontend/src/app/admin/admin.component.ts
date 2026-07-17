import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { environment } from '../../environments/environment';
import { AuthService } from '../services/auth.service';

interface ApiTokenRead {
  id: string;
  label: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

interface ApiTokenWithSecret extends ApiTokenRead {
  token: string;
}

interface TokenCreateResponse {
  token: ApiTokenWithSecret;
}

interface TokenListResponse {
  tokens: ApiTokenRead[];
}

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.Default,
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css'
})
export class AdminComponent implements OnInit {

  private readonly baseUrl = environment.apiBaseUrl;
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  tokens: ApiTokenRead[] = [];
  newLabel = '';
  creating = false;
  revealedToken: ApiTokenWithSecret | null = null;
  tokenError: string | null = null;
  copied = false;
  loggingOut = false;

  ngOnInit(): void {
    this.refreshTokens();
  }

  logout(): void {
    this.loggingOut = true;
    this.auth.logout().subscribe({
      complete: () => {
        this.loggingOut = false;
        this.router.navigate(['/login']);
      },
      error: () => {
        this.loggingOut = false;
        this.router.navigate(['/login']);
      }
    });
  }

  refreshTokens(): void {
    this.tokenError = null;
    this.http
      .get<TokenListResponse>(`${this.baseUrl}/tokens`)
      .subscribe({
        next: res => (this.tokens = res.tokens),
        error: () => (this.tokenError = 'No se pudieron cargar los tokens.')
      });
  }

  createToken(): void {
    const label = this.newLabel.trim();
    if (!label) {
      this.tokenError = 'Introduce una etiqueta.';
      return;
    }
    this.tokenError = null;
    this.creating = true;
    this.http
      .post<TokenCreateResponse>(`${this.baseUrl}/tokens`, { label })
      .subscribe({
        next: res => {
          this.revealedToken = res.token;
          this.newLabel = '';
          this.creating = false;
          this.copied = false;
          this.refreshTokens();
        },
        error: () => {
          this.creating = false;
          this.tokenError = 'No se pudo crear el token.';
        }
      });
  }

  copyRevealedToken(): void {
    if (!this.revealedToken) {
      return;
    }
    void navigator.clipboard.writeText(this.revealedToken.token).then(() => {
      this.copied = true;
    });
  }

  dismissRevealedToken(): void {
    this.revealedToken = null;
    this.copied = false;
  }

  revokeToken(id: string): void {
    this.tokenError = null;
    this.http.delete(`${this.baseUrl}/tokens/${id}`).subscribe({
      next: () => this.refreshTokens(),
      error: () => (this.tokenError = 'No se pudo revocar el token.')
    });
  }

  isActive(token: ApiTokenRead): boolean {
    return token.revoked_at === null;
  }
}

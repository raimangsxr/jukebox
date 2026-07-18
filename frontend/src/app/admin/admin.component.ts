import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnInit,
  inject,
  signal
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { environment } from '../../environments/environment';
import { AuthService } from '../services/auth.service';
import { QueueEntryRead } from '../models/jukebox-state';
import { DisplayStateService } from '../services/display-state.service';
import { QueueAdminService } from '../services/queue-admin.service';

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
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css'
})
export class AdminComponent implements OnInit {

  private readonly baseUrl = environment.apiBaseUrl;
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly queueAdmin = inject(QueueAdminService);
  private readonly displayState = inject(DisplayStateService);
  private readonly cdr = inject(ChangeDetectorRef);

  tokens: ApiTokenRead[] = [];
  readonly pending = signal<QueueEntryRead[]>([]);
  newLabel = '';
  creating = false;
  revealedToken: ApiTokenWithSecret | null = null;
  tokenError: string | null = null;
  moderationError: string | null = null;
  copied = false;
  loggingOut = false;
  moderationBusy = false;
  rejectReasons: Record<string, string> = {};

  ngOnInit(): void {
    this.refreshTokens();
    this.refreshPending();
    void this.displayState.refresh();
  }

  get canStartPlayback(): boolean {
    const state = this.displayState.snapshot;
    return !!state && !state.now_playing && state.queue.length > 0;
  }

  get canSkipPlayback(): boolean {
    return !!this.displayState.snapshot?.now_playing;
  }

  get playbackDisabled(): boolean {
    return !this.canStartPlayback && !this.canSkipPlayback;
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
        next: res => {
        this.tokens = res.tokens;
        this.cdr.markForCheck();
      },
        error: () => (this.tokenError = 'No se pudieron cargar los tokens.')
      });
  }

  refreshPending(): void {
    this.moderationError = null;
    this.queueAdmin.getPending().subscribe({
      next: res => {
        this.pending.set(Array.isArray(res.entries) ? res.entries : []);
        this.cdr.markForCheck();
      },
      error: () => {
        this.moderationError = 'No se pudo cargar la cola de moderación.';
        this.cdr.markForCheck();
      }
    });
  }

  approveEntry(id: string): void {
    this.moderationBusy = true;
    this.queueAdmin.approve(id).subscribe({
      next: () => {
        this.moderationBusy = false;
        this.refreshPending();
        void this.displayState.refresh();
      },
      error: err => {
        this.moderationBusy = false;
        this.moderationError = this.mapQueueError(err);
      }
    });
  }

  rejectEntry(id: string): void {
    this.moderationBusy = true;
    this.queueAdmin.reject(id, this.rejectReasons[id]).subscribe({
      next: () => {
        this.moderationBusy = false;
        this.refreshPending();
        void this.displayState.refresh();
      },
      error: err => {
        this.moderationBusy = false;
        this.moderationError = this.mapQueueError(err);
      }
    });
  }

  advancePlayback(): void {
    this.moderationBusy = true;
    this.queueAdmin.skipOrStart().subscribe({
      next: state => {
        this.moderationBusy = false;
        this.displayState.applyState(state);
      },
      error: err => {
        this.moderationBusy = false;
        this.moderationError = this.mapQueueError(err);
      }
    });
  }

  youtubeUrl(videoId: string): string {
    return `https://www.youtube.com/watch?v=${videoId}`;
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

  private mapQueueError(err: { error?: { detail?: string } }): string {
    const detail = err.error?.detail;
    switch (detail) {
      case 'queue is full':
        return 'La cola está llena (100 canciones). Libera hueco antes de aprobar.';
      case 'video already in queue':
        return 'Ese vídeo ya está en la cola activa.';
      case 'nothing to advance':
        return 'No hay nada que reproducir ni saltar.';
      case 'invalid status transition':
        return 'Esta entrada ya no se puede moderar.';
      default:
        return 'No se pudo completar la acción de moderación.';
    }
  }
}

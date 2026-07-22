import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnDestroy,
  OnInit,
  inject,
  signal
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';

import { environment } from '../../environments/environment';
import { ApiKeyUsageListResponse } from '../models/youtube-api-key-usage';
import { EventConfigRead } from '../models/event-config';
import { AuthService } from '../services/auth.service';
import { PendingQueueEntryRead } from '../models/jukebox-state';
import { DisplayStateService } from '../services/display-state.service';
import { EventConfigService } from '../services/event-config.service';
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
export class AdminComponent implements OnInit, OnDestroy {

  private readonly baseUrl = environment.apiBaseUrl;
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly queueAdmin = inject(QueueAdminService);
  private readonly displayState = inject(DisplayStateService);
  private readonly eventConfigService = inject(EventConfigService);
  private readonly cdr = inject(ChangeDetectorRef);

  tokens: ApiTokenRead[] = [];
  readonly pending = signal<PendingQueueEntryRead[]>([]);
  newLabel = '';
  creating = false;
  revealedToken: ApiTokenWithSecret | null = null;
  tokenError: string | null = null;
  moderationError: string | null = null;
  copied = false;
  loggingOut = false;
  playbackBusy = false;
  private readonly rowBusy = new Set<string>();
  rejectReasons: Record<string, string> = {};

  // Event configuration form (010, US5)
  eventConfig: EventConfigRead | null = null;
  configLoading = false;
  configSaving = false;
  configError: string | null = null;
  configSaved = false;
  apiKeyUsage: ApiKeyUsageListResponse | null = null;
  apiKeyUsageError: string | null = null;
  private stateSubscription: Subscription | null = null;
  private apiKeyUsageSubscription: Subscription | null = null;

  ngOnInit(): void {
    this.refreshTokens();
    this.refreshApiKeyUsage();
    this.loadEventConfig();
    void this.displayState.start();
    this.stateSubscription = this.displayState.state$.subscribe(() => {
      this.refreshPending();
      this.cdr.markForCheck();
    });
    this.apiKeyUsageSubscription = this.displayState.apiKeyUsage$.subscribe(usage => {
      if (usage) {
        this.apiKeyUsage = usage;
        this.cdr.markForCheck();
      }
    });
  }

  ngOnDestroy(): void {
    this.stateSubscription?.unsubscribe();
    this.apiKeyUsageSubscription?.unsubscribe();
    this.displayState.stop();
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

  refreshApiKeyUsage(): void {
    this.apiKeyUsageError = null;
    this.http
      .get<ApiKeyUsageListResponse>(`${this.baseUrl}/youtube/api-keys/usage`)
      .subscribe({
        next: res => {
          this.apiKeyUsage = res;
          this.cdr.markForCheck();
        },
        error: () => {
          this.apiKeyUsageError = 'No se pudo cargar el uso de API keys.';
          this.cdr.markForCheck();
        }
      });
  }

  formatResetAt(value: string | undefined): string {
    if (!value) {
      return '—';
    }
    const date = new Date(value);
    return date.toLocaleString('es-ES', {
      dateStyle: 'short',
      timeStyle: 'short',
      timeZone: 'America/Los_Angeles'
    });
  }

  usageStatusLabel(exhausted: boolean): string {
    return exhausted ? 'Agotada' : 'Activa';
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

  isRowBusy(id: string): boolean {
    return this.rowBusy.has(id);
  }

  approveEntry(id: string): void {
    this.rowBusy.add(id);
    this.cdr.markForCheck();
    this.queueAdmin.approve(id).subscribe({
      next: () => {
        this.rowBusy.delete(id);
        this.cdr.markForCheck();
      },
      error: err => {
        this.rowBusy.delete(id);
        this.moderationError = this.mapQueueError(err);
        this.cdr.markForCheck();
      }
    });
  }

  rejectEntry(id: string): void {
    this.rowBusy.add(id);
    this.cdr.markForCheck();
    this.queueAdmin.reject(id, this.rejectReasons[id]).subscribe({
      next: () => {
        this.rowBusy.delete(id);
        this.cdr.markForCheck();
      },
      error: err => {
        this.rowBusy.delete(id);
        this.moderationError = this.mapQueueError(err);
        this.cdr.markForCheck();
      }
    });
  }

  advancePlayback(): void {
    this.playbackBusy = true;
    this.queueAdmin.skipOrStart().subscribe({
      next: state => {
        this.playbackBusy = false;
        this.displayState.applyState(state);
        this.cdr.markForCheck();
      },
      error: err => {
        this.playbackBusy = false;
        this.moderationError = this.mapQueueError(err);
        this.cdr.markForCheck();
      }
    });
  }

  loadEventConfig(): void {
    this.configLoading = true;
    this.configError = null;
    this.eventConfigService.getConfig().subscribe({
      next: config => {
        this.eventConfig = { ...config };
        this.configLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.configLoading = false;
        this.configError = 'No se pudo cargar la configuración del evento.';
        this.cdr.markForCheck();
      }
    });
  }

  saveEventConfig(): void {
    if (!this.eventConfig) {
      return;
    }
    this.configSaving = true;
    this.configSaved = false;
    this.configError = null;
    this.eventConfigService
      .updateConfig({
        name: this.eventConfig.name,
        subtitle: this.eventConfig.subtitle,
        app_height_px: this.eventConfig.app_height_px,
        theme: this.eventConfig.theme,
        queue_visible_count: this.eventConfig.queue_visible_count
      })
      .subscribe({
        next: config => {
          this.eventConfig = { ...config };
          this.configSaving = false;
          this.configSaved = true;
          this.cdr.markForCheck();
        },
        error: err => {
          this.configSaving = false;
          this.configError =
            err?.status === 422
              ? 'Revisa los campos: valores fuera de rango.'
              : 'No se pudo guardar la configuración del evento.';
          this.cdr.markForCheck();
        }
      });
  }

  youtubeUrl(videoId: string): string {
    return `https://www.youtube.com/watch?v=${videoId}`;
  }

  formatDuration(durationSec: number | null | undefined): string {
    if (durationSec == null || durationSec < 0) {
      return '—';
    }
    const minutes = Math.floor(durationSec / 60);
    const seconds = durationSec % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }

  submitterLabel(entry: PendingQueueEntryRead): string {
    return entry.submitted_by_display_name?.trim() || '—';
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

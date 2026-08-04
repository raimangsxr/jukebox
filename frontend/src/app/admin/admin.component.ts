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
import { EventConfigRead, QueueMode } from '../models/event-config';
import { AuthService } from '../services/auth.service';
import { HistoryQueueEntryRead, PendingQueueEntryRead, ActiveQueueEntryRead, ActiveQueueListResponse } from '../models/jukebox-state';
import { DisplayStateService } from '../services/display-state.service';
import { EventConfigService } from '../services/event-config.service';
import {
  FillerReserveBatchValidation,
  FillerReserveEntryRead,
  FillerReserveService,
} from '../services/filler-reserve.service';
import { QueueAdminService } from '../services/queue-admin.service';
import { AdminStatsService } from '../services/admin-stats.service';
import { AdminStatsResponse } from '../models/admin-stats';
import {
  activeQueueEmptyCopy,
  parseVoteCountInput,
  queueSourceLabel,
  queueStatusLabel,
} from './admin-queue.util';
import {
  emptyRankingCopy,
  emptySummaryCopy,
  participantDisplayLabel,
  shouldFetchStatsOnPanelChange,
} from './admin-stats.util';
import { PlaybackAudioMode } from '../models/playback-status';
import { LiveStatusComponent } from '../components/live-status.component';
import { CollapsibleSectionComponent } from '../components/collapsible-section/collapsible-section.component';
import { LiveConnectionStatus } from '../services/live-connection';

type AdminPanelId = 'moderation' | 'queue' | 'history' | 'stats' | 'reserve' | 'apiKeys' | 'event' | 'tokens';

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
  imports: [CommonModule, FormsModule, LiveStatusComponent, CollapsibleSectionComponent],
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
  private readonly adminStats = inject(AdminStatsService);
  private readonly fillerReserve = inject(FillerReserveService);
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
  queuePanelError: string | null = null;
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
  queueMode: QueueMode = 'moderated';
  queueModeSaving = false;
  pendingQueueModeChange: QueueMode | null = null;
  playbackAudioMode: PlaybackAudioMode = 'idle';
  connectionStatus: LiveConnectionStatus = 'reconnecting';

  historyEntries: HistoryQueueEntryRead[] = [];
  historyTotal = 0;
  historyTotalAll = 0;
  historyPage = 1;
  historyPageSize = 25;
  historyStatusFilter: '' | 'played' | 'rejected' = '';
  historyLoading = false;
  historyError: string | null = null;
  pendingRequeueId: string | null = null;
  requeueBusy = false;
  pendingClearHistory = false;
  clearHistoryBusy = false;

  activeQueue: ActiveQueueListResponse | null = null;
  activeQueueLoading = false;
  activeQueueError: string | null = null;
  pendingClearActiveQueue = false;
  clearActiveQueueBusy = false;
  pendingDeleteActiveId: string | null = null;
  deleteActiveBusy = false;
  pendingVoteEditEntry: ActiveQueueEntryRead | null = null;
  voteEditInput = '';
  voteEditError: string | null = null;
  voteEditBusy = false;
  private readonly activeQueueRowBusy = new Set<string>();
  readonly activeQueueEmptyLabel = activeQueueEmptyCopy();

  statsSnapshot: AdminStatsResponse | null = null;
  statsLoading = false;
  statsError: string | null = null;
  readonly rankingEmptyLabel = emptyRankingCopy();
  readonly summaryEmptyLabel = emptySummaryCopy();

  readonly panelExpanded: Record<AdminPanelId, boolean> = {
    moderation: true,
    queue: false,
    history: false,
    stats: false,
    reserve: false,
    apiKeys: false,
    event: false,
    tokens: false,
  };

  reserveEntries: FillerReserveEntryRead[] = [];
  reserveLoading = false;
  reserveError: string | null = null;
  reserveInput = '';
  reserveBusy = false;
  fillerAutoInjectEnabled = true;
  fillerAutoInjectSaving = false;
  batchSource: 'csv' | 'playlist' | null = null;
  importFile: File | null = null;
  playlistUrl = '';
  batchValidation: FillerReserveBatchValidation | null = null;
  batchModalOpen = false;
  batchBusy = false;

  private stateSubscription: Subscription | null = null;
  private apiKeyUsageSubscription: Subscription | null = null;
  private playbackStatusSubscription: Subscription | null = null;

  ngOnInit(): void {
    this.refreshTokens();
    this.refreshApiKeyUsage();
    this.loadEventConfig();
    this.refreshHistory();
    this.refreshHistoryTotalAll();
    this.refreshReserve();
    void this.displayState.start();
    this.stateSubscription = this.displayState.state$.subscribe(() => {
      this.refreshPending();
      this.refreshHistory();
      this.refreshHistoryTotalAll();
      if (this.panelExpanded.queue) {
        this.loadActiveQueue();
      }
      this.cdr.markForCheck();
    });
    this.apiKeyUsageSubscription = this.displayState.apiKeyUsage$.subscribe(usage => {
      if (usage) {
        this.apiKeyUsage = usage;
        this.cdr.markForCheck();
      }
    });
    this.playbackStatusSubscription = this.displayState.playbackStatus$.subscribe(status => {
      this.playbackAudioMode = status?.audio_mode ?? 'idle';
      this.cdr.markForCheck();
    });
    this.displayState.connectionStatus$.subscribe(status => {
      this.connectionStatus = status;
      this.cdr.markForCheck();
    });
  }

  ngOnDestroy(): void {
    this.stateSubscription?.unsubscribe();
    this.apiKeyUsageSubscription?.unsubscribe();
    this.playbackStatusSubscription?.unsubscribe();
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

  get playbackStatusLabel(): string {
    const state = this.displayState.snapshot;
    if (!state) {
      return '';
    }
    if (state.now_playing) {
      if (this.playbackAudioMode === 'sound') {
        return `Sonando con audio: ${state.now_playing.title}`;
      }
      if (this.playbackAudioMode === 'muted') {
        return `Sonando sin audio: ${state.now_playing.title}`;
      }
      return `Sonando: ${state.now_playing.title}`;
    }
    if (state.queue.length > 0) {
      return `Cola lista — ${state.queue.length} canciones en espera`;
    }
    return 'Sin canciones en cola';
  }

  get playbackAudioHint(): string | null {
    const state = this.displayState.snapshot;
    if (!state?.now_playing || this.playbackAudioMode !== 'muted') {
      return null;
    }
    return 'La pantalla reproduce sin audio. Revisa Chromium kiosk (--autoplay-policy) o el iframe allow="autoplay".';
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
    this.queuePanelError = null;
    this.queueAdmin.skipOrStart().subscribe({
      next: state => {
        this.playbackBusy = false;
        this.displayState.applyState(state);
        if (this.panelExpanded.queue) {
          this.loadActiveQueue();
        }
        this.cdr.markForCheck();
      },
      error: err => {
        this.playbackBusy = false;
        this.queuePanelError = this.mapQueueControlError(err);
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
        this.queueMode = config.queue_mode;
        this.fillerAutoInjectEnabled = config.filler_auto_inject_enabled;
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

  onQueueModeChange(next: QueueMode): void {
    if (next === this.queueMode || this.queueModeSaving) {
      return;
    }
    this.pendingQueueModeChange = next;
    this.cdr.markForCheck();
  }

  get queueModeConfirmMessage(): string {
    if (this.pendingQueueModeChange === 'free') {
      return 'Los nuevos envíos entrarán directamente en la cola sin pasar por revisión.';
    }
    if (this.pendingQueueModeChange === 'moderated') {
      return 'Los nuevos envíos requerirán tu aprobación antes de entrar en la cola.';
    }
    return '';
  }

  get queueModeConfirmTitle(): string {
    if (this.pendingQueueModeChange === 'free') {
      return '¿Cambiar a modo Libre?';
    }
    if (this.pendingQueueModeChange === 'moderated') {
      return '¿Cambiar a modo Moderado?';
    }
    return 'Confirmar cambio de modo';
  }

  cancelQueueModeChange(): void {
    this.pendingQueueModeChange = null;
    this.cdr.markForCheck();
  }

  confirmQueueModeChange(): void {
    const next = this.pendingQueueModeChange;
    if (next === null || next === this.queueMode || this.queueModeSaving) {
      this.pendingQueueModeChange = null;
      this.cdr.markForCheck();
      return;
    }
    const previous = this.queueMode;
    this.pendingQueueModeChange = null;
    this.queueModeSaving = true;
    this.moderationError = null;
    this.eventConfigService.updateQueueMode(next).subscribe({
      next: config => {
        this.queueMode = config.queue_mode;
        if (this.eventConfig) {
          this.eventConfig = { ...this.eventConfig, queue_mode: config.queue_mode };
        }
        this.queueModeSaving = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.queueMode = previous;
        this.queueModeSaving = false;
        this.moderationError = 'No se pudo cambiar el modo de cola.';
        this.cdr.markForCheck();
      }
    });
  }

  queueModeLabel(mode: QueueMode): string {
    return mode === 'free' ? 'Libre' : 'Moderado';
  }

  setPanelExpanded(id: AdminPanelId, expanded: boolean): void {
    this.panelExpanded[id] = expanded;
    if (id === 'queue' && expanded) {
      this.loadActiveQueue();
    }
    if (shouldFetchStatsOnPanelChange(id, expanded)) {
      this.loadStats();
    }
    this.cdr.markForCheck();
  }

  loadActiveQueue(): void {
    this.activeQueueLoading = true;
    this.activeQueueError = null;
    this.queueAdmin.getActiveQueue().subscribe({
      next: res => {
        this.activeQueue = res;
        this.activeQueueLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.activeQueueLoading = false;
        this.activeQueueError = 'No se pudo cargar la cola de reproducción.';
        this.cdr.markForCheck();
      },
    });
  }

  activeQueueCount(): number {
    if (!this.activeQueue) {
      return 0;
    }
    return (this.activeQueue.now_playing ? 1 : 0) + this.activeQueue.queued.length;
  }

  isActiveQueueEmpty(): boolean {
    return this.activeQueueCount() === 0;
  }

  queueBadge(): string {
    const count = this.activeQueueCount();
    return `${count} en cola`;
  }

  activeQueueRows(): ActiveQueueEntryRead[] {
    if (!this.activeQueue) {
      return [];
    }
    const rows: ActiveQueueEntryRead[] = [];
    if (this.activeQueue.now_playing) {
      rows.push(this.activeQueue.now_playing);
    }
    rows.push(...this.activeQueue.queued);
    return rows;
  }

  isNowPlayingEntry(entry: ActiveQueueEntryRead): boolean {
    return this.activeQueue?.now_playing?.id === entry.id;
  }

  isActiveQueueRowBusy(id: string): boolean {
    return this.activeQueueRowBusy.has(id);
  }

  activeQueueSubmitterLabel(entry: ActiveQueueEntryRead): string {
    return entry.submitted_by_display_name?.trim() || '—';
  }

  activeQueueSourceLabel(source: string): string {
    return queueSourceLabel(source);
  }

  activeQueueStatusLabel(entry: ActiveQueueEntryRead): string {
    return queueStatusLabel(entry.status, this.isNowPlayingEntry(entry));
  }

  priorityLabel(priority: 'normal' | 'low' | undefined): string {
    return priority === 'low' ? 'Baja' : 'Normal';
  }

  formatCreatedAt(value: string | undefined): string {
    return this.formatResetAt(value);
  }

  requestClearActiveQueue(): void {
    if (this.isActiveQueueEmpty() || this.clearActiveQueueBusy) {
      return;
    }
    this.pendingClearActiveQueue = true;
    this.cdr.markForCheck();
  }

  cancelClearActiveQueue(): void {
    this.pendingClearActiveQueue = false;
    this.cdr.markForCheck();
  }

  confirmClearActiveQueue(): void {
    if (this.clearActiveQueueBusy) {
      return;
    }
    this.clearActiveQueueBusy = true;
    this.queuePanelError = null;
    this.queueAdmin.clearActiveQueue().subscribe({
      next: state => {
        this.clearActiveQueueBusy = false;
        this.pendingClearActiveQueue = false;
        this.displayState.applyState(state);
        this.activeQueue = { now_playing: null, queued: [] };
        this.cdr.markForCheck();
      },
      error: err => {
        this.clearActiveQueueBusy = false;
        this.pendingClearActiveQueue = false;
        this.queuePanelError = this.mapQueueControlError(err);
        this.cdr.markForCheck();
      },
    });
  }

  requestDeleteActive(entryId: string): void {
    this.pendingDeleteActiveId = entryId;
    this.cdr.markForCheck();
  }

  cancelDeleteActive(): void {
    this.pendingDeleteActiveId = null;
    this.cdr.markForCheck();
  }

  confirmDeleteActive(): void {
    const entryId = this.pendingDeleteActiveId;
    if (!entryId || this.deleteActiveBusy) {
      return;
    }
    this.deleteActiveBusy = true;
    this.queuePanelError = null;
    this.queueAdmin.deleteActiveEntry(entryId).subscribe({
      next: state => {
        this.deleteActiveBusy = false;
        this.pendingDeleteActiveId = null;
        this.displayState.applyState(state);
        this.loadActiveQueue();
        this.cdr.markForCheck();
      },
      error: err => {
        this.deleteActiveBusy = false;
        this.pendingDeleteActiveId = null;
        this.queuePanelError = this.mapQueueControlError(err);
        this.cdr.markForCheck();
      },
    });
  }

  forcePlayEntry(entryId: string): void {
    if (this.isActiveQueueRowBusy(entryId)) {
      return;
    }
    this.activeQueueRowBusy.add(entryId);
    this.queuePanelError = null;
    this.queueAdmin.playNow(entryId).subscribe({
      next: state => {
        this.activeQueueRowBusy.delete(entryId);
        this.displayState.applyState(state);
        this.loadActiveQueue();
        this.cdr.markForCheck();
      },
      error: err => {
        this.activeQueueRowBusy.delete(entryId);
        this.queuePanelError = this.mapQueueControlError(err);
        this.cdr.markForCheck();
      },
    });
  }

  requestVoteEdit(entry: ActiveQueueEntryRead): void {
    this.pendingVoteEditEntry = entry;
    this.voteEditInput = String(entry.vote_count);
    this.voteEditError = null;
    this.cdr.markForCheck();
  }

  cancelVoteEdit(): void {
    this.pendingVoteEditEntry = null;
    this.voteEditInput = '';
    this.voteEditError = null;
    this.cdr.markForCheck();
  }

  saveVoteEdit(): void {
    const entry = this.pendingVoteEditEntry;
    if (!entry || this.voteEditBusy) {
      return;
    }
    const parsed = parseVoteCountInput(this.voteEditInput);
    if (!parsed.valid) {
      this.voteEditError = parsed.message;
      this.cdr.markForCheck();
      return;
    }
    this.voteEditBusy = true;
    this.voteEditError = null;
    this.queuePanelError = null;
    this.queueAdmin.setVoteCount(entry.id, parsed.value).subscribe({
      next: state => {
        this.voteEditBusy = false;
        this.pendingVoteEditEntry = null;
        this.voteEditInput = '';
        this.displayState.applyState(state);
        this.loadActiveQueue();
        this.cdr.markForCheck();
      },
      error: err => {
        this.voteEditBusy = false;
        if (err?.status === 422) {
          this.voteEditError = 'El valor de votos no es válido.';
        } else {
          this.voteEditError = this.mapQueueControlError(err);
        }
        this.cdr.markForCheck();
      },
    });
  }

  loadStats(): void {
    this.statsLoading = true;
    this.statsError = null;
    this.adminStats.getStats().subscribe({
      next: stats => {
        this.statsSnapshot = stats;
        this.statsLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.statsLoading = false;
        this.statsError = 'No se pudieron cargar las estadísticas.';
        this.cdr.markForCheck();
      },
    });
  }

  statsParticipantLabel(item: { display_name: string }): string {
    return participantDisplayLabel(item as Parameters<typeof participantDisplayLabel>[0]);
  }

  moderationBadge(): string {
    const count = this.pending().length;
    return `${count} pendiente${count === 1 ? '' : 's'}`;
  }

  historyBadge(): string {
    return `${this.historyTotalAll} entrada${this.historyTotalAll === 1 ? '' : 's'}`;
  }

  refreshHistoryTotalAll(): void {
    this.queueAdmin.getHistory({ page: 1, page_size: 1 }).subscribe({
      next: res => {
        this.historyTotalAll = res.total;
        this.cdr.markForCheck();
      },
    });
  }

  refreshHistory(): void {
    this.historyLoading = true;
    this.historyError = null;
    const params: { page: number; page_size: number; status?: 'played' | 'rejected' } = {
      page: this.historyPage,
      page_size: this.historyPageSize,
    };
    if (this.historyStatusFilter) {
      params.status = this.historyStatusFilter;
    }
    this.queueAdmin.getHistory(params).subscribe({
      next: res => {
        this.historyEntries = res.entries;
        this.historyTotal = res.total;
        this.historyLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.historyLoading = false;
        this.historyError = 'No se pudo cargar el historial.';
        this.cdr.markForCheck();
      },
    });
  }

  onHistoryFilterChange(value: '' | 'played' | 'rejected'): void {
    this.historyStatusFilter = value;
    this.historyPage = 1;
    this.refreshHistory();
  }

  historyPageCount(): number {
    return Math.max(1, Math.ceil(this.historyTotal / this.historyPageSize));
  }

  goHistoryPage(page: number): void {
    const max = this.historyPageCount();
    if (page < 1 || page > max) {
      return;
    }
    this.historyPage = page;
    this.refreshHistory();
  }

  requestRequeue(entryId: string): void {
    this.pendingRequeueId = entryId;
    this.cdr.markForCheck();
  }

  cancelRequeue(): void {
    this.pendingRequeueId = null;
    this.cdr.markForCheck();
  }

  confirmRequeue(): void {
    const entryId = this.pendingRequeueId;
    if (!entryId || this.requeueBusy) {
      return;
    }
    this.requeueBusy = true;
    this.queueAdmin.requeue(entryId).subscribe({
      next: () => {
        this.requeueBusy = false;
        this.pendingRequeueId = null;
        this.refreshHistory();
        this.refreshHistoryTotalAll();
        this.cdr.markForCheck();
      },
      error: err => {
        this.requeueBusy = false;
        this.historyError = this.mapQueueError(err);
        this.pendingRequeueId = null;
        this.cdr.markForCheck();
      },
    });
  }

  historyStatusLabel(status: string): string {
    return status === 'played' ? 'Reproducida' : status === 'rejected' ? 'Rechazada' : status;
  }

  requestClearHistory(): void {
    if (this.historyTotalAll === 0 || this.clearHistoryBusy) {
      return;
    }
    this.pendingClearHistory = true;
    this.cdr.markForCheck();
  }

  cancelClearHistory(): void {
    this.pendingClearHistory = false;
    this.cdr.markForCheck();
  }

  confirmClearHistory(): void {
    if (this.clearHistoryBusy) {
      return;
    }
    this.clearHistoryBusy = true;
    this.historyError = null;
    this.queueAdmin.clearHistory().subscribe({
      next: () => {
        this.clearHistoryBusy = false;
        this.pendingClearHistory = false;
        this.historyEntries = [];
        this.historyTotal = 0;
        this.historyTotalAll = 0;
        this.historyPage = 1;
        this.cdr.markForCheck();
      },
      error: () => {
        this.clearHistoryBusy = false;
        this.pendingClearHistory = false;
        this.historyError = 'No se pudo vaciar el historial.';
        this.cdr.markForCheck();
      },
    });
  }

  sourceLabel(source: string): string {
    switch (source) {
      case 'participant':
        return 'Participante';
      case 'operator_requeue':
        return 'Re-encolada';
      case 'operator_filler':
        return 'Reserva';
      case 'operator_direct':
        return 'Operador';
      case 'auto_inject':
        return 'Auto-inyección';
      default:
        return source;
    }
  }

  refreshReserve(): void {
    this.reserveLoading = true;
    this.reserveError = null;
    this.fillerReserve.list().subscribe({
      next: res => {
        this.reserveEntries = res.entries;
        this.reserveLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.reserveLoading = false;
        this.reserveError = 'No se pudo cargar la reserva de relleno.';
        this.cdr.markForCheck();
      },
    });
  }

  exportReserveCsv(): void {
    if (this.reserveBusy || this.batchBusy) {
      return;
    }
    this.reserveError = null;
    this.fillerReserve.exportCsv().subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `filler-reserve-${new Date().toISOString().slice(0, 10)}.csv`;
        anchor.click();
        URL.revokeObjectURL(url);
      },
      error: () => {
        this.reserveError = 'No se pudo exportar la reserva.';
        this.cdr.markForCheck();
      },
    });
  }

  onImportFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    this.importFile = file;
    this.batchSource = 'csv';
    this.batchBusy = true;
    this.reserveError = null;
    this.fillerReserve.validateImport(file).subscribe({
      next: validation => {
        this.batchValidation = validation;
        this.batchModalOpen = true;
        this.batchBusy = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.importFile = null;
        this.batchSource = null;
        this.batchBusy = false;
        this.reserveError = 'No se pudo validar el fichero de importación.';
        this.cdr.markForCheck();
      },
    });
  }

  validatePlaylist(): void {
    const url = this.playlistUrl.trim();
    if (!url || this.batchBusy) {
      return;
    }
    this.batchSource = 'playlist';
    this.importFile = null;
    this.batchBusy = true;
    this.reserveError = null;
    this.fillerReserve.validatePlaylist(url).subscribe({
      next: validation => {
        this.batchValidation = validation;
        this.batchModalOpen = true;
        this.batchBusy = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.batchSource = null;
        this.batchBusy = false;
        this.reserveError = 'No se pudo validar la playlist.';
        this.cdr.markForCheck();
      },
    });
  }

  cancelBatch(): void {
    this.batchModalOpen = false;
    this.importFile = null;
    this.batchValidation = null;
    this.batchSource = null;
    this.cdr.markForCheck();
  }

  confirmBatch(): void {
    if (!this.batchValidation?.can_confirm || this.batchBusy || !this.batchSource) {
      return;
    }
    this.batchBusy = true;
    const request =
      this.batchSource === 'csv' && this.importFile
        ? this.fillerReserve.importReserve(this.importFile)
        : this.batchSource === 'playlist'
          ? this.fillerReserve.addPlaylist(this.playlistUrl.trim())
          : null;
    if (!request) {
      this.batchBusy = false;
      return;
    }
    request.subscribe({
      next: res => {
        this.reserveEntries = res.entries;
        this.batchBusy = false;
        if (this.batchSource === 'playlist') {
          this.playlistUrl = '';
        }
        this.cancelBatch();
        this.cdr.markForCheck();
      },
      error: err => {
        this.batchBusy = false;
        const errors = err.error?.detail?.errors as { line: number; detail: string }[] | undefined;
        if (errors?.length && this.batchValidation) {
          this.batchValidation = {
            ...this.batchValidation,
            can_confirm: false,
            errors,
          };
        } else {
          this.reserveError =
            this.batchSource === 'csv'
              ? 'No se pudo importar la reserva.'
              : 'No se pudo añadir la playlist.';
          this.cancelBatch();
        }
        this.cdr.markForCheck();
      },
    });
  }

  clearReserve(): void {
    if (this.reserveBusy || this.batchBusy || this.reserveEntries.length === 0) {
      return;
    }
    if (
      !confirm(
        '¿Vaciar toda la reserva de relleno? Esta acción no se puede deshacer.',
      )
    ) {
      return;
    }
    this.reserveBusy = true;
    this.reserveError = null;
    this.fillerReserve.clearReserve().subscribe({
      next: () => {
        this.reserveBusy = false;
        this.refreshReserve();
      },
      error: () => {
        this.reserveBusy = false;
        this.reserveError = 'No se pudo vaciar la reserva.';
        this.cdr.markForCheck();
      },
    });
  }

  mapBatchError(detail: string): string {
    switch (detail) {
      case 'invalid youtube reference':
        return 'Referencia de YouTube no válida';
      case 'duplicate in file':
        return 'Vídeo duplicado en el fichero';
      case 'duplicate in batch':
        return 'Vídeo duplicado en el lote';
      case 'playlist unavailable':
        return 'Playlist no disponible';
      case 'playlist empty':
        return 'La playlist no tiene vídeos';
      case 'playlist too large':
        return 'La playlist supera el tamaño máximo procesable';
      default:
        return detail;
    }
  }

  batchModalTitle(): string {
    return this.batchSource === 'playlist'
      ? 'Añadir playlist a la reserva'
      : 'Importar reserva desde CSV';
  }

  batchConfirmLabel(): string {
    return this.batchBusy
      ? 'Añadiendo…'
      : this.batchSource === 'playlist'
        ? 'Confirmar playlist'
        : 'Confirmar importación';
  }

  addToReserve(): void {
    const value = this.reserveInput.trim();
    if (!value || this.reserveBusy) {
      return;
    }
    this.reserveBusy = true;
    this.reserveError = null;
    this.fillerReserve.add({ youtube_url_or_id: value }).subscribe({
      next: () => {
        this.reserveInput = '';
        this.reserveBusy = false;
        this.refreshReserve();
      },
      error: err => {
        this.reserveBusy = false;
        this.reserveError = this.mapQueueError(err);
        this.cdr.markForCheck();
      },
    });
  }

  deleteReserveEntry(id: string): void {
    this.fillerReserve.delete(id).subscribe({
      next: () => this.refreshReserve(),
      error: err => {
        this.reserveError = this.mapQueueError(err);
        this.cdr.markForCheck();
      },
    });
  }

  moveReserveEntry(id: string, direction: -1 | 1): void {
    const index = this.reserveEntries.findIndex(entry => entry.id === id);
    if (index < 0) {
      return;
    }
    const target = index + direction;
    if (target < 0 || target >= this.reserveEntries.length) {
      return;
    }
    const ordered = [...this.reserveEntries];
    const [item] = ordered.splice(index, 1);
    ordered.splice(target, 0, item);
    this.fillerReserve.reorder(ordered.map(entry => entry.id)).subscribe({
      next: res => {
        this.reserveEntries = res.entries;
        this.cdr.markForCheck();
      },
      error: err => {
        this.reserveError = this.mapQueueError(err);
        this.cdr.markForCheck();
      },
    });
  }

  enqueueReserveEntry(id: string): void {
    this.reserveBusy = true;
    this.fillerReserve.enqueue(id).subscribe({
      next: () => {
        this.reserveBusy = false;
        this.refreshReserve();
      },
      error: err => {
        this.reserveBusy = false;
        this.reserveError = this.mapQueueError(err);
        this.cdr.markForCheck();
      },
    });
  }

  operatorDirectEnqueue(): void {
    const value = this.reserveInput.trim();
    if (!value || this.reserveBusy) {
      return;
    }
    this.reserveBusy = true;
    this.reserveError = null;
    this.queueAdmin.operatorSubmit(value).subscribe({
      next: () => {
        this.reserveInput = '';
        this.reserveBusy = false;
        this.cdr.markForCheck();
      },
      error: err => {
        this.reserveBusy = false;
        this.reserveError = this.mapQueueError(err);
        this.cdr.markForCheck();
      },
    });
  }

  onFillerAutoInjectToggle(enabled: boolean): void {
    if (this.fillerAutoInjectSaving) {
      return;
    }
    const previous = this.fillerAutoInjectEnabled;
    this.fillerAutoInjectEnabled = enabled;
    this.fillerAutoInjectSaving = true;
    this.eventConfigService.updateFillerAutoInject(enabled).subscribe({
      next: config => {
        this.fillerAutoInjectEnabled = config.filler_auto_inject_enabled;
        if (this.eventConfig) {
          this.eventConfig = {
            ...this.eventConfig,
            filler_auto_inject_enabled: config.filler_auto_inject_enabled,
          };
        }
        this.fillerAutoInjectSaving = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.fillerAutoInjectEnabled = previous;
        this.fillerAutoInjectSaving = false;
        this.configError = 'No se pudo actualizar la inyección automática.';
        this.cdr.markForCheck();
      },
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
      case 'filler reserve is full':
        return 'La reserva de relleno está llena (50 canciones).';
      case 'nothing to advance':
        return 'No hay nada que reproducir ni saltar.';
      case 'invalid status transition':
        return 'Esta entrada ya no se puede moderar.';
      default:
        return 'No se pudo completar la acción de moderación.';
    }
  }

  private mapQueueControlError(err: { error?: { detail?: string }; status?: number }): string {
    const detail = err.error?.detail;
    switch (detail) {
      case 'queue is full':
        return 'La cola está llena (100 canciones).';
      case 'video already in queue':
        return 'Ese vídeo ya está en la cola activa.';
      case 'nothing to advance':
        return 'No hay nada que reproducir ni saltar.';
      case 'queue entry not found':
        return 'La entrada ya no existe en la cola.';
      case 'entry not active':
        return 'La entrada ya no está en la cola activa.';
      case 'invalid status':
        return 'Esta entrada no se puede modificar en la cola activa.';
      default:
        if (err.status === 422) {
          return 'Los datos enviados no son válidos.';
        }
        return 'No se pudo completar la acción en la cola de reproducción.';
    }
  }
}

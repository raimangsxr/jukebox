import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnDestroy,
  OnInit,
  inject
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription, firstValueFrom } from 'rxjs';

import { ParticipantStateResponse, QueueEntryRead } from '../models/jukebox-state';
import { ParticipantRead } from '../models/participant-state';
import { SearchResultItem } from '../models/youtube-search';
import { ParticipantStateService } from '../services/participant-state.service';
import { ParticipantService } from '../services/participant.service';
import { environment } from '../../environments/environment';

import { NotificationToastComponent } from './notification-toast.component';
import {
  SubmitActivePath,
  canSubmitFromActivePath,
  isSearchQueryValid,
  nextActivePathOnSearchSelect,
  nextActivePathOnUrlEdit,
  resolveActivePathOnUrlFocus
} from './participate-submit.util';

const STATUS_LABELS: Record<string, string> = {
  pending_review: 'Pendiente de revisión',
  queued: 'En cola',
  playing: 'Sonando',
  played: 'Reproducida',
  rejected: 'Rechazada'
};

@Component({
  selector: 'app-participate',
  standalone: true,
  imports: [FormsModule, NotificationToastComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './participate.component.html',
  styleUrl: './participate.component.css'
})
export class ParticipateComponent implements OnInit, OnDestroy {
  private readonly participantService = inject(ParticipantService);
  private readonly stateService = inject(ParticipantStateService);
  private readonly cdr = inject(ChangeDetectorRef);

  authenticated = false;
  loading = true;
  state: ParticipantStateResponse | null = null;
  participant: ParticipantRead | null = null;
  submissions: QueueEntryRead[] = [];
  errorMessage: string | null = null;
  submitUrl = '';
  submitting = false;
  votingEntryId: string | null = null;
  showDevAuth = false;
  googleOAuthEnabled = false;

  searchEnabled = false;
  searchQuery = '';
  searchResults: SearchResultItem[] = [];
  selectedResult: SearchResultItem | null = null;
  searchLoading = false;
  searchMessage: string | null = null;
  activePath: SubmitActivePath = null;
  lastSearchQuery = '';

  private stateSub: Subscription | null = null;
  private submissionsSub: Subscription | null = null;

  ngOnInit(): void {
    const params = new URLSearchParams(window.location.search);
    const oauthError = this.participantService.parseOAuthReturnQuery(window.location.search);
    if (oauthError) {
      this.errorMessage = oauthError;
    }
    if (params.has('oauth') || params.has('oauth_error')) {
      window.history.replaceState({}, '', window.location.pathname);
    }
    this.showDevAuth =
      environment.allowDevParticipantAuth || params.get('dev') === '1';
    void this.initialize();
  }

  private async initialize(): Promise<void> {
    try {
      const oauthConfig = await firstValueFrom(this.participantService.getOAuthConfig());
      this.googleOAuthEnabled = oauthConfig.enabled;
    } catch {
      this.googleOAuthEnabled = false;
    }
    await this.bootstrap();
  }

  ngOnDestroy(): void {
    this.stateSub?.unsubscribe();
    this.submissionsSub?.unsubscribe();
    this.stateService.stop();
  }

  async bootstrap(): Promise<void> {
    this.stateService.stop();
    this.stateSub?.unsubscribe();
    this.submissionsSub?.unsubscribe();
    this.loading = true;
    const participant = await this.participantService.loadMe();
    this.authenticated = participant !== null;
    this.participant = participant;
    if (this.authenticated) {
      try {
        const config = await firstValueFrom(this.participantService.getSearchConfig());
        this.searchEnabled = config.enabled;
        await this.stateService.start();
        this.stateSub = this.stateService.state$.subscribe(state => {
          this.state = state;
          this.cdr.markForCheck();
        });
        this.submissionsSub = this.stateService.submissions$.subscribe(entries => {
          this.submissions = entries;
          this.cdr.markForCheck();
        });
      } catch {
        this.authenticated = false;
        this.participant = null;
        this.participantService.clearSession();
      }
    }
    this.loading = false;
    this.cdr.markForCheck();
  }

  signInGoogle(): void {
    this.errorMessage = null;
    if (!this.googleOAuthEnabled) {
      this.errorMessage =
        'El inicio de sesión con Google no está configurado en el servidor. Contacta con el organizador.';
      this.cdr.markForCheck();
      return;
    }
    this.participantService.startGoogleLogin();
  }

  async signInDev(): Promise<void> {
    this.errorMessage = null;
    try {
      await this.participantService.devAuthAsync();
      await this.bootstrap();
    } catch {
      this.errorMessage = 'No se pudo iniciar sesión de participante.';
      this.cdr.markForCheck();
    }
  }

  onUrlModelChange(value: string): void {
    this.submitUrl = value;
    this.onUrlTextEdit();
  }

  onUrlTextEdit(): void {
    this.activePath = nextActivePathOnUrlEdit();
  }

  onUrlFocus(): void {
    this.activePath = resolveActivePathOnUrlFocus(this.activePath);
  }

  selectSearchResult(result: SearchResultItem): void {
    this.selectedResult = result;
    this.activePath = nextActivePathOnSearchSelect();
    this.cdr.markForCheck();
  }

  async runSearch(): Promise<void> {
    if (!this.authenticated || !this.searchEnabled || this.searchLoading) {
      return;
    }
    this.searchMessage = null;
    if (!isSearchQueryValid(this.searchQuery)) {
      this.searchMessage = this.participantService.mapSearchError('invalid search query');
      this.cdr.markForCheck();
      return;
    }
    this.searchLoading = true;
    this.selectedResult = null;
    this.searchResults = [];
    this.cdr.markForCheck();
    try {
      const response = await firstValueFrom(
        this.participantService.searchYoutube(this.searchQuery.trim())
      );
      this.searchResults = response.results;
      this.lastSearchQuery = this.searchQuery.trim();
      if (!response.results.length) {
        this.searchMessage =
          'No hay resultados. Prueba otra búsqueda o pega un enlace.';
      }
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: string } })?.error?.detail;
      this.searchMessage = this.participantService.mapSearchError(detail);
    } finally {
      this.searchLoading = false;
      this.cdr.markForCheck();
    }
  }

  onSearchKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      event.preventDefault();
      void this.runSearch();
    }
  }

  canSubmit(): boolean {
    if (this.submitting) {
      return false;
    }
    return canSubmitFromActivePath(
      this.activePath,
      this.submitUrl,
      this.selectedResult?.youtube_video_id ?? null
    );
  }

  async submitSong(): Promise<void> {
    if (!this.authenticated || !this.canSubmit()) {
      return;
    }
    this.errorMessage = null;
    this.submitting = true;
    this.cdr.markForCheck();
    try {
      if (this.activePath === 'search' && this.selectedResult) {
        await firstValueFrom(
          this.participantService.submitSong(
            this.selectedResult.youtube_video_id,
            this.lastSearchQuery || this.searchQuery.trim()
          )
        );
        this.selectedResult = null;
        this.searchResults = [];
        this.searchQuery = '';
        this.lastSearchQuery = '';
      } else if (this.activePath === 'url') {
        await firstValueFrom(
          this.participantService.submitSong(this.submitUrl.trim())
        );
        this.submitUrl = '';
      }
      await this.stateService.refreshSubmissions();
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: string } })?.error?.detail;
      this.errorMessage = this.participantService.mapSubmitError(
        detail,
        this.state?.max_pending_submissions ?? 2
      );
    } finally {
      this.submitting = false;
      this.cdr.markForCheck();
    }
  }

  async vote(entry: QueueEntryRead): Promise<void> {
    if (!this.authenticated || this.votingEntryId) {
      return;
    }
    this.errorMessage = null;
    this.votingEntryId = entry.id;
    this.cdr.markForCheck();
    try {
      const response = await firstValueFrom(this.participantService.castVote(entry.id));
      this.stateService.applyVoteResponse(response.votes_remaining, response.state);
      this.state = this.stateService.snapshot;
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: string } })?.error?.detail;
      if (detail === 'vote limit exceeded') {
        this.errorMessage = 'Has agotado tus votos. Espera unos minutos para votar de nuevo.';
      } else if (detail === 'entry not votable') {
        this.errorMessage = 'Esta canción ya no admite votos.';
      } else {
        this.errorMessage = 'No se pudo registrar el voto.';
      }
    } finally {
      this.votingEntryId = null;
      this.cdr.markForCheck();
    }
  }

  votesRemainingLabel(): string {
    const remaining = this.state?.votes_remaining ?? 2;
    return `${remaining} de 2 votos disponibles`;
  }

  statusLabel(status: string): string {
    return STATUS_LABELS[status] ?? status;
  }

  isSearchSectionActive(): boolean {
    return this.activePath === 'search';
  }

  isUrlSectionActive(): boolean {
    return this.activePath === 'url';
  }
}

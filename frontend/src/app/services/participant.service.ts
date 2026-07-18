import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, firstValueFrom, tap } from 'rxjs';

import { environment } from '../../environments/environment';
import { QueueEntryRead } from '../models/jukebox-state';
import { ParticipantMeResponse } from '../models/participant-state';
import { SearchConfigResponse, SearchResponse } from '../models/youtube-search';

const SUBMIT_ERROR_MESSAGES: Record<string, string> = {
  'pending submission limit reached':
    'Has alcanzado el límite de canciones pendientes (2).',
  'active song limit reached': 'Ya tienes una canción activa en cola o sonando.',
  'video already in queue':
    'Ese vídeo ya está en la cola o pendiente de revisión.',
  'invalid youtube reference': 'Enlace de YouTube no válido o vídeo no disponible.',
  'not authenticated': 'Inicia sesión para continuar.'
};

const SEARCH_ERROR_MESSAGES: Record<string, string> = {
  'search rate limit exceeded':
    'Has hecho demasiadas búsquedas. Espera unos minutos o pega un enlace.',
  'youtube search unavailable':
    'La búsqueda no está disponible ahora. Puedes pegar un enlace de YouTube.',
  'invalid search query': 'Escribe al menos 2 caracteres para buscar.',
  'not authenticated': 'Inicia sesión para continuar.'
};

const OAUTH_ERROR_MESSAGES: Record<string, string> = {
  denied: 'Inicio de sesión cancelado o denegado.',
  invalid_state: 'Sesión de inicio no válida. Inténtalo de nuevo.',
  exchange_failed: 'No se pudo completar el inicio de sesión con Google.',
  not_configured:
    'El inicio de sesión con Google no está configurado en el servidor. Contacta con el organizador.'
};

@Injectable({ providedIn: 'root' })
export class ParticipantService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  private readonly participantSignal = signal<ParticipantMeResponse['participant'] | null>(null);

  readonly participant = this.participantSignal.asReadonly();

  startGoogleLogin(): void {
    window.location.href = `${this.baseUrl}/auth/google/login`;
  }

  getOAuthConfig(): Observable<{ enabled: boolean }> {
    return this.http.get<{ enabled: boolean }>(`${this.baseUrl}/auth/google/config`);
  }

  parseOAuthReturnQuery(search: string): string | null {
    const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search);
    const error = params.get('oauth_error');
    if (error) {
      return OAUTH_ERROR_MESSAGES[error] ?? 'No se pudo iniciar sesión con Google.';
    }
    if (params.has('oauth')) {
      return null;
    }
    return null;
  }

  mapSubmitError(detail: string | undefined): string {
    if (!detail) {
      return 'No se pudo enviar la canción.';
    }
    return SUBMIT_ERROR_MESSAGES[detail] ?? 'No se pudo enviar la canción.';
  }

  mapSearchError(detail: string | undefined): string {
    if (!detail) {
      return 'No se pudo completar la búsqueda.';
    }
    return SEARCH_ERROR_MESSAGES[detail] ?? 'No se pudo completar la búsqueda.';
  }

  getSearchConfig(): Observable<SearchConfigResponse> {
    return this.http.get<SearchConfigResponse>(`${this.baseUrl}/youtube/search/config`);
  }

  searchYoutube(query: string): Observable<SearchResponse> {
    return this.http.get<SearchResponse>(`${this.baseUrl}/youtube/search`, {
      params: { q: query }
    });
  }

  async loadMe(): Promise<ParticipantMeResponse['participant'] | null> {
    try {
      const response = await firstValueFrom(
        this.http.get<ParticipantMeResponse>(`${this.baseUrl}/participant/me`)
      );
      this.participantSignal.set(response.participant);
      return response.participant;
    } catch {
      this.participantSignal.set(null);
      return null;
    }
  }

  devAuth(displayName = 'Participante'): Observable<ParticipantMeResponse> {
    return this.http
      .post<ParticipantMeResponse>(`${this.baseUrl}/participant/dev-auth`, {
        display_name: displayName
      })
      .pipe(tap(response => this.participantSignal.set(response.participant)));
  }

  async devAuthAsync(displayName = 'Participante'): Promise<ParticipantMeResponse['participant']> {
    const response = await firstValueFrom(this.devAuth(displayName));
    return response.participant;
  }

  submitSong(urlOrId: string, searchQuery?: string): Observable<QueueEntryRead> {
    const body: { youtube_url_or_id: string; search_query?: string } = {
      youtube_url_or_id: urlOrId
    };
    if (searchQuery?.trim()) {
      body.search_query = searchQuery.trim();
    }
    return this.http.post<QueueEntryRead>(`${this.baseUrl}/queue/submit`, body);
  }

  getSubmissions(): Observable<{ entries: QueueEntryRead[] }> {
    return this.http.get<{ entries: QueueEntryRead[] }>(
      `${this.baseUrl}/participant/submissions`
    );
  }

  castVote(queueEntryId: string) {
    return this.http.post<import('../models/participant-state').VoteResponse>(
      `${this.baseUrl}/votes`,
      { queue_entry_id: queueEntryId }
    );
  }

  clearSession(): void {
    this.participantSignal.set(null);
  }
}

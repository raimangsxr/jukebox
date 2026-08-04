import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  HistoryListResponse,
  PendingListResponse,
  QueueEntryRead,
  StateResponse,
} from '../models/jukebox-state';

@Injectable({ providedIn: 'root' })
export class QueueAdminService {

  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  getPending(): Observable<PendingListResponse> {
    return this.http.get<PendingListResponse>(`${this.baseUrl}/queue/pending`);
  }

  approve(id: string): Observable<QueueEntryRead> {
    return this.http.post<QueueEntryRead>(`${this.baseUrl}/queue/${id}/approve`, {});
  }

  reject(id: string, reason?: string): Observable<QueueEntryRead> {
    return this.http.post<QueueEntryRead>(`${this.baseUrl}/queue/${id}/reject`, {
      reason: reason ?? null,
    });
  }

  skipOrStart(): Observable<StateResponse> {
    return this.http.post<StateResponse>(`${this.baseUrl}/queue/skip`, {});
  }

  getHistory(params?: {
    status?: 'played' | 'rejected';
    page?: number;
    page_size?: number;
  }): Observable<HistoryListResponse> {
    return this.http.get<HistoryListResponse>(`${this.baseUrl}/queue/history`, {
      params: params as Record<string, string | number>,
    });
  }

  requeue(historyEntryId: string): Observable<QueueEntryRead> {
    return this.http.post<QueueEntryRead>(
      `${this.baseUrl}/queue/history/${historyEntryId}/requeue`,
      {}
    );
  }

  operatorSubmit(youtubeUrlOrId: string, searchQuery?: string): Observable<QueueEntryRead> {
    return this.http.post<QueueEntryRead>(`${this.baseUrl}/queue/operator-submit`, {
      youtube_url_or_id: youtubeUrlOrId,
      search_query: searchQuery ?? null,
    });
  }
}

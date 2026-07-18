import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
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
}

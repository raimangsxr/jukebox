import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { QueueEntryRead } from '../models/jukebox-state';

export interface FillerReserveEntryRead {
  id: string;
  youtube_video_id: string;
  title: string;
  thumbnail_url: string | null;
  duration_sec: number | null;
  position: number;
  created_at: string;
}

export interface FillerReserveListResponse {
  entries: FillerReserveEntryRead[];
}

export interface FillerReserveAddRequest {
  youtube_url_or_id: string;
  search_query?: string | null;
}

export interface FillerReserveBatchLineError {
  line: number;
  detail: string;
}

export interface FillerReserveBatchValidation {
  add_count: number;
  skipped_in_reserve: number;
  skipped_in_queue: number;
  skipped_unresolvable: number;
  skipped_capacity: number;
  can_confirm: boolean;
  errors: FillerReserveBatchLineError[];
}

/** @deprecated Use FillerReserveBatchValidation */
export type FillerReserveImportValidation = FillerReserveBatchValidation;

@Injectable({ providedIn: 'root' })
export class FillerReserveService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  list(): Observable<FillerReserveListResponse> {
    return this.http.get<FillerReserveListResponse>(`${this.baseUrl}/filler-reserve`);
  }

  add(payload: FillerReserveAddRequest): Observable<FillerReserveEntryRead> {
    return this.http.post<FillerReserveEntryRead>(`${this.baseUrl}/filler-reserve`, payload);
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/filler-reserve/${id}`);
  }

  clearReserve(): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/filler-reserve`);
  }

  reorder(orderedIds: string[]): Observable<FillerReserveListResponse> {
    return this.http.put<FillerReserveListResponse>(`${this.baseUrl}/filler-reserve/reorder`, {
      ordered_ids: orderedIds,
    });
  }

  enqueue(id: string): Observable<QueueEntryRead> {
    return this.http.post<QueueEntryRead>(`${this.baseUrl}/filler-reserve/${id}/enqueue`, {});
  }

  enqueueBatch(ids: string[]): Observable<QueueEntryRead[]> {
    return this.http.post<QueueEntryRead[]>(`${this.baseUrl}/filler-reserve/enqueue-batch`, {
      ids,
    });
  }

  exportCsv(): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/filler-reserve/export`, {
      responseType: 'blob',
    });
  }

  validateImport(file: File): Observable<FillerReserveBatchValidation> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<FillerReserveBatchValidation>(
      `${this.baseUrl}/filler-reserve/import/validate`,
      formData,
    );
  }

  importReserve(file: File): Observable<FillerReserveListResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<FillerReserveListResponse>(
      `${this.baseUrl}/filler-reserve/import`,
      formData,
    );
  }

  validatePlaylist(url: string): Observable<FillerReserveBatchValidation> {
    return this.http.post<FillerReserveBatchValidation>(
      `${this.baseUrl}/filler-reserve/playlist/validate`,
      { youtube_playlist_url: url },
    );
  }

  addPlaylist(url: string): Observable<FillerReserveListResponse> {
    return this.http.post<FillerReserveListResponse>(
      `${this.baseUrl}/filler-reserve/playlist`,
      { youtube_playlist_url: url },
    );
  }
}

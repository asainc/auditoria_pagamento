/** Feedback supervisionado, dataset e FinOps da extração. */
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { ApiConfiguration } from './config';
import {
  DatasetSnapshot,
  FeedbackCurationInput,
  FeedbackEventRecord,
  FeedbackPage,
  FinOpsSummary,
  QualitySummary,
  ReviewCaptureResult,
  ReviewSnapshotInput,
} from './contracts';

@Injectable({providedIn:'root'})
export class QualityApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(ApiConfiguration);

  captureReview(payload: ReviewSnapshotInput) {
    return this.http.post<ReviewCaptureResult>(`${this.config.baseUrl}/qualidade/revisoes`, payload);
  }

  summary() {
    return this.http.get<QualitySummary>(`${this.config.baseUrl}/qualidade/resumo`);
  }

  feedback(page = 1, size = 25, status = 'pending', field = '') {
    let params = new HttpParams().set('pagina', page).set('tamanho', size);
    if (status) params = params.set('status', status);
    if (field.trim()) params = params.set('campo', field.trim());
    return this.http.get<FeedbackPage>(`${this.config.baseUrl}/qualidade/feedback`, {params});
  }

  curate(id: string, payload: FeedbackCurationInput) {
    return this.http.post<FeedbackEventRecord>(`${this.config.baseUrl}/qualidade/feedback/${encodeURIComponent(id)}/curadoria`, payload);
  }

  snapshotDataset() {
    return this.http.post<DatasetSnapshot>(`${this.config.baseUrl}/qualidade/datasets/snapshot`, {});
  }

  finops(days = 30) {
    const params = new HttpParams().set('dias', days);
    return this.http.get<FinOpsSummary>(`${this.config.baseUrl}/qualidade/finops`, {params});
  }
}

/** Extrações continuam no servidor mesmo quando o usuário troca de processo. */
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ApiConfiguration } from './config';
import { ExtractionResult, ExtractionStatus } from './contracts';

@Injectable({providedIn:'root'})
export class ExtractionApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(ApiConfiguration);
  start(process: string) { return this.http.post<ExtractionStatus>(`${this.config.baseUrl}/extracoes`, {numero_processo:process}); }
  status(process: string) { return this.http.get<ExtractionStatus>(`${this.config.baseUrl}/extracoes/${encodeURIComponent(process)}/status`); }
  result(process: string) { return this.http.get<ExtractionResult>(`${this.config.baseUrl}/extracoes/${encodeURIComponent(process)}/resultado`); }
}

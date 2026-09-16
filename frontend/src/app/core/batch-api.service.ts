/** Importação e execução são ações distintas e explicitamente tipadas. */
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ApiConfiguration } from './config';
import { BatchImport, BatchRequest, BatchResponse } from './contracts';

@Injectable({providedIn:'root'})
export class BatchApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(ApiConfiguration);
  import(file: File) { const data = new FormData(); data.append('file', file); return this.http.post<BatchImport>(`${this.config.baseUrl}/lotes/importar`, data); }
  execute(payload: BatchRequest) { return this.http.post<BatchResponse>(`${this.config.baseUrl}/lotes/executar`, payload); }
}

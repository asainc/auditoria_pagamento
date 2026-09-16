/** Catálogo único é consultado na API. */
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ApiConfiguration } from './config';
import { IndexOption, IndexStatus } from './contracts';

@Injectable({providedIn:'root'})
export class IndexApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(ApiConfiguration);
  options() { return this.http.get<IndexOption[]>(`${this.config.baseUrl}/indices`); }
  status() { return this.http.get<IndexStatus>(`${this.config.baseUrl}/indices/status`); }
  update() { return this.http.post<IndexStatus>(`${this.config.baseUrl}/indices/atualizar`, {}); }
}

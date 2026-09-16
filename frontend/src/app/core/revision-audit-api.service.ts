/** Trilha de revisão humana; nenhum cálculo é executado neste serviço. */
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { ApiConfiguration } from './config';
import { ParameterChangeInput, ParameterChangeRecord } from './contracts';

@Injectable({providedIn:'root'})
export class RevisionAuditApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(ApiConfiguration);

  record(payload: ParameterChangeInput) {
    return this.http.post<ParameterChangeRecord>(`${this.config.baseUrl}/auditoria/parametros`, payload);
  }

  listProcess(process: string) {
    const params = new HttpParams().set('numero_processo', process);
    return this.http.get<ParameterChangeRecord[]>(`${this.config.baseUrl}/auditoria/parametros`, {params});
  }

  listDraft(draftId: string) {
    const params = new HttpParams().set('rascunho_id', draftId);
    return this.http.get<ParameterChangeRecord[]>(`${this.config.baseUrl}/auditoria/parametros`, {params});
  }
}

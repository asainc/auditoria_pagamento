/** Serviço HTTP do domínio documental. */
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ApiConfiguration } from './config';
import { DocumentMetadata, Installment_Output, ProcessSummary, UploadResponse } from './contracts';

@Injectable({providedIn:'root'})
export class DocumentApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(ApiConfiguration);
  upload(files: File[]) { const data = new FormData(); files.forEach(file => data.append('files', file)); return this.http.post<UploadResponse>(`${this.config.baseUrl}/documentos/upload`, data); }
  processes() { return this.http.get<ProcessSummary[]>(`${this.config.baseUrl}/documentos/processos`); }
  documents(process: string) { return this.http.get<DocumentMetadata[]>(`${this.config.baseUrl}/documentos/processos/${encodeURIComponent(process)}`); }
  file(id: string) { return this.http.get(`${this.config.baseUrl}/documentos/${encodeURIComponent(id)}/arquivo`, {responseType:'blob'}); }
  importInstallments(file: File, damageType: string) { const data = new FormData(); data.append('file', file); return this.http.post<Installment_Output[]>(`${this.config.baseUrl}/documentos/parcelas/importar`, data, {params:{verba_tipo:damageType}}); }
}

/** Disponibilidade é consultada antes do upload, sem enviar a chave ao navegador. */
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { firstValueFrom, timeout } from 'rxjs';
import { ApiConfiguration } from './config';
import { ExtractionConfiguration, Health } from './contracts';
import { connectionMessage } from './api-errors';

@Injectable({providedIn:'root'})
export class ConnectionApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(ApiConfiguration);
  readonly state = signal<'checking' | 'online' | 'offline'>('checking');
  readonly message = signal('Verificando conexão com o servidor…');
  readonly extraction = signal<ExtractionConfiguration | null>(null);
  private pending: Promise<boolean> | null = null;

  check(): Promise<boolean> {
    if (this.pending) return this.pending;
    this.pending = this.probe().finally(() => { this.pending = null; });
    return this.pending;
  }

  private async probe(): Promise<boolean> {
    this.state.set('checking');
    try {
      const health = await firstValueFrom(this.http.get<Health>(`${this.config.baseUrl}/saude`).pipe(timeout(8000)));
      if (health.status !== 'ok' || health.versao_api !== '1.0.0') throw new Error('O endereço respondeu, mas não é uma API compatível com esta calculadora. Confira apiBaseUrl.');
      const extraction = await firstValueFrom(this.http.get<ExtractionConfiguration>(`${this.config.baseUrl}/extracoes/configuracao`).pipe(timeout(8000)));
      if (extraction.provedor !== 'openai' || typeof extraction.configurada !== 'boolean') throw new Error('O backend precisa ser atualizado para a mesma versão deste frontend.');
      this.extraction.set(extraction);
      this.state.set('online'); this.message.set('Conectado ao servidor');
      return true;
    } catch (error) {
      this.state.set('offline'); this.extraction.set(null);
      this.message.set(error instanceof HttpErrorResponse ? connectionMessage(error.status) : error instanceof Error && error.name !== 'TimeoutError' ? error.message : connectionMessage(0));
      return false;
    }
  }
}

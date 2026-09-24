/** A interface envia parâmetros; nenhuma matemática jurídica é executada aqui. */
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ApiConfiguration } from './config';
import {
  CalculationComparison,
  CalculationDefaults,
  CalculationExecutionsPage,
  CalculationHistoryPage,
  CalculationRequest,
  CalculationStateResult,
  CalculationVersionDetail,
  CalculationVersionsPage,
  FeePreparation,
  Installment_Output,
  VersionedCalculationResponse,
} from './contracts';

export interface CalculationHistoryFilters {
  pagina?: number;
  tamanho_pagina?: number;
  busca?: string;
  origem?: 'manual'|'processo'|'';
  estado?: 'ativo'|'arquivado'|'cancelado'|'';
  indice?: string;
  criado_por?: string;
  atualizado_de?: string;
  atualizado_ate?: string;
  ordenacao?: 'processo'|'atualizado_desc'|'atualizado_asc'|'criado_desc'|'criado_asc';
}

@Injectable({providedIn:'root'})
export class CalculationApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(ApiConfiguration);

  defaults(indice?: string) {
    const params = indice ? {indice} : undefined;
    return this.http.get<CalculationDefaults>(`${this.config.baseUrl}/calculos/padroes`, {params});
  }

  prepareFees(payload: FeePreparation) {
    return this.http.post<Installment_Output[]>(`${this.config.baseUrl}/calculos/honorarios/preparar`, payload);
  }

  calculate(
    payload: CalculationRequest,
    calculationId = '',
    baseVersion: number | null = null,
    expectedCurrentVersion: number | null = null,
  ) {
    const params: Record<string, string | number> = {};
    if (calculationId) params['calculo_id'] = calculationId;
    if (baseVersion !== null) params['versao_base'] = baseVersion;
    if (expectedCurrentVersion !== null) params['versao_atual_esperada'] = expectedCurrentVersion;
    return this.http.post<VersionedCalculationResponse>(`${this.config.baseUrl}/calculos`, payload, {params});
  }

  history(filters: CalculationHistoryFilters = {}) {
    const params: Record<string, string | number> = {};
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null && value !== '') params[key] = value;
    }
    return this.http.get<CalculationHistoryPage>(`${this.config.baseUrl}/calculos/historico`, {params});
  }

  versions(calculationId: string, page = 1, pageSize = 50) {
    return this.http.get<CalculationVersionsPage>(`${this.config.baseUrl}/calculos/${encodeURIComponent(calculationId)}/versoes`, {
      params:{pagina:page,tamanho_pagina:pageSize},
    });
  }

  compare(calculationId: string, fromVersion: number, toVersion: number) {
    return this.http.get<CalculationComparison>(`${this.config.baseUrl}/calculos/${encodeURIComponent(calculationId)}/comparar`, {
      params:{versao_origem:fromVersion,versao_destino:toVersion},
    });
  }

  changeState(calculationId: string, state: 'ativo'|'arquivado'|'cancelado') {
    return this.http.post<CalculationStateResult>(`${this.config.baseUrl}/calculos/${encodeURIComponent(calculationId)}/estado`, {estado:state});
  }

  executions(calculationId: string, version: number, page = 1, pageSize = 20) {
    return this.http.get<CalculationExecutionsPage>(`${this.config.baseUrl}/calculos/${encodeURIComponent(calculationId)}/versoes/${version}/execucoes`, {
      params:{pagina:page,tamanho_pagina:pageSize},
    });
  }

  version(calculationId: string, version: number) {
    return this.http.get<CalculationVersionDetail>(`${this.config.baseUrl}/calculos/${encodeURIComponent(calculationId)}/versoes/${version}`);
  }

  versionPdf(calculationId: string, version: number, audit = false) {
    return this.http.get(`${this.config.baseUrl}/calculos/${encodeURIComponent(calculationId)}/versoes/${version}/memoria-pdf`, {
      responseType:'blob',
      params:{auditavel:audit},
    });
  }

  executionPdf(calculationId: string, executionId: string, audit = false) {
    return this.http.get(`${this.config.baseUrl}/calculos/${encodeURIComponent(calculationId)}/execucoes/${encodeURIComponent(executionId)}/memoria-pdf`, {
      responseType:'blob',
      params:{auditavel:audit},
    });
  }

  /** Exportação do request atual sem criar nova versão; o fluxo normal usa a execução persistida. */
  pdf(payload: CalculationRequest, indicesHash = '') {
    return this.http.post(`${this.config.baseUrl}/calculos/memoria-pdf`, payload, {
      responseType:'blob',
      params:{indices_sha256:indicesHash},
    });
  }
}

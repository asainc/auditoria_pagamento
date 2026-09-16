/** A interface envia parâmetros; nenhuma matemática jurídica é executada aqui. */
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ApiConfiguration } from './config';
import { CalculationDefaults, CalculationRequest, CalculationResponse, FeePreparation, Installment_Output } from './contracts';

@Injectable({providedIn:'root'})
export class CalculationApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(ApiConfiguration);
  defaults() { return this.http.get<CalculationDefaults>(`${this.config.baseUrl}/calculos/padroes`); }
  prepareFees(payload: FeePreparation) { return this.http.post<Installment_Output[]>(`${this.config.baseUrl}/calculos/honorarios/preparar`, payload); }
  calculate(payload: CalculationRequest) { return this.http.post<CalculationResponse>(`${this.config.baseUrl}/calculos`, payload); }
  pdf(payload: CalculationRequest, audit = false, indicesHash = '') { return this.http.post(`${this.config.baseUrl}/calculos/memoria-pdf`, payload, {responseType:'blob', params:{auditavel:audit,indices_sha256:indicesHash}}); }
}

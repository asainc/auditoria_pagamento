/** Execuções técnicas paginadas e carregadas apenas quando a versão é expandida. */
import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { CalculationApiService } from '../core/calculation-api.service';
import { CalculationExecutionSummary, CalculationHistoryItem } from '../core/contracts';
import { Notifications, saveBlob } from '../core/notifications';

@Component({
  selector:'app-history-executions',
  standalone:true,
  template:`
    <section class="execution-panel">
      <div class="execution-panel-heading"><strong>Execuções técnicas da V{{ version }}</strong><small>Reexecuções sem mudança de parâmetros ou parcelas permanecem nesta versão.</small></div>
      @if (loading() && !rows().length) {
        <p class="quiet-empty">Carregando execuções…</p>
      } @else {
        @for (execution of rows(); track execution.execucao_id) {
          <div class="execution-row">
            <div><strong>{{ dateTime(execution.executada_em) }}</strong><small>{{ execution.executada_por }} · {{ execution.duracao_ms }} ms</small></div>
            <div class="execution-hashes"><small>Entrada {{ shortHash(execution.entrada_sha256) }}</small><small>Índices {{ shortHash(execution.indices_sha256) }}</small><small>Motor {{ shortHash(execution.motor_sha256) }}</small></div>
            <div class="version-actions"><button type="button" class="small-button" (click)="download(execution)">Memória</button></div>
          </div>
        } @empty {<p class="quiet-empty">Nenhuma execução técnica registrada.</p>}
        @if (page() < totalPages()) {
          <button type="button" class="small-button load-more" (click)="loadMore()" [disabled]="loading()">{{ loading() ? 'Carregando…' : 'Carregar mais execuções' }}</button>
        }
      }
    </section>
  `,
})
export class HistoryExecutionsComponent implements OnInit {
  @Input({required:true}) calculation!: CalculationHistoryItem;
  @Input({required:true}) version = 1;
  private readonly api=inject(CalculationApiService);
  private readonly notices=inject(Notifications);
  readonly rows=signal<CalculationExecutionSummary[]>([]);
  readonly loading=signal(false);
  readonly page=signal(0);
  readonly totalPages=signal(0);
  private readonly pageSize=10;

  ngOnInit(): void { void this.loadPage(1,false); }
  loadMore(): void { if(this.page()<this.totalPages()) void this.loadPage(this.page()+1,true); }
  private async loadPage(page:number,append:boolean):Promise<void>{
    if(this.loading())return;this.loading.set(true);
    try{
      const result=await firstValueFrom(this.api.executions(this.calculation.calculo_id,this.version,page,this.pageSize));
      this.rows.set(append?[...this.rows(),...result.itens]:result.itens);
      this.page.set(result.pagina);this.totalPages.set(result.total_paginas);
    }catch(error){this.notices.error(error);}finally{this.loading.set(false);}
  }
  async download(execution:CalculationExecutionSummary):Promise<void>{
    try{const content=await firstValueFrom(this.api.executionPdf(this.calculation.calculo_id,execution.execucao_id,false));const safe=this.calculation.identificador_calculo.replace(/[^A-Za-z0-9._-]+/g,'_');saveBlob(content,`execucao_${safe}_v${execution.versao}_${execution.execucao_id.slice(-8)}.pdf`);}catch(error){this.notices.error(error);}
  }
  dateTime(value:string):string{const d=new Date(value);return Number.isNaN(d.getTime())?value:new Intl.DateTimeFormat('pt-BR',{dateStyle:'short',timeStyle:'short'}).format(d);}
  shortHash(value:string):string{return value?`${value.slice(0,10)}…`:'—';}
}

/** Página orquestradora do histórico; filtros, diff, comparação e execuções são componentes independentes. */
import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { CalculationApiService, CalculationHistoryFilters } from '../core/calculation-api.service';
import { CalculationHistoryItem, CalculationVersionSummary } from '../core/contracts';
import { Notifications, saveBlob } from '../core/notifications';
import { HistoryDiffComponent } from './history-diff.component';
import { HistoryExecutionsComponent } from './history-executions.component';
import { HistoryFiltersComponent } from './history-filters.component';
import { HistoryVersionComparatorComponent } from './history-version-comparator.component';

@Component({
  selector:'app-calculation-history-page',
  standalone:true,
  imports:[HistoryDiffComponent,HistoryExecutionsComponent,HistoryFiltersComponent,HistoryVersionComparatorComponent],
  template:`
    <section class="history-page">
      <header class="history-heading">
        <div><span class="eyebrow">Rastreabilidade</span><h1>Histórico dos cálculos</h1><p>Versões representam mudanças de parâmetros ou parcelas. Reexecuções do mesmo estado ficam registradas separadamente.</p></div>
        <button type="button" class="small-button" (click)="load()" [disabled]="loading()">{{ loading() ? 'Atualizando…' : 'Atualizar histórico' }}</button>
      </header>

      <app-history-filters [loading]="loading()" (filtersApplied)="applyFilters($event)"></app-history-filters>

      <div class="history-toolbar">
        <div class="history-metrics" aria-label="Resumo do histórico"><div><span>Cálculos encontrados</span><strong>{{ totalItems() }}</strong></div><div><span>Página</span><strong>{{ page() }}@if(totalPages()){ / {{ totalPages() }}}</strong></div></div>
        <small class="history-help">Versões e execuções são carregadas somente quando necessárias.</small>
      </div>

      @if (loading() && !history().length) {
        <p class="quiet-empty">Carregando histórico dos cálculos…</p>
      } @else if (!history().length) {
        <div class="history-empty"><h2>Nenhum cálculo encontrado</h2><p>Ajuste os filtros ou conclua um novo cálculo.</p></div>
      } @else {
        <div class="history-list">
          @for(calculation of history(); track calculation.calculo_id){
            <article class="history-card" [class.history-card-muted]="calculation.estado !== 'ativo'">
              <button type="button" class="history-card-heading" (click)="toggle(calculation)" [attr.aria-expanded]="expanded(calculation.calculo_id)">
                <div class="history-process-copy"><span class="history-process-label">{{ calculation.origem_calculo === 'processo' ? 'Processo' : 'Cálculo manual' }}</span><strong>{{ calculation.identificador_calculo }}</strong><small>{{ calculation.quantidade_versoes }} {{ calculation.quantidade_versoes===1?'versão':'versões' }} · {{ calculation.quantidade_execucoes }} {{ calculation.quantidade_execucoes===1?'execução':'execuções' }}</small></div>
                <div class="history-latest"><span>Estado</span><strong class="state-badge" [class]="'state-badge state-' + calculation.estado">{{ stateLabel(calculation.estado) }}</strong></div>
                <div class="history-latest"><span>Versão atual</span><strong>V{{ calculation.versao_atual }}</strong></div>
                <div class="history-latest"><span>Total atual</span><strong>{{ money(calculation.total_atual) }}</strong></div>
                <div class="history-latest history-index"><span>Critério atual</span><strong>{{ calculation.indice_atual }}</strong><small>{{ calculation.competencia_atualizacao_atual }}</small></div>
                <span class="history-chevron" aria-hidden="true">{{ expanded(calculation.calculo_id) ? '−' : '+' }}</span>
              </button>

              @if(expanded(calculation.calculo_id)){
                <div class="history-detail-area">
                  <div class="calculation-lifecycle-row"><div><strong>Ciclo de vida</strong><small>Arquivar ou cancelar não apaga versões nem execuções.</small></div><div class="version-actions">
                    @if(calculation.estado==='ativo'){
                      <button type="button" class="small-button" (click)="changeState(calculation,'arquivado')">Arquivar</button><button type="button" class="small-button danger-lite" (click)="changeState(calculation,'cancelado')">Cancelar</button>
                    } @else {
                      <button type="button" class="small-button primary" (click)="changeState(calculation,'ativo')">Reativar</button>@if(calculation.estado==='arquivado'){<button type="button" class="small-button danger-lite" (click)="changeState(calculation,'cancelado')">Cancelar</button>}
                    }
                  </div></div>

                  @if(versionsLoading(calculation.calculo_id) && !versions(calculation.calculo_id).length){
                    <p class="quiet-empty">Carregando versões…</p>
                  } @else {
                    @if(versions(calculation.calculo_id).length>1){<app-history-version-comparator [calculationId]="calculation.calculo_id" [versions]="versions(calculation.calculo_id)"></app-history-version-comparator>}
                    <div class="history-version-list">
                      @for(version of versions(calculation.calculo_id); track version.versao){
                        <section class="version-card" [class.current-version]="version.versao===calculation.versao_atual">
                          <div class="version-heading"><div><div class="version-title-line"><strong>Versão {{ version.versao }}</strong>@if(version.versao===calculation.versao_atual){<span class="version-badge">Atual</span>}</div><small>Criada em {{ dateTime(version.criado_em) }}@if(version.versao_base){ · baseada na V{{ version.versao_base }}} · {{ version.quantidade_execucoes ?? 1 }} {{ (version.quantidade_execucoes ?? 1)===1?'execução':'execuções' }}</small></div>
                            <div class="version-actions">@if(calculation.estado==='ativo'){<button type="button" class="small-button primary" (click)="openVersion(calculation,version)">Abrir e editar</button>}<button type="button" class="small-button" (click)="toggleExecutions(calculation.calculo_id,version.versao)">{{ executionsExpanded(calculation.calculo_id,version.versao)?'Ocultar execuções':'Ver execuções' }}</button><button type="button" class="small-button" (click)="download(calculation,version)">Memória PDF</button></div>
                          </div>
                          <div class="version-summary-grid"><div><span>Total</span><strong>{{ money(version.total_geral) }}</strong></div><div><span>Índice</span><strong>{{ version.indice }}</strong></div><div><span>Atualização</span><strong>{{ version.competencia_atualizacao }}</strong></div><div><span>Última execução</span><strong>{{ version.ultima_execucao_em?dateTime(version.ultima_execucao_em):'—' }}</strong></div></div>
                          @if(version.versao===1){<p class="version-origin">Versão inicial do cálculo.</p>}
                          @if(hasDiff(version)){<details class="version-diff-details"><summary>Ver alterações completas em relação à versão base</summary><app-history-diff [diff]="version.diff!"></app-history-diff></details>}
                          @if(executionsExpanded(calculation.calculo_id,version.versao)){<app-history-executions [calculation]="calculation" [version]="version.versao"></app-history-executions>}
                        </section>
                      }
                      @if(hasMoreVersions(calculation.calculo_id)){<button type="button" class="small-button load-more" (click)="loadMoreVersions(calculation.calculo_id)" [disabled]="versionsLoading(calculation.calculo_id)">{{ versionsLoading(calculation.calculo_id)?'Carregando…':'Carregar mais versões' }}</button>}
                    </div>
                  }
                </div>
              }
            </article>
          }
        </div>
        <nav class="history-pagination" aria-label="Paginação do histórico"><button type="button" class="small-button" (click)="previousPage()" [disabled]="page()<=1 || loading()">Anterior</button><span>Página {{ page() }} de {{ totalPages() || 1 }}</span><button type="button" class="small-button" (click)="nextPage()" [disabled]="page()>=totalPages() || loading()">Próxima</button></nav>
      }
    </section>
  `,
})
export class CalculationHistoryPageComponent {
  private readonly api=inject(CalculationApiService);
  private readonly router=inject(Router);
  private readonly notices=inject(Notifications);
  readonly history=signal<CalculationHistoryItem[]>([]);
  readonly loading=signal(false);
  readonly page=signal(1);
  readonly totalItems=signal(0);
  readonly totalPages=signal(0);
  private filters:CalculationHistoryFilters={tamanho_pagina:20,ordenacao:'processo'};
  readonly expandedIds=signal<Set<string>>(new Set());
  readonly versionsByCalculation=signal<Record<string,CalculationVersionSummary[]>>({});
  readonly versionPages=signal<Record<string,{page:number,totalPages:number}>>({});
  readonly loadingVersionIds=signal<Set<string>>(new Set());
  readonly expandedExecutionKeys=signal<Set<string>>(new Set());

  constructor(){void this.load();}

  async load():Promise<void>{
    if(this.loading())return;this.loading.set(true);
    try{const result=await firstValueFrom(this.api.history({...this.filters,pagina:this.page()}));this.history.set(result.itens);this.totalItems.set(result.total_itens);this.totalPages.set(result.total_paginas);if(result.total_paginas>0&&this.page()>result.total_paginas){this.page.set(result.total_paginas);void this.load();}}
    catch(error){this.notices.error(error);}finally{this.loading.set(false);}
  }
  applyFilters(filters:CalculationHistoryFilters):void{this.filters={...filters};this.page.set(1);this.resetLazyState();void this.load();}
  previousPage():void{if(this.page()>1){this.page.update(v=>v-1);this.resetLazyState();void this.load();}}
  nextPage():void{if(this.page()<this.totalPages()){this.page.update(v=>v+1);this.resetLazyState();void this.load();}}
  private resetLazyState():void{this.expandedIds.set(new Set());this.versionsByCalculation.set({});this.versionPages.set({});this.expandedExecutionKeys.set(new Set());}
  expanded(id:string):boolean{return this.expandedIds().has(id);}
  versions(id:string):CalculationVersionSummary[]{return this.versionsByCalculation()[id]??[];}
  versionsLoading(id:string):boolean{return this.loadingVersionIds().has(id);}

  async toggle(calculation:CalculationHistoryItem):Promise<void>{const next=new Set(this.expandedIds());if(next.has(calculation.calculo_id)){next.delete(calculation.calculo_id);this.expandedIds.set(next);return;}next.add(calculation.calculo_id);this.expandedIds.set(next);if(!this.versions(calculation.calculo_id).length)await this.loadVersions(calculation.calculo_id,1,false);}
  private async loadVersions(id:string,page:number,append:boolean):Promise<void>{if(this.versionsLoading(id))return;const loading=new Set(this.loadingVersionIds());loading.add(id);this.loadingVersionIds.set(loading);try{const result=await firstValueFrom(this.api.versions(id,page,50));this.versionsByCalculation.update(values=>({...values,[id]:append?[...this.versions(id),...result.itens]:result.itens}));this.versionPages.update(values=>({...values,[id]:{page:result.pagina,totalPages:result.total_paginas}}));}catch(error){this.notices.error(error);}finally{const done=new Set(this.loadingVersionIds());done.delete(id);this.loadingVersionIds.set(done);}}
  hasMoreVersions(id:string):boolean{const state=this.versionPages()[id];return Boolean(state&&state.page<state.totalPages);}
  loadMoreVersions(id:string):void{const state=this.versionPages()[id];if(state&&state.page<state.totalPages)void this.loadVersions(id,state.page+1,true);}

  private executionKey(calculationId:string,version:number):string{return `${calculationId}:${version}`;}
  executionsExpanded(calculationId:string,version:number):boolean{return this.expandedExecutionKeys().has(this.executionKey(calculationId,version));}
  toggleExecutions(calculationId:string,version:number):void{const key=this.executionKey(calculationId,version);const values=new Set(this.expandedExecutionKeys());values.has(key)?values.delete(key):values.add(key);this.expandedExecutionKeys.set(values);}

  async changeState(calculation:CalculationHistoryItem,state:'ativo'|'arquivado'|'cancelado'):Promise<void>{if(state==='cancelado'&&!globalThis.confirm('Cancelar este cálculo? O histórico será preservado, mas novas execuções ficarão bloqueadas até uma reativação.'))return;try{await firstValueFrom(this.api.changeState(calculation.calculo_id,state));this.notices.show(`Estado alterado para ${this.stateLabel(state).toLowerCase()}.`);await this.load();}catch(error){this.notices.error(error);}}
  async openVersion(calculation:CalculationHistoryItem,version:CalculationVersionSummary):Promise<void>{await this.router.navigate(['/auditoria-pagamentos/calculo'],{queryParams:{calculo:calculation.calculo_id,versao:version.versao}});}
  async download(calculation:CalculationHistoryItem,version:CalculationVersionSummary):Promise<void>{try{const content=await firstValueFrom(this.api.versionPdf(calculation.calculo_id,version.versao,false));const prefix=calculation.origem_calculo==='processo'?'processo':'calculo_manual';const safe=calculation.identificador_calculo.replace(/[^A-Za-z0-9._-]+/g,'_');saveBlob(content,`${prefix}_${safe}_v${version.versao}.pdf`);}catch(error){this.notices.error(error);}}
  hasDiff(version:CalculationVersionSummary):boolean{return Boolean((version.diff?.campos??[]).length||(version.diff?.parcelas??[]).length);}
  stateLabel(state:string):string{return ({ativo:'Ativo',arquivado:'Arquivado',cancelado:'Cancelado'} as Record<string,string>)[state]??state;}
  money(value:string|null|undefined):string{if(value===null||value===undefined||value==='')return '—';const n=Number(value);return Number.isFinite(n)?new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(n):value;}
  dateTime(value:string):string{const d=new Date(value);return Number.isNaN(d.getTime())?value:new Intl.DateTimeFormat('pt-BR',{dateStyle:'short',timeStyle:'short'}).format(d);}
}

/** Filtros do histórico isolados da paginação e da consulta HTTP. */
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CalculationHistoryFilters } from '../core/calculation-api.service';

@Component({
  selector:'app-history-filters',
  standalone:true,
  imports:[FormsModule],
  template:`
    <section class="history-filter-panel" aria-label="Filtros do histórico">
      <div class="history-filter-grid">
        <label class="field filter-wide"><span>Processo ou identificador</span><input type="search" [(ngModel)]="search" placeholder="Número do processo ou cálculo manual" autocomplete="off"></label>
        <label class="field"><span>Origem</span><select [(ngModel)]="origin"><option value="">Todas</option><option value="processo">Processo</option><option value="manual">Manual</option></select></label>
        <label class="field"><span>Estado</span><select [(ngModel)]="state"><option value="">Todos</option><option value="ativo">Ativo</option><option value="arquivado">Arquivado</option><option value="cancelado">Cancelado</option></select></label>
        <label class="field"><span>Índice atual</span><input type="text" [(ngModel)]="index" placeholder="Ex.: IPCA-15"></label>
        <label class="field"><span>Criado por</span><input type="text" [(ngModel)]="creator" placeholder="Usuário técnico"></label>
        <label class="field"><span>Atualizado de</span><input type="date" [(ngModel)]="dateFrom"></label>
        <label class="field"><span>Atualizado até</span><input type="date" [(ngModel)]="dateTo"></label>
        <label class="field"><span>Ordenação</span><select [(ngModel)]="sort"><option value="processo">Número do processo</option><option value="atualizado_desc">Mais recentemente atualizado</option><option value="atualizado_asc">Atualização mais antiga</option><option value="criado_desc">Mais recentemente criado</option><option value="criado_asc">Criação mais antiga</option></select></label>
        <label class="field"><span>Itens por página</span><select [(ngModel)]="pageSize"><option [ngValue]="10">10</option><option [ngValue]="20">20</option><option [ngValue]="50">50</option><option [ngValue]="100">100</option></select></label>
      </div>
      <div class="history-filter-actions"><button type="button" class="small-button primary" (click)="apply()" [disabled]="loading">Aplicar filtros</button><button type="button" class="small-button" (click)="clear()" [disabled]="loading">Limpar filtros</button></div>
    </section>
  `,
})
export class HistoryFiltersComponent {
  @Input() loading=false;
  @Output() filtersApplied=new EventEmitter<CalculationHistoryFilters>();
  search=''; origin:''|'manual'|'processo'=''; state:''|'ativo'|'arquivado'|'cancelado'=''; index=''; creator=''; dateFrom=''; dateTo='';
  sort:'processo'|'atualizado_desc'|'atualizado_asc'|'criado_desc'|'criado_asc'='processo'; pageSize=20;
  apply():void{this.filtersApplied.emit({tamanho_pagina:this.pageSize,busca:this.search.trim(),origem:this.origin,estado:this.state,indice:this.index.trim(),criado_por:this.creator.trim(),atualizado_de:this.dateFrom,atualizado_ate:this.dateTo,ordenacao:this.sort});}
  clear():void{this.search='';this.origin='';this.state='';this.index='';this.creator='';this.dateFrom='';this.dateTo='';this.sort='processo';this.pageSize=20;this.apply();}
}

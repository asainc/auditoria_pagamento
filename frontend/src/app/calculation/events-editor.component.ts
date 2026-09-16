/** Eventos são enviados ao motor somente com valores e critérios revisados. */
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { WorkspaceStore } from '../core/workspace.store';
import { FinancialEvent_Input } from '../core/contracts';

@Component({selector:'app-events-editor', standalone:true, imports:[FormsModule], template:`
  <div class="panel-heading"><div><h2>Eventos financeiros</h2><p>Revise o critério de cada depósito, pagamento ou levantamento.</p></div><button type="button" (click)="add()" [disabled]="!store.canEdit()">Adicionar evento</button></div>
  <div class="tray-scroll"><div class="events-list">
    @for (event of store.active().financialEvents; track $index; let index = $index) {
      <div class="event-row"><label class="field">Tipo<select [ngModel]="event.tipo" [disabled]="!store.canEdit()" (ngModelChange)="set(index,'tipo',$event)"><option value="deposito_judicial">Depósito judicial</option><option value="pagamento_parcial">Pagamento parcial</option><option value="compensacao">Compensação</option><option value="levantamento">Levantamento</option></select></label>
        <label class="field">Data<input type="date" [ngModel]="event.data" [disabled]="!store.canEdit()" (ngModelChange)="set(index,'data',$event)"></label>
        <label class="field">Valor<input inputmode="decimal" [ngModel]="event.valor" [disabled]="!store.canEdit()" (ngModelChange)="set(index,'valor',$event)"></label>
        <label class="field">Critério<select [ngModel]="event.criterio" [disabled]="!store.canEdit()" (ngModelChange)="set(index,'criterio',$event)"><option value="informativo">Somente informativo</option><option value="descontar_no_final">Descontar no final</option><option value="abater_na_data_do_pagamento">Abater na data do pagamento</option></select></label>
        <label class="field">Índice do evento<select [ngModel]="event.indice_atualizacao ?? ''" [disabled]="!store.canEdit()" (ngModelChange)="set(index,'indice_atualizacao',$event)"><option value="">Índice geral do cálculo</option>@for (option of store.indices(); track option.chave) {<option [value]="option.chave">{{ option.nome }}</option>}</select></label>
        <button type="button" class="row-remove" (click)="remove(index)" [disabled]="!store.canEdit()" aria-label="Remover evento">×</button>
      </div>
    } @empty {<p class="quiet-empty">Nenhum evento informado. Adicione apenas eventos comprovados no processo.</p>}
  </div></div>
`})
export class EventsEditorComponent {
  readonly store = inject(WorkspaceStore);
  /** Um novo evento é informativo até a operação escolher explicitamente outro critério. */
  add(): void {this.store.update(draft => ({...draft,financialEvents:[...draft.financialEvents,{tipo:'deposito_judicial',data:null,valor:'',criterio:'informativo'}]}));}
  set<K extends keyof FinancialEvent_Input>(index: number, key: K, value: FinancialEvent_Input[K]): void {this.store.update(draft => ({...draft,financialEvents:draft.financialEvents.map((event,position) => position === index ? {...event,[key]:value} : event)}));}
  remove(index: number): void {this.store.update(draft => ({...draft,financialEvents:draft.financialEvents.filter((_,position) => position !== index)}));}
}

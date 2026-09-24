/** Edição direta de parcelas com rolagem própria, sem apagar outros tipos de verba. */
import { Component, computed, inject, model, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { WorkspaceStore } from '../core/workspace.store';
import { DocumentApiService } from '../core/document-api.service';
import { InstallmentForm } from '../core/calculation-mapper';
import { DamageType } from './parameter-fields';
import { InstallmentBatchComponent } from './installment-batch.component';

@Component({selector:'app-installment-editor', standalone:true, imports:[FormsModule,InstallmentBatchComponent], template:`
  <div class="installment-header"><div><span class="eyebrow">Valores de origem</span><h2>Parcelas</h2></div><div class="actions">
    @if (store.active().feesOnMoralDamages) {<button type="button" class="small-button" (click)="store.refreshFees()">Atualizar honorários</button>}
    <button type="button" class="small-button" (click)="batchOpen.set(true)" [disabled]="!store.canEdit()">Em lote</button>
    <label class="small-button file-button">Importar planilha<input type="file" accept=".xlsx,.xls,.csv" (change)="importFile($event)" [disabled]="!store.canEdit() || importing()"></label>
    <button type="button" class="text-button danger" (click)="clear()" [disabled]="!store.active().installments.length">Remover todas</button>
  </div></div>
  <div class="damage-tabs" role="group" aria-label="Tipo de verba em edição">
    @for (type of types; track type.key) { <button type="button" [class.active]="damageType() === type.key" [attr.aria-pressed]="damageType() === type.key" (click)="damageType.set(type.key)">{{ type.label }}</button> }
  </div>
  <div class="installment-scroll" tabindex="0" aria-label="Parcelas com rolagem própria"><table class="installment-table">
    <thead><tr><th scope="col">Item</th><th scope="col">Data</th><th scope="col">Valor original (R$)</th><th scope="col">Multiplicador</th><th scope="col">Descrição</th><th scope="col">Ação</th></tr></thead>
    <tbody>@for (row of rows(); track $index; let index = $index) {
      <tr><td class="numeric">{{ index + 1 }}</td>
        <td><input type="date" [ngModel]="row.data" (ngModelChange)="edit(index, 'data', $event)" [disabled]="!store.canEdit()" [attr.aria-label]="'Data da parcela ' + (index + 1)"></td>
        <td><input inputmode="decimal" [ngModel]="row.valor_singelo" (ngModelChange)="edit(index, 'valor_singelo', $event)" [disabled]="!store.canEdit()" placeholder="0,00" [attr.aria-label]="'Valor da parcela ' + (index + 1)"></td>
        <td>
          @if (damageType() === 'dano_material') {
            <select [ngModel]="row.multiplicador ?? ''" (ngModelChange)="editMultiplier(index, $event)" [disabled]="!store.canEdit()" [attr.aria-label]="'Multiplicador da parcela ' + (index + 1)">
              <option value="">Padrão global</option><option [ngValue]="1">1x</option><option [ngValue]="2">2x</option>
            </select>
          } @else { <span class="readonly-cell">1x</span> }
        </td>
        <td><input [ngModel]="row.descricao" (ngModelChange)="edit(index, 'descricao', $event)" [disabled]="!store.canEdit()" placeholder="Digite para adicionar" maxlength="500" [attr.aria-label]="'Descrição da parcela ' + (index + 1)"></td>
        <td><button type="button" class="row-remove" (click)="remove(index)" [disabled]="index === activeRows().length || !store.canEdit()" [attr.aria-label]="'Remover parcela ' + (index + 1)">×</button></td></tr>
    }</tbody>
  </table></div>
  <div class="table-footer">{{ activeRows().length }} parcela(s) deste tipo<span>Digite na última linha para adicionar.</span></div>
  @if (batchOpen()) {<app-installment-batch [damageType]="damageType()" (closed)="batchOpen.set(false)" (added)="add($event)"/>}
`})
export class InstallmentEditorComponent {
  readonly store = inject(WorkspaceStore);
  private readonly api = inject(DocumentApiService);
  readonly damageType = model<DamageType>('dano_material');
  readonly batchOpen = signal(false);
  readonly importing = signal(false);
  readonly types: {key:DamageType;label:string}[] = [{key:'dano_material',label:'Dano material'},{key:'dano_moral',label:'Dano moral'},{key:'honorarios',label:'Honorários'},{key:'custas',label:'Custas'}];
  readonly activeRows = computed(() => this.store.active().installments.filter(row => row.verba_tipo === this.damageType()));
  readonly rows = computed(() => [...this.activeRows(), {data:'',valor_singelo:'',descricao:'',verba_tipo:this.damageType(),multiplicador:null}]);

  /** A linha virtual vira parcela somente ao receber algum conteúdo. */
  edit(index: number, key: 'data' | 'valor_singelo' | 'descricao', value: string): void {
    const row = this.activeRows()[index];
    this.store.update(draft => ({...draft, installments:row ? draft.installments.map(item => item === row ? {...item,[key]:value} : item) : [...draft.installments,{...this.rows()[index],[key]:value}]}));
  }
  editMultiplier(index: number, value: number | string | null): void {
    const row = this.activeRows()[index];
    if (!row) return;
    const multiplier = value === 1 || value === '1' ? 1 : value === 2 || value === '2' ? 2 : null;
    this.store.update(draft => ({...draft,installments:draft.installments.map(item => item === row ? {...item,multiplicador:multiplier} : item)}));
  }
  remove(index: number): void { const row = this.activeRows()[index]; this.store.update(draft => ({...draft,installments:draft.installments.filter(item => item !== row)})); }
  clear(): void { this.store.update(draft => ({...draft,installments:[]})); }
  add(rows: InstallmentForm[]): void { this.store.update(draft => ({...draft,installments:[...draft.installments,...rows]})); }
  /** Resposta é associada ao processo capturado, nunca à seleção que mudou durante o upload. */
  async importFile(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement; const file = input.files?.[0]; input.value = '';
    if (!file) return;
    const draftKey = this.store.draftKey(); const damageType = this.damageType();
    this.importing.set(true);
    try { const rows = await firstValueFrom(this.api.importInstallments(file,damageType)); if (draftKey !== this.store.draftKey()) {this.store.notices.show('Área de trabalho alterada. Importe novamente no cálculo desejado.');return;} this.add(rows); }
    catch (error) {this.store.notices.error(error);} finally {this.importing.set(false);}
  }
}

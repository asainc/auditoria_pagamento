/** Criação de linhas recorrentes organiza datas; não implementa cálculo jurídico. */
import { Component, ElementRef, afterNextRender, input, output, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { InstallmentForm, decimalText } from '../core/calculation-mapper';
import { DamageType } from './parameter-fields';

import { recurringDate } from './installment-dates';

@Component({selector:'app-installment-batch', standalone:true, imports:[FormsModule], template:`
  <dialog #dialog (cancel)="closed.emit()" aria-labelledby="installment-batch-title">
    <form (ngSubmit)="generate()"><div class="panel-heading"><h2 id="installment-batch-title">Parcelas em lote</h2><button type="button" aria-label="Fechar" (click)="closed.emit()">×</button></div>
      <div class="dialog-content"><p>Gere as linhas e confira as datas antes de confirmar o cálculo.</p>
        @if (error()) {<p class="inline-error" role="alert">{{ error() }}</p>}
        <div class="form-grid"><label class="field">Valor de cada parcela<input name="value" [(ngModel)]="value" inputmode="decimal" required></label>
        <label class="field">Data inicial<input name="start" type="date" [(ngModel)]="start" required></label>
        <label class="field">Quantidade<input name="quantity" type="number" min="1" max="1000" [(ngModel)]="quantity" required></label>
        <label class="field">Periodicidade<select name="period" [(ngModel)]="period" required><option value="">Selecione</option><option value="mensal">Mensal</option><option value="anual">Anual</option><option value="semanal">Semanal</option><option value="diaria">Diária</option></select></label>
        <label class="field full">Descrição<input name="description" [(ngModel)]="description" maxlength="500"></label></div>
      </div><div class="dialog-actions"><button type="button" (click)="closed.emit()">Cancelar</button><button type="submit" class="primary">Adicionar parcelas</button></div>
    </form>
  </dialog>`})
export class InstallmentBatchComponent {
  readonly damageType = input.required<DamageType>();
  readonly added = output<InstallmentForm[]>();
  readonly closed = output<void>();
  readonly dialog = viewChild.required<ElementRef<HTMLDialogElement>>('dialog');
  readonly error = signal('');
  value = ''; start = ''; quantity: number | null = null; period = ''; description = '';
  constructor() { afterNextRender(() => this.dialog().nativeElement.showModal()); }
  /** A adição não substitui as linhas existentes e invalida sua revisão no componente pai. */
  generate(): void {
    try {
      const quantity = Number(this.quantity);
      if (!Number.isInteger(quantity) || quantity < 1 || quantity > 1000 || !['mensal','anual','semanal','diaria'].includes(this.period)) throw new Error('Informe quantidade entre 1 e 1.000 e uma periodicidade.');
      const value = decimalText(this.value);
      this.added.emit(Array.from({length:quantity}, (_, index) => ({data:recurringDate(this.start,index,this.period), valor_singelo:value, descricao:this.description, verba_tipo:this.damageType()})));
      this.closed.emit();
    } catch (error) {this.error.set(error instanceof Error ? error.message : 'Confira os dados.');}
  }
}

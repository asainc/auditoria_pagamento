/** Lotes mostram a prévia completa antes de solicitar confirmação e executar. */
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { BatchApiService } from '../core/batch-api.service';
import { BatchResponse, CalculationDraft } from '../core/contracts';
import { Notifications, saveBlob } from '../core/notifications';
import { PARAM_FIELDS } from '../calculation/parameter-fields';

@Component({selector:'app-batch-page', standalone:true, imports:[FormsModule], template:`
  <main class="management-page"><header class="management-heading"><div><span class="eyebrow">Operação em lote</span><h1>Vários processos, uma revisão</h1><p>Importe o arquivo, confira cada processo e execute os cálculos.</p></div><a class="button" href="modelo_lote.json" download>Baixar modelo JSON</a></header>
    <section class="management-card batch-upload"><label class="file-button button">{{ busy() ? 'Processando…' : 'Importar arquivo de lote' }}<input type="file" accept=".json,.xlsx,.xls,.csv" (change)="importFile($event)" [disabled]="busy()"></label><span>JSON, XLSX, XLS ou CSV · até 100 processos</span></section>
    @if (drafts().length) {
      <div class="batch-review-toolbar"><strong>{{ drafts().length }} processo(s) para revisar</strong><label class="checkbox"><input type="checkbox" [ngModel]="reviewed()" (ngModelChange)="reviewed.set($event)" [disabled]="busy()"><span>Revisei todos os processos deste lote</span></label><button class="primary" type="button" (click)="execute()" [disabled]="!reviewed() || busy()">Executar lote</button></div>
      @for (draft of drafts(); track draft.numero_processo) {
        <details class="management-card batch-process"><summary><strong>Processo {{ draft.numero_processo }}</strong><span>{{ draft.parcelas.length }} parcela(s)</span></summary>
          <div class="batch-process-body"><h2>Parâmetros</h2><dl class="parameter-review">@for (entry of parameters(draft); track entry.label) {<div><dt>{{ entry.label }}</dt><dd>{{ entry.value }}</dd></div>}</dl>
            <div class="table-scroll"><table><thead><tr><th>Data</th><th>Valor original</th><th>Verba</th><th>Descrição</th></tr></thead><tbody>@for (row of draft.parcelas; track $index) {<tr><td>{{ row.data }}</td><td>{{ row.valor_singelo }}</td><td>{{ label(row.verba_tipo) }}</td><td>{{ row.descricao }}</td></tr>}</tbody></table></div>
            @if (draft.eventos_financeiros?.length) {<h2>Eventos financeiros</h2><div class="table-scroll"><table><thead><tr><th>Tipo</th><th>Data</th><th>Valor</th><th>Critério</th></tr></thead><tbody>@for (event of draft.eventos_financeiros; track $index) {<tr><td>{{ label(event.tipo) }}</td><td>{{ event.data }}</td><td>{{ event.valor }}</td><td>{{ label(event.criterio) }}</td></tr>}</tbody></table></div>}
          </div>
        </details>
      }
    } @else {<div class="management-empty"><h2>Comece pelo modelo de importação</h2><p>O modelo usa valores fictícios. Substitua-os pelos dados revisados dos processos.</p></div>}
    @if (result(); as result) {<section class="management-card"><div class="panel-heading"><h2>Resultados do lote</h2><button type="button" (click)="download()">Baixar resultados JSON</button></div><div class="batch-process-body">
      @for (item of result.resultados; track $index) {<article class="batch-result"><h3>Processo {{ item.numero_processo }}</h3>@if (item.erro) {<p class="inline-error">{{ item.erro }}</p>} @else if (item.resultado; as calculation) {<dl class="result-summary">@for (row of calculation.resumo; track $index) {<div><dt>{{ label(row.campo) }}</dt><dd>{{ row.valor }}</dd></div>}</dl>}</article>}
    </div></section>}
  </main>
`})
export class BatchPageComponent {
  private readonly api = inject(BatchApiService);
  private readonly notifications = inject(Notifications);
  readonly drafts = signal<CalculationDraft[]>([]);
  readonly result = signal<BatchResponse | null>(null);
  readonly busy = signal(false);
  readonly reviewed = signal(false);

  /** Novo arquivo remove confirmação e resultados associados ao arquivo anterior. */
  async importFile(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement; const file = input.files?.[0]; input.value = ''; if (!file) return;
    this.busy.set(true); this.reviewed.set(false); this.result.set(null); this.drafts.set([]);
    try {this.drafts.set((await firstValueFrom(this.api.import(file))).processos);}
    catch (error) {this.notifications.error(error);} finally {this.busy.set(false);}
  }
  /** A confirmação pertence à revisão atual, não ao conteúdo importado. */
  async execute(): Promise<void> {
    if (!this.reviewed() || this.busy()) return;
    this.busy.set(true);
    try {this.result.set(await firstValueFrom(this.api.execute({processos:this.drafts().map(draft => ({...draft,revisao_humana_confirmada:true}))})));}
    catch (error) {this.notifications.error(error);} finally {this.busy.set(false);}
  }
  parameters(draft: CalculationDraft): {label:string;value:string}[] {return PARAM_FIELDS.filter(field => draft.parametros[field.key] !== undefined && draft.parametros[field.key] !== null).map(field => ({label:field.label,value:String(draft.parametros[field.key])}));}
  label(value: string): string {return value.replace(/_/g,' ');}
  download(): void {if (this.result()) saveBlob(new Blob([JSON.stringify(this.result(),null,2)],{type:'application/json'}),'resultados_lote.json');}
}

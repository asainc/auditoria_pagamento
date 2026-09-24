/** Resultado e memória exibem apenas valores calculados pelo backend. */
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { WorkspaceStore } from '../core/workspace.store';
import { summaryRows, finalTotal } from '../core/result-presentation';
import { ResultCalculationSummaryComponent } from './result-calculation-summary.component';

@Component({selector:'app-result-panel', standalone:true, imports:[RouterLink,ResultCalculationSummaryComponent], template:`
  <div class="panel-heading"><div><h2>Resultado do cálculo</h2>@if (store.active().result; as result) {<p>Execução medida: {{ result.metadata.duracao_ms }} ms</p>}</div>
    <div class="actions result-actions">
      <button type="button" class="small-button" (click)="store.downloadPdf()" [disabled]="!store.active().result || store.exporting()">Memória PDF</button>
      <a class="button small-button" routerLink="/auditoria-pagamentos/historico">Histórico</a>
      @if (store.active().result?.registro; as registration) {
        <div class="result-version-card" aria-label="Versão do cálculo"><span>Versão do cálculo</span><strong>V{{ registration.versao }}</strong></div>
      }
    </div>
  </div>
  <div class="tray-scroll">
    @if (store.active().result; as result) {
      <app-result-calculation-summary [result]="result" [indices]="store.indices()" />
      <div class="final-total"><span>Total final calculado</span><strong>R$ {{ total(result) }}</strong></div>
      @if (store.active().feesOnMoralDamages) {<p class="quiet-empty">Os honorários sobre danos morais já compõem as parcelas. O acréscimo global de honorários fica zerado para evitar dupla cobrança.</p>}
      <dl class="result-summary">@for (row of summary(result); track $index) {<div><dt>{{ row.campo }}</dt><dd>{{ row.valor }}</dd></div>}</dl>
      <details class="memory-details"><summary>Memória por parcela</summary><div class="memory-scroll"><table><thead><tr>@for (column of result.memoria.colunas; track column) {<th>{{ label(column) }}</th>}</tr></thead><tbody>@for (row of result.memoria.linhas; track $index) {<tr>@for (cell of row; track $index) {<td>{{ cell }}</td>}</tr>}</tbody></table></div></details>
    } @else {<p class="quiet-empty">Preencha os dados, confirme a revisão e clique em “Calcular débito”. O resultado aparecerá aqui.</p>}
  </div>
`})
export class ResultPanelComponent {
  readonly store = inject(WorkspaceStore);
  readonly summary = summaryRows;
  readonly total = finalTotal;
  label(key: string): string {return key.replace(/_/g,' ').replace(/^./,value => value.toUpperCase());}
}

/** Comparador isolado: carrega somente quando o usuário solicita a comparação. */
import { Component, Input, OnChanges, SimpleChanges, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { CalculationApiService } from '../core/calculation-api.service';
import { CalculationComparison, CalculationVersionSummary } from '../core/contracts';
import { Notifications } from '../core/notifications';
import { HistoryDiffComponent } from './history-diff.component';

@Component({
  selector:'app-history-version-comparator',
  standalone:true,
  imports:[FormsModule, HistoryDiffComponent],
  template:`
    <section class="version-comparator">
      <div><strong>Comparador de versões</strong><small>Compare parâmetros, parcelas e impacto no total.</small></div>
      <label class="field compact-field"><span>De</span><select [(ngModel)]="fromVersion">@for (version of versions; track version.versao) {<option [ngValue]="version.versao">V{{ version.versao }}</option>}</select></label>
      <label class="field compact-field"><span>Para</span><select [(ngModel)]="toVersion">@for (version of versions; track version.versao) {<option [ngValue]="version.versao">V{{ version.versao }}</option>}</select></label>
      <button type="button" class="small-button primary" (click)="compare()" [disabled]="loading() || fromVersion === toVersion">{{ loading() ? 'Comparando…' : 'Comparar' }}</button>
    </section>
    @if (comparison(); as result) {
      <section class="comparison-result">
        <div class="comparison-totals"><div><span>V{{ result.versao_origem }}</span><strong>{{ money(result.total_origem) }}</strong></div><div class="comparison-arrow">→</div><div><span>V{{ result.versao_destino }}</span><strong>{{ money(result.total_destino) }}</strong></div><div class="comparison-impact"><span>Diferença</span><strong>{{ signedMoney(result.diferenca_total) }}</strong></div></div>
        <app-history-diff [diff]="result.diff"></app-history-diff>
      </section>
    }
  `,
})
export class HistoryVersionComparatorComponent implements OnChanges {
  @Input({required:true}) calculationId = '';
  @Input({required:true}) versions: CalculationVersionSummary[] = [];
  private readonly api=inject(CalculationApiService);
  private readonly notices=inject(Notifications);
  readonly loading=signal(false);
  readonly comparison=signal<CalculationComparison|null>(null);
  fromVersion=0;
  toVersion=0;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['versions'] && this.versions.length) {
      const newest=this.versions[0].versao;
      const older=this.versions[1]?.versao ?? newest;
      if (!this.versions.some(row=>row.versao===this.fromVersion)) this.fromVersion=older;
      if (!this.versions.some(row=>row.versao===this.toVersion)) this.toVersion=newest;
      this.comparison.set(null);
    }
  }

  async compare(): Promise<void> {
    if (!this.calculationId || !this.fromVersion || !this.toVersion || this.fromVersion===this.toVersion || this.loading()) return;
    this.loading.set(true);
    try { this.comparison.set(await firstValueFrom(this.api.compare(this.calculationId,this.fromVersion,this.toVersion))); }
    catch(error) { this.notices.error(error); }
    finally { this.loading.set(false); }
  }
  money(value:string|null|undefined):string { if(value===null||value===undefined||value==='')return '—';const n=Number(value);return Number.isFinite(n)?new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(n):value; }
  signedMoney(value:string|null|undefined):string { if(value===null||value===undefined||value==='')return '—';const n=Number(value);if(!Number.isFinite(n))return value;const formatted=new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Math.abs(n));return `${n>0?'+ ':n<0?'− ':''}${formatted}`; }
}

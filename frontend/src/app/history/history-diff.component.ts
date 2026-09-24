/** Exibe diferenças entre versões sem conhecer carregamento, paginação ou estado da página. */
import { Component, Input } from '@angular/core';

import { CalculationDiff, InstallmentDiff } from '../core/contracts';
import { PARAM_FIELDS } from '../calculation/parameter-fields';

@Component({
  selector:'app-history-diff',
  standalone:true,
  template:`
    <div class="full-diff">
      @if ((diff.campos ?? []).length) {
        <div class="diff-section"><strong>Parâmetros alterados</strong><div class="diff-table">
          @for (item of diff.campos; track item.caminho) {
            <div class="diff-row"><span>{{ fieldLabel(item.caminho) }}</span><code>{{ displayValue(item.valor_anterior) }}</code><b>→</b><code>{{ displayValue(item.valor_novo) }}</code></div>
          }
        </div></div>
      }
      @if ((diff.parcelas ?? []).length) {
        <div class="diff-section"><strong>Parcelas alteradas</strong>
          @for (item of diff.parcelas; track item.posicao) {
            <div class="installment-diff">
              <div><span>Parcela {{ item.posicao }}</span><strong>{{ installmentAction(item) }}</strong></div>
              @if (item.acao === 'alterada') {
                <div class="installment-before-after"><div><span>Antes</span><small>{{ installmentTextValue(item.antes) }}</small></div><b>→</b><div><span>Depois</span><small>{{ installmentTextValue(item.depois) }}</small></div></div>
                @if ((item.campos_alterados ?? []).length) {
                  <div class="installment-field-diff">
                    @for (field of item.campos_alterados ?? []; track field) {
                      <div><span>{{ installmentFieldLabel(field) }}</span><code>{{ installmentFieldValue(item.antes, field) }}</code><b>→</b><code>{{ installmentFieldValue(item.depois, field) }}</code></div>
                    }
                  </div>
                }
              } @else {<small>{{ installmentText(item) }}</small>}
            </div>
          }
        </div>
      }
      @if (!(diff.campos ?? []).length && !(diff.parcelas ?? []).length) {<p class="version-origin">Não há diferenças de parâmetros ou parcelas.</p>}
    </div>
  `,
})
export class HistoryDiffComponent {
  @Input({required:true}) diff!: CalculationDiff;

  displayValue(value: unknown): string { if (value===null||value===undefined||value==='') return '—'; if (typeof value==='boolean') return value?'Sim':'Não'; return String(value); }
  fieldLabel(path: string): string { if (path==='parcelas') return 'Parcelas'; if (path==='honorarios_sobre_danos_morais') return 'Honorários sobre danos morais'; const key=path.replace(/^parametros\./,''); return PARAM_FIELDS.find(field=>field.key===key)?.label ?? key.replace(/_/g,' '); }
  installmentAction(item: InstallmentDiff): string { return item.acao==='adicionada'?'Adicionada':item.acao==='removida'?'Removida':'Alterada'; }
  installmentFieldLabel(field: string): string { const labels:Record<string,string>={data:'Data',valor_singelo:'Valor',descricao:'Descrição',verba_tipo:'Tipo',multiplicador:'Multiplicador',origem:'Origem'}; return labels[field]??field; }
  installmentFieldValue(row: InstallmentDiff['antes'] | InstallmentDiff['depois'], field: string): string { if (!row) return '—'; const value=(row as unknown as Record<string, unknown>)[field]; if (field==='valor_singelo' && value!==null && value!==undefined) return this.money(String(value)); return this.displayValue(value); }
  installmentText(item: InstallmentDiff): string { return this.installmentTextValue(item.depois??item.antes); }
  installmentTextValue(row: InstallmentDiff['antes'] | InstallmentDiff['depois']): string { if (!row) return '—'; return `${row.data} · ${this.money(String(row.valor_singelo))} · ${row.verba_tipo.replace(/_/g,' ')}`; }
  private money(value: string): string { const number=Number(value); return Number.isFinite(number)?new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(number):value; }
}

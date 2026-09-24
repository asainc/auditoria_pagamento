/** Resumo operacional do cálculo exibido somente na guia Resultado. */
import { Component, Input } from '@angular/core';
import { CalculationResponse, IndexOption } from '../core/contracts';
import { DamageCalculationSummary, damageCalculationSummaries } from '../core/result-presentation';

@Component({
  selector:'app-result-calculation-summary',
  standalone:true,
  template:`
    <section class="result-calculation-context" aria-label="Resumo do cálculo">
      @for (item of summaries(); track item.tipo) {
        <article class="result-damage-summary">
          <h3>{{ item.titulo }}</h3>
          <p><strong>Indexador:</strong> {{ item.indexador }}</p>
          <p><strong>Período de correção:</strong> {{ item.periodoCorrecao }}</p>
          <p><strong>Período de incidência de juros:</strong> {{ item.periodoJuros }}</p>
          <p><strong>Juros:</strong> {{ item.juros }}</p>
        </article>
      } @empty {
        <p class="quiet-empty">Não há verbas de dano material ou dano moral para resumir.</p>
      }
    </section>
  `,
})
export class ResultCalculationSummaryComponent {
  @Input({required:true}) result!: CalculationResponse;
  @Input() indices: IndexOption[] = [];
  summaries(): DamageCalculationSummary[] { return damageCalculationSummaries(this.result,this.indices); }
}

/** Log visual reúne a origem automática e a trilha imutável de revisão humana. */
import { Component, computed, inject } from '@angular/core';
import { WorkspaceStore } from '../core/workspace.store';
import { PARAM_FIELDS, ParameterKey } from './parameter-fields';

interface ExtractionLogRow {
  key: ParameterKey;
  parameter: string;
  source: string;
  extractedAt: string;
  extractedValue: string;
  humanValue: string;
  changed: boolean;
}

interface RevisionLogRow {
  id: number;
  parameter: string;
  recordedAt: string;
  previousValue: string;
  newValue: string;
  extractedValue: string;
  source: string;
  actor: string;
}

@Component({selector:'app-extraction-log', standalone:true, template:`
  <div class="panel-heading"><div><h2>Logs de extração e revisão</h2><p>Rastreabilidade dos parâmetros sugeridos automaticamente e das alterações realizadas na conferência humana.</p></div></div>
  <div class="tray-scroll log-list">
    @if (usage()) {
      <section class="usage-summary" aria-label="Telemetria da extração corporativa">
        <div><span>Modelos/serviços</span><strong>{{ usage()!.modelo }}</strong></div>
        <div><span>Chamadas</span><strong>{{ usage()!.chamadas }}</strong></div>
        <div><span>Duração acumulada</span><strong>{{ duration(usage()!.duracao_total_ms) }}</strong></div>
        <div><span>Tokens</span><strong>{{ usage()!.tokens_total == null ? 'Não disponibilizado' : number(usage()!.tokens_total!) }}</strong></div>
        <div><span>Custo</span><strong>{{ usage()!.custo_estimado_usd == null ? 'Não disponibilizado' : cost(usage()!.custo_estimado_usd) }}</strong></div>
      </section>
      <p class="log-note">A aplicação exibe somente métricas retornadas ou observadas. O contrato corporativo atual não fornece contagem de tokens nem cobrança, portanto esses valores não são estimados.</p>
    }

    @if (rows().length) {
      <div class="log-table-scroll">
        <table class="log-table">
          <thead><tr><th>Parâmetro</th><th>Origem</th><th>Data e hora da extração</th><th>Valor extraído</th><th>Valor atual</th></tr></thead>
          <tbody>
            @for (row of rows(); track row.key + row.source + row.extractedValue) {
              <tr [class.human-changed]="row.changed">
                <td><strong>{{ row.parameter }}</strong></td>
                <td>{{ row.source }}</td>
                <td>{{ row.extractedAt }}</td>
                <td class="log-value">{{ row.extractedValue }}</td>
                <td class="log-value">{{ row.humanValue }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <p class="log-note"><strong>Linha destacada:</strong> o valor atual diverge do valor sugerido pela extração ou pela regra operacional.</p>
    } @else {
      <p class="quiet-empty">Nenhum parâmetro extraído está disponível para este processo.</p>
    }

    @if (revisionRows().length) {
      <div class="panel-heading log-history-heading"><div><h2>Histórico de alterações humanas</h2><p>Cada linha representa um evento persistido; alterações anteriores não são sobrescritas.</p></div></div>
      <div class="log-table-scroll">
        <table class="log-table review-log-table">
          <thead><tr><th>Parâmetro</th><th>Data e hora</th><th>Valor anterior</th><th>Novo valor</th><th>Valor automático</th><th>Origem automática</th><th>Responsável técnico</th></tr></thead>
          <tbody>
            @for (row of revisionRows(); track row.id) {
              <tr>
                <td><strong>{{ row.parameter }}</strong></td>
                <td>{{ row.recordedAt }}</td>
                <td class="log-value">{{ row.previousValue }}</td>
                <td class="log-value">{{ row.newValue }}</td>
                <td class="log-value">{{ row.extractedValue }}</td>
                <td>{{ row.source }}</td>
                <td>{{ row.actor }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
  </div>
`})
export class ExtractionLogComponent {
  readonly store = inject(WorkspaceStore);

  readonly usage = computed(() => {
    const usage = this.store.active().extraction?.uso_ia;
    if (!usage) return null;
    const models = [...new Set((usage.detalhamento ?? []).map(item => item.modelo).filter(Boolean))];
    return {...usage, modelo:models.length ? models.join(' · ') : 'Não informado'};
  });

  readonly rows = computed<ExtractionLogRow[]>(() => {
    const draft = this.store.active();
    const extraction = draft.extraction;
    if (!extraction) return [];
    const extractedAt = this.formatDate(draft.appliedExtractionAt);
    const rows: ExtractionLogRow[] = [];

    for (const field of PARAM_FIELDS) {
      const path = `parametros.${field.key}`;
      const consolidated = extraction.parametros_consolidados?.[field.key];
      const decision = extraction.decisoes_cronologicas?.find(item => item.campo === path);
      if (consolidated !== undefined && consolidated !== null && decision) {
        rows.push(this.row(field.key, field.label, `${decision.documento} · página ${decision.pagina} · sequência ${decision.sequencia}`, extractedAt, consolidated));
      } else {
        const evidences = extraction.campos.filter(item => item.campo === path && item.escopo === 'caso_concreto' && item.valor !== null);
        for (const evidence of evidences) rows.push(this.row(field.key, field.label, `${evidence.documento} · página ${evidence.pagina}`, extractedAt, evidence.valor));
      }
      for (const adjustment of extraction.ajustes_operacionais ?? []) {
        if (adjustment.campo === path) rows.push(this.row(field.key, field.label, `Regra operacional · ${adjustment.motivo}`, extractedAt, adjustment.valor));
      }
    }
    return rows;
  });

  readonly revisionRows = computed<RevisionLogRow[]>(() => this.store.parameterChanges().map(change => ({
    id:change.identificador,
    parameter:PARAM_FIELDS.find(field => field.key === change.campo)?.label ?? change.campo,
    recordedAt:this.formatDate(change.registrado_em),
    previousValue:this.display(change.valor_anterior),
    newValue:this.display(change.valor_novo),
    extractedValue:this.display(change.valor_extraido),
    source:change.origem_extraida ?? 'Não disponível',
    actor:change.ator_tecnico,
  })));

  private row(key: ParameterKey, parameter: string, source: string, extractedAt: string, extracted: unknown): ExtractionLogRow {
    const current = this.store.active().parameters[key];
    const extractedValue = this.display(extracted);
    const currentValue = current === undefined || current === null || current === '' ? 'Não informado' : this.display(current);
    return {key, parameter, source, extractedAt, extractedValue, humanValue:currentValue, changed:currentValue !== extractedValue};
  }

  private display(value: unknown): string {
    if (value === true) return 'Sim';
    if (value === false) return 'Não';
    if (value === null || value === undefined || value === '') return 'Não informado';
    return String(value);
  }

  number(value: number): string {
    return new Intl.NumberFormat('pt-BR').format(value);
  }

  duration(value: number | null | undefined): string {
    if (value === null || value === undefined) return 'Não disponível';
    if (value < 1000) return `${Math.round(value)} ms`;
    return `${(value / 1000).toFixed(1).replace('.', ',')} s`;
  }

  cost(value: string | null | undefined): string {
    if (value === null || value === undefined || value === '') return 'Não calculado';
    const numeric = Number(value);
    return Number.isFinite(numeric) ? new Intl.NumberFormat('pt-BR', {style:'currency', currency:'USD', minimumFractionDigits:4, maximumFractionDigits:6}).format(numeric) : 'Não calculado';
  }

  private formatDate(value: string): string {
    if (!value) return 'Não disponível';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat('pt-BR', {dateStyle:'short', timeStyle:'medium'}).format(date);
  }
}

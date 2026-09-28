/** Painel operacional de qualidade supervisionada e FinOps, sem expor documento bruto. */
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { FeedbackEventRecord, FinOpsSummary, QualitySummary } from '../core/contracts';
type FeedbackReasonCode = FeedbackEventRecord['motivo_codigo'];
import { Notifications } from '../core/notifications';
import { QualityApiService } from '../core/quality-api.service';

@Component({
  selector: 'app-quality-page',
  standalone: true,
  imports: [FormsModule],
  template: `
    <main class="quality-page">
      <header class="quality-heading">
        <div><span class="eyebrow">Melhoria contínua</span><h1>Qualidade da extração</h1></div>
        <button type="button" class="small-button" (click)="createDataset()" [disabled]="loading()">Congelar dataset aprovado</button>
      </header>
      <p class="quality-intro">A revisão humana é registrada separadamente da predição original. Somente exemplos aprovados entram no conjunto reutilizável de aprendizado.</p>

      @if (summary(); as data) {
        <section class="quality-cards" aria-label="Resumo da qualidade">
          <article><small>Campos revisados</small><strong>{{ data.total_eventos }}</strong></article>
          <article><small>Confirmados</small><strong>{{ data.confirmados }}</strong></article>
          <article><small>Corrigidos/removidos/adicionados</small><strong>{{ data.corrigidos + data.removidos + data.adicionados }}</strong></article>
          <article><small>Taxa de intervenção humana</small><strong>{{ percent(data.taxa_intervencao) }}</strong></article>
          <article><small>Pendentes de curadoria</small><strong>{{ data.pendentes_curadoria }}</strong></article>
        </section>

        <section class="quality-panel">
          <h2>Campos com maior intervenção</h2>
          <div class="quality-table-wrap">
            <table class="quality-table">
              <thead><tr><th>Campo</th><th>Revisões</th><th>Correções</th><th>Taxa</th></tr></thead>
              <tbody>
                @for (row of data.por_campo ?? []; track row.campo) {
                  <tr><td>{{ row.campo }}</td><td>{{ row.total }}</td><td>{{ row.corrigidos + row.removidos + row.adicionados }}</td><td>{{ percent(row.taxa_intervencao) }}</td></tr>
                }
              </tbody>
            </table>
          </div>
        </section>
      }

      @if (finops(); as usage) {
        <section class="quality-panel">
          <div class="quality-panel-heading">
            <div><h2>FinOps da IA</h2><p>Período de {{ usage.periodo_dias }} dias. Tokens estimados são indicadores locais, não faturamento.</p></div>
            <select aria-label="Período FinOps" [ngModel]="days()" (ngModelChange)="changeDays($event)"><option [ngValue]="7">7 dias</option><option [ngValue]="30">30 dias</option><option [ngValue]="90">90 dias</option></select>
          </div>
          <div class="quality-cards finops-cards">
            <article><small>Chamadas à API</small><strong>{{ usage.chamadas_api }}</strong></article>
            <article><small>Falhas de API</small><strong>{{ usage.falhas_api ?? 0 }}</strong></article>
            <article><small>Reaproveitadas do cache</small><strong>{{ usage.acertos_cache }}</strong></article>
            <article><small>Taxa de cache</small><strong>{{ percent(usage.taxa_cache) }}</strong></article>
            <article><small>Tokens reais</small><strong>{{ usage.tokens_reais ?? 'Não fornecidos' }}</strong></article>
            <article><small>Tokens estimados</small><strong>{{ usage.tokens_estimados }}</strong></article>
            <article><small>Custo estimado</small><strong>{{ usage.custo_estimado_usd ? ('$ ' + usage.custo_estimado_usd) : 'Tarifa não configurada' }}</strong></article>
          </div>
          <p class="quality-note">Origem dos tokens: {{ tokenOrigin(usage.origem_tokens) }}. Caracteres enviados: {{ usage.caracteres_entrada }}. O cache evitou {{ usage.economia_chamadas_cache }} chamada(s) idêntica(s).</p>
          @if (usage.orcamento_mensal_usd) {
            <div class="finops-budget" [attr.data-status]="usage.status_orcamento">
              <strong>Orçamento mensal: $ {{ usage.orcamento_mensal_usd }}</strong>
              <span>{{ budgetLabel(usage) }}</span>
            </div>
          }
          <div class="quality-table-wrap">
            <table class="quality-table">
              <thead><tr><th>Etapa</th><th>API</th><th>Falhas</th><th>Cache</th><th>Caracteres entrada</th><th>Tokens estimados</th></tr></thead>
              <tbody>@for (row of usage.por_etapa ?? []; track row.etapa) {<tr><td>{{ row.etapa }}</td><td>{{ row.chamadas_api }}</td><td>{{ row.falhas_api ?? 0 }}</td><td>{{ row.acertos_cache }}</td><td>{{ row.caracteres_entrada }}</td><td>{{ row.tokens_estimados }}</td></tr>}</tbody>
            </table>
          </div>
        </section>
      }

      <section class="quality-panel">
        <div class="quality-panel-heading"><div><h2>Curadoria de correções</h2><p>Uma correção humana não vira ground truth automaticamente.</p></div><button type="button" class="text-button" (click)="loadAll()">Atualizar</button></div>
        @if (!feedback().length) {<p class="quality-empty">Não há correções pendentes de curadoria.</p>}
        @for (row of feedback(); track row.identificador) {
          <article class="feedback-card">
            <div class="feedback-card-main">
              <strong>{{ row.campo }}</strong><span>{{ actionLabel(row.acao) }}</span>
              <div class="feedback-values"><div><small>IA</small><b>{{ value(row.valor_modelo) }}</b></div><div class="feedback-arrow">→</div><div><small>Humano</small><b>{{ value(row.valor_humano) }}</b></div></div>
              @if (row.evidencia_modelo) {<blockquote>{{ row.evidencia_modelo }}</blockquote>}
              @if (row.documento) {<small>{{ row.documento }}{{ row.pagina ? ' · página ' + row.pagina : '' }}</small>}
            </div>
            <div class="feedback-curation">
              <label>Motivo
                <select [(ngModel)]="reasonById[row.identificador]">
                  @for (reason of reasons; track reason.value) {<option [value]="reason.value">{{ reason.label }}</option>}
                </select>
              </label>
              <button type="button" class="small-button primary" (click)="curate(row, 'approved')">Aprovar exemplo</button>
              <button type="button" class="text-button danger" (click)="curate(row, 'rejected')">Rejeitar</button>
            </div>
          </article>
        }
      </section>
    </main>
  `,
})
export class QualityPageComponent implements OnInit {
  private readonly api = inject(QualityApiService);
  private readonly notices = inject(Notifications);
  readonly summary = signal<QualitySummary|null>(null);
  readonly finops = signal<FinOpsSummary|null>(null);
  readonly feedback = signal<FeedbackEventRecord[]>([]);
  readonly loading = signal(false);
  readonly days = signal(30);
  readonly reasonById: Record<string, FeedbackReasonCode> = {};
  readonly reasons: {value: FeedbackReasonCode; label: string}[] = [
    {value:'decisao_posterior_prevalece',label:'Decisão posterior prevalece'},
    {value:'documento_incorreto',label:'Documento incorreto'},
    {value:'pagina_incorreta',label:'Página incorreta'},
    {value:'valor_interpretado_incorretamente',label:'Valor interpretado incorretamente'},
    {value:'data_interpretada_incorretamente',label:'Data interpretada incorretamente'},
    {value:'regra_nao_se_aplica',label:'Regra não se aplica'},
    {value:'campo_ausente_no_documento',label:'Campo ausente no documento'},
    {value:'contrato_incorreto',label:'Contrato incorreto'},
    {value:'parcela_associada_ao_contrato_errado',label:'Parcela associada ao contrato errado'},
    {value:'classificacao_documento_incorreta',label:'Classificação documental incorreta'},
    {value:'ambiguidade_documental',label:'Ambiguidade documental'},
    {value:'adicao_manual',label:'Adição manual'},
    {value:'outro',label:'Outro'},
    {value:'nao_informado',label:'Ainda não classificado'},
    {value:'confirmado_sem_alteracao',label:'Confirmado sem alteração'},
  ];

  ngOnInit(): void { void this.loadAll(); }

  async loadAll(): Promise<void> {
    if (this.loading()) return;
    this.loading.set(true);
    try {
      const [summary, feedback, finops] = await Promise.all([
        firstValueFrom(this.api.summary()), firstValueFrom(this.api.feedback()), firstValueFrom(this.api.finops(this.days())),
      ]);
      this.summary.set(summary); this.feedback.set(feedback.itens); this.finops.set(finops);
      for (const row of feedback.itens) this.reasonById[row.identificador] = row.motivo_codigo;
    } catch (error) { this.notices.error(error); }
    finally { this.loading.set(false); }
  }

  async changeDays(value: number): Promise<void> {
    this.days.set(Number(value));
    try { this.finops.set(await firstValueFrom(this.api.finops(this.days()))); }
    catch (error) { this.notices.error(error); }
  }

  async curate(row: FeedbackEventRecord, status: 'approved'|'rejected'): Promise<void> {
    try {
      await firstValueFrom(this.api.curate(row.identificador, {status, motivo_codigo:this.reasonById[row.identificador] ?? row.motivo_codigo}));
      this.feedback.update(values => values.filter(item => item.identificador !== row.identificador));
      this.summary.set(await firstValueFrom(this.api.summary()));
    } catch (error) { this.notices.error(error); }
  }

  async createDataset(): Promise<void> {
    try {
      const result = await firstValueFrom(this.api.snapshotDataset());
      this.notices.show(`Dataset ${result.identificador} congelado com ${result.quantidade_exemplos} exemplo(s) aprovado(s).`);
    } catch (error) { this.notices.error(error); }
  }

  percent(value: string): string { return `${(Number(value || 0) * 100).toFixed(1).replace('.', ',')}%`; }
  value(value: unknown): string { return value === null || value === undefined || value === '' ? 'Não informado' : String(value); }
  actionLabel(action: string): string { return ({corrected:'Corrigido',removed:'Removido',added:'Adicionado',ambiguous:'Ambíguo',not_found:'Não encontrado',confirmed:'Confirmado'} as Record<string,string>)[action] ?? action; }
  tokenOrigin(value: string): string { return ({gateway:'contadores reais do gateway',estimativa_local:'estimativa local por caracteres',mista:'mista (gateway + estimativa)',cache:'somente cache local',indisponivel:'sem dados'} as Record<string,string>)[value] ?? value; }
  budgetLabel(usage: FinOpsSummary): string {
    if (usage.status_orcamento === 'unavailable') return 'Consumo indisponível: faltam tarifas ou telemetria completa; o sistema não assume custo zero.';
    if (!usage.consumo_mes_estimado_usd) return 'Nenhum custo mensal calculável foi registrado.';
    const ratio = usage.percentual_orcamento ? this.percent(usage.percentual_orcamento) : '—';
    const status = ({ok:'dentro do orçamento',warning:'faixa de alerta',exceeded:'orçamento atingido',not_configured:'não configurado'} as Record<string,string>)[usage.status_orcamento ?? 'not_configured'] ?? usage.status_orcamento;
    return `Consumo estimado do mês: $ ${usage.consumo_mes_estimado_usd} (${ratio}) · ${status}.`;
  }
}

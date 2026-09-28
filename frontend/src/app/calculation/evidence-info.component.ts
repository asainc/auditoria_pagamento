/** Exibe a origem documental e as considerações de extração sem ocupar uma aba própria. */
import { Component, computed, inject, input, signal } from '@angular/core';
import { WorkspaceStore } from '../core/workspace.store';
import { CalculationParameters_Input, ChronologyDecision, FieldEvidence, OperationalAdjustment } from '../core/contracts';

@Component({
  selector: 'app-evidence-info',
  standalone: true,
  template: `
    @if (visible()) {
      <div class="evidence-info-control" [class.align-left]="align() === 'left'">
        <button
          type="button"
          class="evidence-info-trigger"
          [attr.aria-label]="label()"
          [attr.aria-expanded]="open()"
          (click)="toggle($event)"
        >i</button>

        @if (open()) {
          <div class="evidence-info-popover" role="dialog" [attr.aria-label]="label()" (click)="$event.stopPropagation()">
            <div class="evidence-info-heading">
              <div>
                <strong>Origem e considerações</strong>
                <small>Informações usadas na conferência deste dado.</small>
              </div>
              <button type="button" class="evidence-info-close" aria-label="Fechar informações" (click)="open.set(false)">×</button>
            </div>

            @if (includeAlerts() && alerts().length) {
              <div class="evidence-info-section">
                <strong>Considerações da extração</strong>
                @for (alert of alerts(); track $index) {
                  <p class="evidence-info-alert">{{ alert }}</p>
                }
              </div>
            }

            @for (adjustment of adjustments(); track $index) {
              <div class="evidence-info-section operational">
                <strong>Regra operacional aplicada</strong>
                <p>{{ adjustment.motivo }}</p>
                <div class="evidence-info-values">
                  <span>Valor aplicado</span>
                  <b>{{ formatValue(adjustment.valor) }}</b>
                </div>
              </div>
            }

            @for (decision of decisions(); track $index) {
              <div class="evidence-info-section">
                <strong>Consideração documental</strong>
                <p>{{ decision.motivo }}</p>
                <div class="evidence-info-values">
                  <span>Valor considerado</span>
                  <b>{{ formatValue(decision.valor) }}</b>
                </div>
                <button type="button" class="evidence-source-link" (click)="showSource(decision.documento, decision.pagina, decision.motivo)">
                  {{ decision.documento }} · página {{ decision.pagina }} · abrir no documento
                </button>
              </div>
            }

            @for (field of evidences(); track $index) {
              <div class="evidence-info-section">
                <div class="evidence-info-values">
                  <span>Extraído</span>
                  <b>{{ formatValue(field.valor) }}</b>
                </div>
                @if (currentValue(field.campo); as current) {
                  <div class="evidence-info-values">
                    <span>Valor atual</span>
                    <b>{{ current }}</b>
                  </div>
                }
                <blockquote>{{ field.trecho }}</blockquote>
                <button type="button" class="evidence-source-link" (click)="showSource(field.documento, field.pagina, field.trecho)">
                  {{ field.documento }} · página {{ field.pagina }} · abrir no documento
                </button>
              </div>
            }

            @if (!hasContext()) {
              <p class="evidence-info-empty">Não há evidência documental ou consideração específica vinculada a este dado.</p>
            }
          </div>
        }
      </div>
    }
  `,
})
export class EvidenceInfoComponent {
  readonly store = inject(WorkspaceStore);
  readonly paths = input<string[]>([]);
  readonly includeAlerts = input(false);
  readonly showWhenEmpty = input(false);
  readonly label = input('Ver origem e considerações');
  readonly align = input<'left' | 'right'>('right');
  readonly open = signal(false);

  private readonly pathSet = computed(() => new Set(this.paths()));
  readonly alerts = computed(() => this.store.active().extraction?.alertas ?? []);
  readonly evidences = computed<FieldEvidence[]>(() => {
    const result = this.store.active().extraction;
    const paths = this.pathSet();
    if (!result || !paths.size) return [];
    return result.campos.filter(field => paths.has(field.campo));
  });
  readonly decisions = computed<ChronologyDecision[]>(() => {
    const result = this.store.active().extraction;
    const paths = this.pathSet();
    if (!result || !paths.size) return [];
    return (result.decisoes_cronologicas ?? []).filter(decision => paths.has(decision.campo));
  });
  readonly adjustments = computed<OperationalAdjustment[]>(() => {
    const result = this.store.active().extraction;
    const paths = this.pathSet();
    if (!result || !paths.size) return [];
    return (result.ajustes_operacionais ?? []).filter(adjustment => paths.has(adjustment.campo));
  });
  readonly hasContext = computed(() =>
    this.evidences().length > 0
    || this.decisions().length > 0
    || this.adjustments().length > 0
    || (this.includeAlerts() && this.alerts().length > 0),
  );
  readonly visible = computed(() => this.hasContext() || this.showWhenEmpty());

  toggle(event: Event): void {
    event.stopPropagation();
    this.open.update(value => !value);
  }

  /** Retorna o valor revisado correspondente à evidência, quando ainda existir no rascunho. */
  currentValue(path: string): string {
    if (path.startsWith('parametros_por_dano.')) {
      const match = /^parametros_por_dano\.(dano_material|dano_moral)\.(.+)$/.exec(path);
      if (match) {
        const damage = match[1] as 'dano_material'|'dano_moral';
        const key = match[2] as keyof CalculationParameters_Input;
        return this.formatValue(this.store.active().damageParameters[damage][key]);
      }
    }
    if (path.startsWith('parametros.')) {
      const key = path.slice('parametros.'.length) as keyof CalculationParameters_Input;
      return this.formatValue(this.store.active().parameters[key]);
    }
    const match = /^parcelas\.(\d+)\.(data|valor_singelo|descricao|verba_tipo|multiplicador)$/.exec(path);
    if (!match) return '';
    const row = this.store.active().installments[Number(match[1])];
    if (!row) return '';
    const key = match[2] as 'data' | 'valor_singelo' | 'descricao' | 'verba_tipo' | 'multiplicador';
    return this.formatValue(row[key]);
  }

  formatValue(value: unknown): string {
    if (value === null || value === undefined || value === '') return 'Não informado';
    if (value === true) return 'Sim';
    if (value === false) return 'Não';
    return String(value);
  }

  /** Navega no visualizador existente e preserva o trecho como destaque para auditoria. */
  showSource(documentName: string, page: number, highlight: string): void {
    const document = this.store.documents().find(item => item.nome === documentName);
    if (!document) return;
    this.store.selectedDocument.set(document.identificador);
    this.store.pdfPage.set(page);
    this.store.pdfHighlight.set(highlight);
    this.open.set(false);
  }
}

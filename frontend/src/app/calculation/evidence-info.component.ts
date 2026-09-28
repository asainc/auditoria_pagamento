/** Exibe a origem documental e as considerações de extração sem ocupar uma aba própria. */
import { Component, ElementRef, HostListener, ViewChild, computed, inject, input, signal } from '@angular/core';
import { WorkspaceStore } from '../core/workspace.store';
import { CalculationParameters_Input, ChronologyDecision, FieldEvidence, OperationalAdjustment } from '../core/contracts';

@Component({
  selector: 'app-evidence-info',
  standalone: true,
  template: `
    @if (visible()) {
      <div class="evidence-info-control">
        <button
          #trigger
          type="button"
          class="evidence-info-trigger"
          [attr.aria-label]="label()"
          [attr.aria-expanded]="open()"
          (click)="toggle($event)"
        >i</button>

        <div
          #popover
          popover="auto"
          class="evidence-info-popover"
          [class.place-above]="popoverPosition().placeAbove"
          [style.left.px]="popoverPosition().left"
          [style.top.px]="popoverPosition().top"
          [style.width.px]="popoverPosition().width"
          [style.max-height.px]="popoverPosition().maxHeight"
          role="dialog"
          [attr.aria-label]="label()"
          (toggle)="syncOpenState($event)"
          (click)="$event.stopPropagation()"
        >
            <div class="evidence-info-heading">
              <div>
                <strong>Origem e considerações</strong>
                <small>Informações usadas na conferência deste dado.</small>
              </div>
              <button type="button" class="evidence-info-close" aria-label="Fechar informações" (click)="close()">×</button>
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
      </div>
    }
  `,
})
export class EvidenceInfoComponent {
  readonly store = inject(WorkspaceStore);

  /**
   * Referências aos dois elementos visuais usados para posicionar o balão.
   * O botão informa onde o balão deve nascer; o próprio balão é aberto na
   * camada superior do navegador, fora dos limites do painel e do PDF.
   */
  @ViewChild('trigger') private triggerElement?: ElementRef<HTMLButtonElement>;
  @ViewChild('popover') private popoverElement?: ElementRef<HTMLElement>;
  readonly paths = input<string[]>([]);
  readonly includeAlerts = input(false);
  readonly showWhenEmpty = input(false);
  readonly label = input('Ver origem e considerações');
  readonly align = input<'left' | 'right'>('right');
  readonly open = signal(false);

  /**
   * Coordenadas calculadas no momento em que o usuário abre o balão.
   * Todas as medidas são em pixels relativos à janela do navegador.
   * Isso impede que o conteúdo seja cortado pelo painel lateral ou pelo iframe do PDF.
   */
  readonly popoverPosition = signal({
    left: 12,
    top: 12,
    width: 350,
    maxHeight: 360,
    placeAbove: false,
  });

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

  /**
   * Abre ou fecha o balão de evidências.
   *
   * Entrada:
   * - event: clique no botão de informação.
   *
   * Saída:
   * - nenhuma. O método apenas altera o estado visual do componente.
   *
   * O atributo HTML `popover="auto"` coloca o balão na camada superior do
   * navegador. Dessa forma ele não fica preso ao `overflow` do painel direito
   * e um novo balão fecha automaticamente o anterior, evitando sobreposição.
   */
  toggle(event: Event): void {
    event.stopPropagation();
    const popover = this.popoverElement?.nativeElement;
    if (!popover) return;

    if (popover.matches(':popover-open')) {
      popover.hidePopover();
      return;
    }

    this.updatePopoverPosition();
    popover.showPopover();
  }

  /** Fecha o balão atual sem alterar os dados da conferência. */
  close(): void {
    const popover = this.popoverElement?.nativeElement;
    if (popover?.matches(':popover-open')) popover.hidePopover();
    this.open.set(false);
  }

  /**
   * Mantém `aria-expanded` sincronizado inclusive quando o navegador fecha o
   * balão por clique fora dele ou pela tecla Escape.
   */
  syncOpenState(event: Event): void {
    const element = event.currentTarget as HTMLElement | null;
    this.open.set(element?.matches(':popover-open') ?? false);
  }

  /**
   * Recalcula a posição caso a janela mude de tamanho enquanto o balão estiver aberto.
   * Isso evita que o conteúdo fique parcialmente fora da tela após zoom ou resize.
   */
  @HostListener('window:resize')
  onViewportResize(): void {
    if (this.open()) this.updatePopoverPosition();
  }

  /**
   * Calcula uma posição que sempre respeita as bordas visíveis da janela.
   * O balão tenta abrir abaixo do ícone; quando não há espaço suficiente, abre acima.
   */
  private updatePopoverPosition(): void {
    const trigger = this.triggerElement?.nativeElement;
    if (!trigger) return;

    const rect = trigger.getBoundingClientRect();
    const viewportWidth = document.documentElement.clientWidth;
    const viewportHeight = document.documentElement.clientHeight;
    const margin = 12;
    const gap = 8;
    const preferredWidth = viewportWidth <= 780 ? 310 : 350;
    const width = Math.max(220, Math.min(preferredWidth, viewportWidth - (margin * 2)));

    const availableBelow = Math.max(0, viewportHeight - rect.bottom - margin - gap);
    const availableAbove = Math.max(0, rect.top - margin - gap);
    const placeAbove = availableBelow < 220 && availableAbove > availableBelow;
    const availableHeight = placeAbove ? availableAbove : availableBelow;
    const maxHeight = Math.max(96, Math.min(360, availableHeight));

    const desiredLeft = this.align() === 'left' ? rect.left : rect.right - width;
    const maximumLeft = Math.max(margin, viewportWidth - width - margin);
    const left = Math.min(Math.max(desiredLeft, margin), maximumLeft);
    const top = placeAbove ? rect.top - gap : rect.bottom + gap;

    this.popoverPosition.set({left, top, width, maxHeight, placeAbove});
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
    this.close();
  }
}

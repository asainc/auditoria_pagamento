/** Organiza os critérios por tipo de dano e mantém parcelas no primeiro bloco. */
import { Component, computed, inject, model } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { WorkspaceStore } from '../core/workspace.store';
import { EvidenceInfoComponent } from './evidence-info.component';
import { InstallmentEditorComponent } from './installment-editor.component';
import { DamageType, PARAM_FIELDS, ParamField, ParameterKey, SelectOption } from './parameter-fields';

@Component({
  selector: 'app-parameter-panel',
  standalone: true,
  imports: [FormsModule, InstallmentEditorComponent, EvidenceInfoComponent],
  template: `
    <div class="parameter-heading">
      <span class="eyebrow">Conferência</span>
      <div class="parameter-heading-title">
        <h2>Parâmetros do cálculo</h2>
        <app-evidence-info
          [includeAlerts]="true"
          label="Ver considerações gerais da extração"
        />
      </div>
      <p>Revise as parcelas e os critérios aplicáveis ao tipo de dano antes de calcular.</p>
      <div class="parameter-damage-tabs" role="group" aria-label="Tipo de dano dos parâmetros">
        <button type="button" [class.active]="damageType() === 'dano_material'" [attr.aria-pressed]="damageType() === 'dano_material'" (click)="damageType.set('dano_material')">Dano Material</button>
        <button type="button" [class.active]="damageType() === 'dano_moral'" [attr.aria-pressed]="damageType() === 'dano_moral'" (click)="damageType.set('dano_moral')">Dano Moral</button>
      </div>
    </div>

    @if (!store.indices().length) {
      <div class="parameter-catalog-status" role="status" aria-live="polite">
        <p>{{ store.loadingCatalog() ? 'Carregando índices…' : 'Não foi possível carregar os índices de correção.' }}</p>
        <button type="button" class="text-button" [disabled]="store.loadingCatalog()" (click)="store.initialize(true)">Tentar novamente</button>
      </div>
    }

    <div class="parameter-sections">
      @for (section of sections(); track section.title; let first = $first) {
        <details class="parameter-section" [open]="first">
          <summary>
            <span class="parameter-section-title">
              <strong>{{ section.title }}</strong>
              @if (section.title === 'Dano (Parcelas)') {
                <small>{{ installmentCount() }} parcela(s)</small>
              } @else {
                <small>{{ section.fields.length }} {{ section.fields.length === 1 ? 'critério' : 'critérios' }}</small>
              }
            </span>
            <span class="parameter-section-toggle" aria-hidden="true">+</span>
          </summary>

          @if (section.title === 'Dano (Parcelas)') {
            @if (damageType() === 'dano_material') {
              <div class="double-value-control">
                <div class="double-value-copy">
                  <div class="field-label-row">
                    <strong>Valor em dobro</strong>
                    <app-evidence-info
                      [paths]="parameterPath('valor_dobrado_flag')"
                      label="Ver origem da regra de valor em dobro"
                    />
                  </div>
                  <p>Use quando o título ou decisão determinar restituição ou devolução em dobro para o dano material.</p>
                  <small>O multiplicador definido diretamente em uma parcela (1x ou 2x) prevalece sobre esta regra global.</small>
                </div>
                <label class="double-value-switch">
                  <input
                    type="checkbox"
                    [ngModel]="store.parameterValue('valor_dobrado_flag', damageType()) === true"
                    (ngModelChange)="set('valor_dobrado_flag', $event)"
                    [disabled]="!store.canEdit()"
                  >
                  <span>Aplicar valor em dobro</span>
                </label>
              </div>
            }
            <app-installment-editor [(damageType)]="damageType" [showDamageTabs]="false" [embedded]="true" />
          }

          @if (section.fields.length) {
            <div class="parameter-fields">
              @for (field of section.fields; track field.key) {
                @if (field.type === 'checkbox') {
                  <div class="checkbox-with-evidence">
                    <label class="checkbox">
                      <input type="checkbox" [ngModel]="store.parameterValue(field.key, damageType()) === true" (ngModelChange)="set(field.key, $event)" [disabled]="!store.canEdit()">
                      <span>{{ field.label }}</span>
                    </label>
                    <app-evidence-info [paths]="parameterPath(field.key)" [label]="'Ver origem de ' + field.label" />
                  </div>
                } @else {
                  <div class="field">
                    <div class="field-label-row">
                      <span>{{ field.label }}</span>
                      <app-evidence-info [paths]="parameterPath(field.key)" [label]="'Ver origem de ' + field.label" />
                    </div>
                    @if (field.type === 'select') {
                      <select
                        [attr.aria-label]="field.label"
                        [ngModel]="store.parameterValue(field.key, damageType()) ?? ''"
                        (ngModelChange)="set(field.key, $event)"
                        [disabled]="!store.canEdit() || (!field.options && !store.indices().length)"
                      >
                        @for (option of options(field); track option.value) {
                          <option [ngValue]="option.value" [hidden]="option.hidden === true" [disabled]="option.disabled === true">{{ option.label }}</option>
                        }
                      </select>
                    } @else {
                      <input
                        [attr.aria-label]="field.label"
                        [type]="field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'"
                        [ngModel]="store.parameterValue(field.key, damageType()) ?? ''"
                        (ngModelChange)="set(field.key, $event)"
                        [disabled]="!store.canEdit()"
                        placeholder="Não informado"
                      >
                    }
                    @if (field.help) {<small>{{ field.help }}</small>}
                    @if (field.key === 'indice' && selectedIndexHelp(); as coverageHelp) {<small>{{ coverageHelp }}</small>}
                  </div>
                }
              }
            </div>
          }
        </details>
      }
    </div>
  `,
})
export class ParameterPanelComponent {
  readonly store = inject(WorkspaceStore);
  readonly damageType = model<DamageType>('dano_material');
  private readonly sectionOrder = ['Dano (Parcelas)', 'Atualização monetária', 'Juros moratórios', 'Prescrição', 'Honorários', 'Multa', 'Compensação', 'Duplo índice'];
  readonly installmentCount = computed(() => this.store.active().installments.filter(row => row.verba_tipo === this.damageType()).length);
  readonly selectedIndexHelp = computed(() => {
    const key = String(this.store.parameterValue('indice', this.damageType()) ?? '');
    const selected = this.store.indices().find(index => index.chave === key);
    if (!selected || selected.chave === 'sem_correcao') return '';
    if (!selected.disponivel) return 'A série deste índice não está instalada; selecione outro índice ou atualize a base.';
    const first = this.formatCompetence(selected.competencia_inicial);
    const last = this.formatCompetence(selected.competencia_final);
    const maximum = this.formatCompetence(selected.competencia_maxima_atualizacao);
    if (!first || !last) return '';
    return maximum ? `Dados disponíveis: ${first} a ${last}. Competência máxima de atualização: ${maximum}.` : `Dados disponíveis: ${first} a ${last}.`;
  });
  readonly sections = computed(() => {
    const grouped = new Map<string, ParamField[]>();
    for (const title of this.sectionOrder) grouped.set(title, []);
    for (const field of PARAM_FIELDS) {
      if (field.key === 'valor_dobrado_flag') continue;
      if (field.damageTypes && !field.damageTypes.includes(this.damageType())) continue;
      if (!grouped.has(field.section)) continue;
      grouped.get(field.section)!.push(field);
    }
    return this.sectionOrder
      .map(title => ({title, fields: grouped.get(title) ?? []}))
      .filter(section => section.title === 'Dano (Parcelas)' || section.fields.length > 0);
  });

  set(key: ParameterKey, value: string | number | boolean): void {
    this.store.updateParameter(key, value, this.damageType());
  }

  parameterPath(key: ParameterKey): string[] {
    const scoped = ['Atualização monetária','Juros moratórios'].includes(PARAM_FIELDS.find(field => field.key === key)?.section ?? '');
    return scoped
      ? [`parametros_por_dano.${this.damageType()}.${String(key)}`, `parametros.${String(key)}`]
      : [`parametros.${String(key)}`];
  }

  options(field: ParamField): SelectOption[] {
    return field.options ?? [{value: '', label: 'Selecione'}, ...this.store.indices().map(index => ({value: index.chave, label: index.nome, disabled: index.disponivel === false}))];
  }

  private formatCompetence(value?: string | null): string {
    if (!value || !/^\d{4}-\d{2}$/.test(value)) return '';
    const months = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
    const month = Number(value.slice(5, 7));
    return month >= 1 && month <= 12 ? `${months[month - 1]}/${value.slice(0, 4)}` : value;
  }
}

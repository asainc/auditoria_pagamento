/** Catálogo, agrupamento e visibilidade são decisões de apresentação. */
import { Component, computed, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { WorkspaceStore } from '../core/workspace.store';
import { DamageType, PARAM_FIELDS, ParamField, ParameterKey, SelectOption } from './parameter-fields';

@Component({selector:'app-parameter-panel', standalone:true, imports:[FormsModule], template:`
  <div class="parameter-heading"><span class="eyebrow">Conferência</span><h2>Parâmetros do cálculo</h2><p>Preencha conforme os documentos e revise todos os critérios antes de calcular.</p>
    <label class="checkbox"><input type="checkbox" [ngModel]="showAll()" (ngModelChange)="showAll.set($event)"><span>Exibir todos os critérios</span></label>
  </div>
  @if (!store.indices().length) {
    <div role="status" aria-live="polite">
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
            <small>{{ section.fields.length }} {{ section.fields.length === 1 ? 'critério' : 'critérios' }}</small>
          </span>
          <span class="parameter-section-toggle" aria-hidden="true">+</span>
        </summary>
        <div class="parameter-fields">
          @for (field of section.fields; track field.key) {
            @if (field.type === 'checkbox') {
              <label class="checkbox"><input type="checkbox" [ngModel]="store.active().parameters[field.key] === true" (ngModelChange)="set(field.key, $event)" [disabled]="!store.canEdit()"><span>{{ field.label }}</span></label>
            } @else {
              <label class="field">{{ field.label }}
                @if (field.type === 'select') {
                  <select [ngModel]="store.active().parameters[field.key] ?? ''" (ngModelChange)="set(field.key, $event)" [disabled]="!store.canEdit() || (!field.options && !store.indices().length)">
                    @for (option of options(field); track option.value) {<option [ngValue]="option.value" [hidden]="option.hidden === true" [disabled]="option.disabled === true">{{ option.label }}</option>}
                  </select>
                } @else {
                  <input [type]="field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'" [ngModel]="store.active().parameters[field.key] ?? ''" (ngModelChange)="set(field.key, $event)" [disabled]="!store.canEdit()" placeholder="Não informado">
                }
                @if (field.help) {<small>{{ field.help }}</small>}
                @if (field.key === 'indice' && selectedIndexHelp(); as coverageHelp) {<small>{{ coverageHelp }}</small>}
              </label>
            }
          }
        </div>
      </details>
    }
  </div>
`})
export class ParameterPanelComponent {
  readonly store = inject(WorkspaceStore);
  readonly damageType = input<DamageType>('dano_material');
  readonly showAll = signal(true);
  readonly selectedIndexHelp = computed(() => {
    const key = String(this.store.active().parameters.indice ?? '');
    const selected = this.store.indices().find(index => index.chave === key);
    if (!selected || selected.chave === 'sem_correcao') return '';
    if (!selected.disponivel) return 'A série deste índice não está instalada; selecione outro índice ou atualize a base.';
    const first = this.formatCompetence(selected.competencia_inicial);
    const last = this.formatCompetence(selected.competencia_final);
    const maximum = this.formatCompetence(selected.competencia_maxima_atualizacao);
    if (!first || !last) return '';
    return maximum
      ? `Dados disponíveis: ${first} a ${last}. Competência máxima de atualização: ${maximum}.`
      : `Dados disponíveis: ${first} a ${last}.`;
  });
  readonly sections = computed(() => {
    const grouped = new Map<string, ParamField[]>();
    for (const field of PARAM_FIELDS) {
      if (!this.showAll() && field.damageTypes && !field.damageTypes.includes(this.damageType())) continue;
      grouped.set(field.section, [...(grouped.get(field.section) ?? []), field]);
    }
    return Array.from(grouped, ([title, fields]) => ({title, fields}));
  });
  set(key: ParameterKey, value: string | number | boolean): void { this.store.updateParameter(key, value); }
  options(field: ParamField): SelectOption[] {
    return field.options ?? [
      {value:'',label:'Selecione'},
      ...this.store.indices().map(index => ({value:index.chave,label:index.nome,disabled:index.disponivel === false})),
    ];
  }
  private formatCompetence(value?: string | null): string {
    if (!value || !/^\d{4}-\d{2}$/.test(value)) return '';
    const months = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
    const month = Number(value.slice(5,7));
    return month >= 1 && month <= 12 ? `${months[month - 1]}/${value.slice(0,4)}` : value;
  }
}

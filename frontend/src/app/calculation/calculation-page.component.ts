/** Página compõe componentes coesos e concentra apenas a organização visual. */
import { Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { WorkspaceStore } from '../core/workspace.store';
import { missingFields } from '../core/calculation-mapper';
import { DamageType } from './parameter-fields';
import { ProcessSelectorComponent } from './process-selector.component';
import { PdfViewerComponent } from './pdf-viewer.component';
import { ParameterPanelComponent } from './parameter-panel.component';
import { InstallmentEditorComponent } from './installment-editor.component';
import { EvidencePanelComponent } from './evidence-panel.component';
import { ResultPanelComponent } from './result-panel.component';
import { ExtractionLogComponent } from './extraction-log.component';

@Component({
  selector: 'app-calculation-page',
  standalone: true,
  imports: [
    FormsModule,
    ProcessSelectorComponent,
    PdfViewerComponent,
    ParameterPanelComponent,
    InstallmentEditorComponent,
    EvidencePanelComponent,
    ResultPanelComponent,
    ExtractionLogComponent,
  ],
  template: `
    <header class="page-heading compact-header">
      <div class="page-heading-content compact-header-grid">
        <div class="page-title compact-page-title">
          <button
            type="button"
            class="sidebar-toggle"
            (click)="collapsed.set(!collapsed())"
            [attr.aria-expanded]="!collapsed()"
            aria-controls="process-sidebar"
            aria-label="Recolher ou expandir lista de processos"
          >☰</button>
          <div>
            <span class="eyebrow">Operação</span>
            <div class="page-title-line"><h1>Conferência do cálculo</h1>@if (store.mockMode()) {<span class="test-mode-badge">Cálculo manual</span>}</div>
          </div>
        </div>

        <nav class="section-navigation compact-section-navigation" aria-label="Navegação da conferência">
          <button type="button" [class.active]="tab() === 'parcelas'" (click)="tab.set('parcelas')">Parcelas <span>{{ store.active().installments.length }}</span></button>
          <button type="button" [class.active]="tab() === 'evidencias'" (click)="tab.set('evidencias')">Evidências</button>
          <button type="button" [class.active]="tab() === 'parametros'" (click)="tab.set('parametros')">Parâmetros @if (missing().length) { <span>{{ missing().length }}</span> }</button>
          <button type="button" [class.active]="tab() === 'logs'" (click)="tab.set('logs')">Logs</button>
          <button type="button" [class.active]="tab() === 'resultado'" (click)="tab.set('resultado')">Resultado</button>
        </nav>

        <div class="calculation-action compact-calculation-action">
          <label class="checkbox review compact-review">
            <input
              type="checkbox"
              [ngModel]="store.active().humanReviewed"
              (ngModelChange)="store.review($event)"
              [disabled]="!store.canEdit() || store.reviewing()"
            >
            <span>
              Confirmo a revisão dos dados<br>
              <small>Parcelas e critérios do cálculo</small>
            </span>
          </label>

          <button
            type="button"
            class="primary calculate-button compact-calculate-button"
            (click)="store.calculate()"
            [disabled]="!store.active().humanReviewed || store.calculating() || !store.canEdit()"
          >{{ store.calculating() ? 'Calculando…' : 'Calcular débito' }}</button>
        </div>
      </div>
    </header>

    <div class="workspace" [class.sidebar-collapsed]="collapsed()">
      @if (!collapsed()) {
        <aside id="process-sidebar" class="process-sidebar"><app-process-selector /></aside>
      }

      <main class="document-workspace">
        <section class="document-panel"><app-pdf-viewer /></section>

        <section class="work-tray">
          <div class="tray-content no-tab-strip">
            @switch (tab()) {
              @case ('parcelas') {<app-installment-editor [(damageType)]="damageType" />}
              @case ('evidencias') {<app-evidence-panel />}
              @case ('parametros') {
                <div class="parameters-tab">
                  <app-parameter-panel [damageType]="damageType()" />
                  @if (store.canEdit() && missing().length) {
                    <div class="pending-fields">
                      <strong>Campos ainda necessários</strong>
                      <ul>
                        @for (field of missing(); track field) {
                          <li>{{ field }}</li>
                        }
                      </ul>
                    </div>
                  }
                </div>
              }
              @case ('logs') {<app-extraction-log />}
              @case ('resultado') {<app-result-panel />}
            }
          </div>
        </section>
      </main>
    </div>
  `,
})
export class CalculationPageComponent {
  readonly store = inject(WorkspaceStore);
  readonly collapsed = signal(false);
  readonly damageType = signal<DamageType>('dano_material');
  readonly tab = signal<'parcelas' | 'evidencias' | 'parametros' | 'logs' | 'resultado'>('parcelas');
  readonly missing = computed(() => missingFields(this.store.active()));

  constructor() {
    void this.store.initialize();
    effect(() => {
      if (this.store.active().result) {
        this.tab.set('resultado');
      }
    });
  }
}

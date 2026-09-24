/** Evidências são texto escapado pelo Angular, com navegação para a página da fonte. */
import { Component, inject, output } from '@angular/core';
import { WorkspaceStore } from '../core/workspace.store';
import { FieldEvidence } from '../core/contracts';
import { PARAM_FIELDS, ParameterKey } from './parameter-fields';

@Component({selector:'app-evidence-panel', standalone:true, template:`
  <div class="panel-heading"><div><h2>Evidências da extração</h2><p>Confira as sugestões na página de origem. Conflitos exigem revisão.</p></div></div>
  <div class="tray-scroll evidence-list">
    @if (store.active().extraction; as result) {
      @for (adjustment of result.ajustes_operacionais ?? []; track $index) {
        <article class="evidence-row operational-rule"><div><strong>{{ label(adjustment.campo) }}</strong><span>{{ adjustment.valor }}</span></div><p><strong>Regra operacional aplicada</strong> · {{ adjustment.motivo }}</p></article>
      }
      @if (result.alertas.length && result.ajustes_operacionais?.length) {<p class="quiet-empty">Observações da leitura documental, antes dos padrões acima. Regras operacionais não são trechos da decisão.</p>}
      @for (alert of result.alertas; track $index) {<p class="evidence-alert">{{ alert }}</p>}
      @for (field of result.campos; track $index) {
        <article class="evidence-row">
          <div><strong>{{ label(field.campo) }}</strong><span>{{ field.valor }}</span></div>
          @if (currentValue(field.campo) !== null) {
            <div class="evidence-comparison"><span>Extraído: <strong>{{ field.valor }}</strong></span><span>Atual: <strong>{{ currentValue(field.campo) }}</strong></span><span>Origem: {{ field.documento }} · página {{ field.pagina }}</span></div>
          }
          <blockquote>{{ field.trecho }}</blockquote>
          <button class="text-button" type="button" (click)="showSource(field)">{{ field.documento }} · página {{ field.pagina }} · abrir evidência</button>
        </article>
      } @empty {<p class="quiet-empty">Nenhum campo com evidência verificável foi extraído.</p>}
    } @else {<p class="quiet-empty">As evidências aparecerão após a extração. Você também pode conferir o PDF e preencher os dados manualmente.</p>}
  </div>
`})
export class EvidencePanelComponent {
  readonly sourceSelected = output<void>();
  readonly store = inject(WorkspaceStore);
  label(path: string): string {return PARAM_FIELDS.find(field => `parametros.${field.key}` === path)?.label ?? path.replace(/_/g,' ');}
  currentValue(path: string): string | number | boolean | null {
    if (!path.startsWith('parametros.')) return null;
    const key = path.split('.', 2)[1] as ParameterKey;
    const value = this.store.active().parameters[key];
    return value === undefined ? null : value;
  }
  showSource(field: FieldEvidence): void {
    const document = this.store.documents().find(item => item.nome === field.documento);
    if (document) {
      this.store.selectedDocument.set(document.identificador);
      this.store.pdfPage.set(field.pagina);
      this.store.pdfHighlight.set(field.trecho);
      this.sourceSelected.emit();
    }
  }
}

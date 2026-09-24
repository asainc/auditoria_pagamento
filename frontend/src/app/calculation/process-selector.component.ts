/** A seleção é vazia no início e mantém a busca sob controle do usuário. */
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { WorkspaceStore } from '../core/workspace.store';

@Component({selector:'app-process-selector', standalone:true, imports:[FormsModule], template:`
  <div class="sidebar-heading"><span class="eyebrow">Documentos do processo</span><h2>Arquivo de trabalho</h2></div>
  <div class="connection-status" [class.offline]="store.connection.state() === 'offline'" role="status" aria-live="polite">
    <strong>{{ store.connection.state() === 'checking' ? 'Verificando conexão…' : store.connection.message() }}</strong>
    @if (store.connection.extraction(); as extraction) { <p>{{ extraction.configurada ? 'Extração automática disponível após o envio.' : extraction.mensagem }}</p> }
    <button type="button" class="text-button" [disabled]="store.connection.state() === 'checking' || store.uploading()" (click)="store.initialize(true)">Verificar conexão</button>
  </div>

  <section class="mock-mode-panel" [class.active]="store.mockMode()" [class.disabled]="!!store.selectedProcess()">
    <label class="checkbox">
      <input
        type="checkbox"
        [ngModel]="store.mockMode()"
        (ngModelChange)="store.setMockMode($event)"
        [disabled]="!!store.selectedProcess()"
      >
      <span>
        <strong>Cálculo manual</strong>
        <small>@if (store.selectedProcess()) { Desmarque o processo para habilitar. } @else { Habilita parcelas e parâmetros para preenchimento manual e salva o resultado no histórico. }</small>
      </span>
    </label>
  </section>

  @if (store.mockMode() && !store.selectedProcess()) {
    <label class="field manual-identifier-field">
      <span>Identificador do cálculo manual</span>
      <input
        type="text"
        [ngModel]="store.active().identificadorCalculo"
        (ngModelChange)="store.setManualIdentifier($event)"
        placeholder="Ex.: 1001"
        maxlength="80"
        autocomplete="off"
        aria-describedby="manual-identifier-help"
      >
      <small id="manual-identifier-help">Obrigatório. Use um identificador único para localizar e versionar este cálculo no histórico.</small>
    </label>
  }

  <label class="upload-zone" [class.disabled]="store.uploading() || store.connection.state() !== 'online'">
    <span class="upload-mark" aria-hidden="true">↑</span><strong>{{ store.uploading() ? 'Recebendo PDFs…' : 'Enviar documentos' }}</strong>
    <span>Selecione um ou mais PDFs</span><small>Nome: processo_sequência.pdf</small>
    <input type="file" accept="application/pdf,.pdf" multiple (change)="upload($event)" [disabled]="store.uploading() || store.connection.state() !== 'online'" aria-label="Enviar documentos PDF">
  </label>
  <label class="field">Buscar processo<input [ngModel]="query()" (ngModelChange)="query.set($event)" placeholder="Digite o número" autocomplete="off"></label>
  <label class="field">Processo a calcular
    <select [ngModel]="store.selectedProcess()" (ngModelChange)="store.selectProcess($event)">
      <option value="">{{ store.mockMode() ? 'Sem processo — cálculo manual' : 'Selecione o processo' }}</option>
      @for (process of filtered(); track process.numero_processo) { <option [value]="process.numero_processo">{{ process.numero_processo }}</option> }
    </select>
  </label>
  <p class="subtle">{{ store.processes().length }} processo(s) disponível(is)</p>
  @if (store.selectedProcess()) {
    <div class="sidebar-files">
      @for (document of store.documents(); track document.identificador) {
        <button type="button" class="file-item" [class.selected]="store.selectedDocument() === document.identificador" (click)="selectDocument(document.identificador)">
          <span class="file-badge">PDF</span><span><strong>{{ document.nome }}</strong><small>{{ document.paginas }} página(s)</small></span>
        </button>
      }
    </div>
    @if (store.extractionStatus(); as status) {
      <div class="extraction-status" [class.processing]="status.estado === 'executando' || status.estado === 'aguardando'" role="status">
        <strong>{{ status.estado === 'falha' ? 'Extração não concluída' : status.estado === 'bloqueada' ? 'Configuração de extração pendente' : status.etapa }}</strong><p>{{ status.mensagem }}</p>
        <button type="button" class="text-button" (click)="store.retryExtraction()" [disabled]="status.estado === 'executando' || status.estado === 'aguardando'">Repetir extração</button>
      </div>
    }
  } @else if (store.mockMode()) {
    <div class="sidebar-note"><strong>Cálculo manual habilitado.</strong><br>Informe o identificador, preencha parcelas e parâmetros. Ao calcular, o resultado será salvo automaticamente no histórico.</div>
  } @else { <div class="sidebar-note">Envie os PDFs e selecione o processo para começar a conferência.</div> }
`})
export class ProcessSelectorComponent {
  readonly store = inject(WorkspaceStore);
  readonly query = signal('');
  readonly filtered = computed(() => this.store.processes().filter(process => process.numero_processo.includes(this.query()) || process.numero_processo === this.store.selectedProcess()));
  upload(event: Event): void { const element = event.target as HTMLInputElement; void this.store.upload(Array.from(element.files ?? [])); element.value = ''; }
  selectDocument(id: string): void { this.store.selectedDocument.set(id); this.store.pdfPage.set(1); }
}

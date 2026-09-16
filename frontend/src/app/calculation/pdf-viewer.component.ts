/** O visualizador consome somente Blob da API, com cancelamento e descarte de URLs. */
import { Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DomSanitizer } from '@angular/platform-browser';
import { DocumentApiService } from '../core/document-api.service';
import { WorkspaceStore } from '../core/workspace.store';
import { Notifications, saveBlob } from '../core/notifications';

@Component({selector:'app-pdf-viewer', standalone:true, imports:[FormsModule], template:`
  <div class="panel-heading viewer-heading">
    <label class="field compact">Documento em visualização<select [ngModel]="store.selectedDocument()" (ngModelChange)="select($event)" [disabled]="!store.documents().length">
      <option value="">Selecione um PDF</option>@for (document of store.documents(); track document.identificador) {<option [value]="document.identificador">{{ document.nome }}</option>}
    </select></label>
    <button type="button" class="small-button" (click)="download()" [disabled]="!blob()">Baixar PDF</button>
  </div>
  <div class="pdf-surface">
    @if (loading()) { <div class="empty-state" role="status">Carregando documento…</div> }
    @else if (safeUrl()) { <iframe [src]="safeUrl()" title="Documento PDF para conferência"></iframe> }
    @else { <div class="empty-state"><span class="document-outline" aria-hidden="true"></span><h2>O documento fica aqui</h2><p>Selecione um processo para consultar os PDFs durante a revisão dos parâmetros.</p></div> }
  </div>
`})
export class PdfViewerComponent {
  readonly store = inject(WorkspaceStore);
  private readonly api = inject(DocumentApiService);
  private readonly notifications = inject(Notifications);
  private readonly sanitizer = inject(DomSanitizer);
  readonly loading = signal(false);
  readonly blob = signal<Blob | null>(null);
  private readonly objectUrl = signal('');
  readonly safeUrl = computed(() => this.objectUrl() ? this.sanitizer.bypassSecurityTrustResourceUrl(`${this.objectUrl()}#page=${this.store.pdfPage()}&view=FitH`) : null);

  constructor() {
    effect(onCleanup => {
      const id = this.store.selectedDocument();
      this.objectUrl.set(''); this.blob.set(null); this.loading.set(Boolean(id));
      if (!id) return;
      let url = '';
      const subscription = this.api.file(id).subscribe({next: blob => { url = URL.createObjectURL(blob); this.objectUrl.set(url); this.blob.set(blob); this.loading.set(false); }, error: error => {this.loading.set(false); this.notifications.error(error);}});
      onCleanup(() => {subscription.unsubscribe(); if (url) URL.revokeObjectURL(url);});
    });
  }
  select(id: string): void {this.store.selectedDocument.set(id); this.store.pdfPage.set(1);}
  download(): void { const blob = this.blob(); if (blob) saveBlob(blob, this.store.documents().find(item => item.identificador === this.store.selectedDocument())?.nome ?? 'documento.pdf'); }
}

/** Fachada fina da área de trabalho; estado, extração, cálculo e auditoria vivem em stores específicos. */
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { ConnectionApiService } from './connection-api.service';
import { DocumentApiService } from './document-api.service';
import { IndexApiService } from './index-api.service';
import { Notifications } from './notifications';
import { WorkspaceStateStore, MANUAL_DRAFT_KEY } from './workspace-state.store';
import { WorkspaceAuditStore } from './workspace-audit.store';
import { WorkspaceExtractionStore } from './workspace-extraction.store';
import { WorkspaceCalculationStore } from './workspace-calculation.store';
import { blankDraft } from './calculation-mapper';
import { ParameterKey } from '../calculation/parameter-fields';

@Injectable({providedIn:'root'})
export class WorkspaceStore {
  private readonly state = inject(WorkspaceStateStore);
  private readonly audits = inject(WorkspaceAuditStore);
  private readonly extractions = inject(WorkspaceExtractionStore);
  private readonly calculations = inject(WorkspaceCalculationStore);
  private readonly documentsApi = inject(DocumentApiService);
  private readonly indexApi = inject(IndexApiService);
  readonly notices = inject(Notifications);
  readonly connection = inject(ConnectionApiService);
  private initialized = false;
  readonly loadingCatalog = signal(false);

  // API pública preservada para os componentes existentes.
  readonly processes = this.state.processes;
  readonly selectedProcess = this.state.selectedProcess;
  readonly documents = this.state.documents;
  readonly selectedDocument = this.state.selectedDocument;
  readonly pdfPage = this.state.pdfPage;
  readonly pdfHighlight = this.state.pdfHighlight;
  readonly drafts = this.state.drafts;
  readonly mockMode = this.state.mockMode;
  readonly draftKey = this.state.draftKey;
  readonly canEdit = this.state.canEdit;
  readonly mockWithoutProcess = this.state.mockWithoutProcess;
  readonly active = this.state.active;
  readonly indices = this.state.indices;
  readonly extractionStatus = this.extractions.extractionStatus;
  readonly uploading = this.extractions.uploading;
  readonly calculating = this.calculations.calculating;
  readonly exporting = this.calculations.exporting;
  readonly reviewing = this.calculations.reviewing;
  readonly parameterChanges = this.audits.parameterChanges;

  /** Carrega recursos independentes sem descartar os índices se a busca de processos falhar. */
  async initialize(force = false): Promise<void> {
    if (this.loadingCatalog() || (this.initialized && !force)) return;
    this.loadingCatalog.set(true);
    try {
      if (!await this.connection.check()) return;
      const [processes, indices] = await Promise.allSettled([
        firstValueFrom(this.documentsApi.processes()),
        firstValueFrom(this.indexApi.options()),
      ]);
      if (processes.status === 'fulfilled') this.processes.set(processes.value);
      else this.notices.error(processes.reason);
      if (indices.status === 'fulfilled' && indices.value.length > 0) {
        this.indices.set(indices.value);
      } else {
        this.notices.error(indices.status === 'rejected' ? indices.reason : new Error('O servidor retornou uma lista de índices vazia.'));
      }
      this.initialized = processes.status === 'fulfilled' && indices.status === 'fulfilled' && indices.value.length > 0;
    } catch(error) { this.notices.error(error); }
    finally { this.loadingCatalog.set(false); }
  }

  setMockMode(enabled: boolean): void {
    if (!enabled) void this.audits.flushAll();
    if (enabled && this.selectedProcess()) { this.mockMode.set(false); return; }
    this.mockMode.set(enabled);
    if (enabled) {
      this.state.ensureDraft(MANUAL_DRAFT_KEY, 'manual');
      void this.audits.load(this.drafts()[MANUAL_DRAFT_KEY]?.draftId ?? '');
    } else {
      this.parameterChanges.set([]);
    }
  }

  async upload(files: File[]): Promise<void> {
    await this.extractions.upload(files, process => this.selectProcess(process));
  }

  async selectProcess(process: string): Promise<void> {
    try { await this.audits.flushAll(); }
    catch(error) { this.notices.error(error); return; }
    this.extractions.stopPolling();
    if (process) this.mockMode.set(false);
    this.selectedProcess.set(process);
    this.selectedDocument.set('');
    this.pdfPage.set(1);
    this.pdfHighlight.set('');
    this.documents.set([]);
    this.extractionStatus.set(null);
    this.parameterChanges.set([]);
    if (!process) return;
    this.state.ensureDraft(process, 'processo');
    void this.audits.load(process);
    try {
      const documents = await firstValueFrom(this.documentsApi.documents(process));
      if (this.selectedProcess() !== process) return;
      this.documents.set(documents);
      this.selectedDocument.set(documents[0]?.identificador ?? '');
      this.extractions.watch(process);
    } catch(error) { this.notices.error(error); }
  }

  update(transform: Parameters<WorkspaceStateStore['update']>[0]): void { this.state.update(transform); }

  updateParameter(key: ParameterKey, value: string|number|boolean|null): void {
    const snapshot = this.active();
    const previous = snapshot.parameters[key] ?? null;
    if (JSON.stringify(previous) === JSON.stringify(value)) return;
    this.state.update(draft => ({...draft,parameters:{...draft.parameters,[key]:value}}));
    this.audits.queue(snapshot, key, previous, value);
  }

  review(confirmed: boolean): Promise<void> { return this.calculations.review(confirmed); }
  refreshFees(): Promise<void> { return this.calculations.refreshFees(); }
  retryExtraction(): Promise<void> { return this.extractions.retry(); }
  calculate(): Promise<void> { return this.calculations.calculate(); }
  downloadPdf(audit: boolean): Promise<void> { return this.calculations.downloadPdf(audit); }
}

/** Estado visual e rascunhos vivem no Angular; SQLite recebe somente estado de negócio. */
import { Injectable, computed, inject, signal } from '@angular/core';
import { Subscription, exhaustMap, firstValueFrom, takeWhile, timer } from 'rxjs';
import { ApiConfiguration } from './config';
import { ConnectionApiService } from './connection-api.service';
import { CalculationApiService } from './calculation-api.service';
import { DocumentApiService } from './document-api.service';
import { ExtractionApiService } from './extraction-api.service';
import { IndexApiService } from './index-api.service';
import { RevisionAuditApiService } from './revision-audit-api.service';
import { Notifications, saveBlob } from './notifications';
import { DocumentMetadata, ExtractionStatus, IndexOption, ParameterChangeInput, ParameterChangeRecord, ProcessSummary } from './contracts';
import { WorkspaceDraft, applyExtraction, blankDraft, decimalText, toCalculationRequest } from './calculation-mapper';
import { ParameterKey } from '../calculation/parameter-fields';

const MANUAL_DRAFT_KEY = '__manual__';

@Injectable({providedIn:'root'})
export class WorkspaceStore {
  private readonly documentsApi = inject(DocumentApiService);
  private readonly extractionApi = inject(ExtractionApiService);
  private readonly calculationApi = inject(CalculationApiService);
  private readonly indexApi = inject(IndexApiService);
  private readonly revisionAuditApi = inject(RevisionAuditApiService);
  private readonly config = inject(ApiConfiguration);
  readonly notices = inject(Notifications);
  readonly connection = inject(ConnectionApiService);
  readonly processes = signal<ProcessSummary[]>([]);
  readonly selectedProcess = signal('');
  readonly documents = signal<DocumentMetadata[]>([]);
  readonly selectedDocument = signal('');
  readonly pdfPage = signal(1);
  readonly drafts = signal<Record<string, WorkspaceDraft>>({});
  readonly mockMode = signal(false);
  readonly draftKey = computed(() => this.selectedProcess() || (this.mockMode() ? MANUAL_DRAFT_KEY : ''));
  readonly canEdit = computed(() => Boolean(this.draftKey()));
  readonly mockWithoutProcess = computed(() => this.mockMode() && !this.selectedProcess());
  readonly active = computed(() => {
    const key = this.draftKey();
    if (!key) return blankDraft('', 'processo');
    return this.drafts()[key] ?? (key === MANUAL_DRAFT_KEY ? blankDraft('', 'manual') : blankDraft(key, 'processo'));
  });
  readonly extractionStatus = signal<ExtractionStatus | null>(null);
  readonly indices = signal<IndexOption[]>([]);
  readonly uploading = signal(false);
  readonly calculating = signal(false);
  readonly exporting = signal(false);
  readonly reviewing = signal(false);
  readonly parameterChanges = signal<ParameterChangeRecord[]>([]);
  private polling: Subscription | null = null;
  private readonly pendingAudits = new Map<string, {payload: ParameterChangeInput; timer: ReturnType<typeof setTimeout>}>();
  private initialized = false;

  /** A busca inicial preserva seleção vazia, mesmo com processos já armazenados. */
  async initialize(force = false): Promise<void> {
    if (this.initialized && !force) return;
    if (!await this.connection.check()) return;
    try {
      const [processes, indices] = await Promise.all([firstValueFrom(this.documentsApi.processes()), firstValueFrom(this.indexApi.options())]);
      this.processes.set(processes); this.indices.set(indices); this.initialized = true;
    } catch (error) { this.notices.error(error); }
  }

  /** Habilita um rascunho manual vazio somente quando nenhum processo real está selecionado. */
  setMockMode(enabled: boolean): void {
    if (!enabled) void this.flushAllParameterAudits();
    if (enabled && this.selectedProcess()) {
      this.mockMode.set(false);
      return;
    }
    this.mockMode.set(enabled);
    if (enabled && !this.drafts()[MANUAL_DRAFT_KEY]) {
      this.drafts.update(values => ({...values, [MANUAL_DRAFT_KEY]:blankDraft('', 'manual')}));
    }
    if (enabled) void this.loadParameterChanges(this.drafts()[MANUAL_DRAFT_KEY]?.draftId ?? '');
    else this.parameterChanges.set([]);
  }

  /** Reenvio de arquivos atualiza as listas, sem selecionar processo arbitrariamente. */
  async upload(files: File[]): Promise<void> {
    if (!files.length || this.uploading()) return;
    this.uploading.set(true);
    try {
      if (!await this.connection.check()) { this.notices.show(this.connection.message(), 'error'); return; }
      const response = await firstValueFrom(this.documentsApi.upload(files));
      this.processes.set(await firstValueFrom(this.documentsApi.processes()));
      this.notices.show(`${response.documentos.length} documento(s) recebido(s). Selecione o processo para revisar.`);
      const blocked = response.extracoes.find(status => status.estado === 'bloqueada');
      if (blocked) this.notices.show(blocked.mensagem);
      const selected = this.selectedProcess();
      if (response.documentos.some(row => row.numero_processo === selected)) {
        this.update(draft => ({...draft, extraction:null}));
        await this.selectProcess(selected);
      }
    } catch (error) { this.notices.error(error); }
    finally { this.uploading.set(false); }
  }

  /** Cada processo possui rascunho independente; processo real e cálculo manual nunca compartilham dados. */
  async selectProcess(process: string): Promise<void> {
    try { await this.flushAllParameterAudits(); }
    catch (error) { this.notices.error(error); return; }
    this.polling?.unsubscribe();
    if (process) this.mockMode.set(false);
    this.selectedProcess.set(process); this.selectedDocument.set(''); this.pdfPage.set(1); this.documents.set([]); this.extractionStatus.set(null); this.parameterChanges.set([]);
    if (!process) return;
    this.drafts.update(values => ({...values, [process]:values[process] ?? blankDraft(process, 'processo')}));
    void this.loadParameterChanges(process);
    try {
      const documents = await firstValueFrom(this.documentsApi.documents(process));
      if (this.selectedProcess() !== process) return;
      this.documents.set(documents); this.selectedDocument.set(documents[0]?.identificador ?? '');
      this.watchExtraction(process);
    } catch (error) { this.notices.error(error); }
  }

  /** Qualquer edição invalida o resultado e a confirmação referentes aos dados anteriores. */
  update(transform: (draft: WorkspaceDraft) => WorkspaceDraft): void {
    const key = this.draftKey();
    if (!key) return;
    this.drafts.update(values => {
      const previous = values[key] ?? (key === MANUAL_DRAFT_KEY ? blankDraft('', 'manual') : blankDraft(key, 'processo'));
      const next = transform(previous);
      const changedDate = next.parameters.mes_atualizacao !== previous.parameters.mes_atualizacao || next.parameters.ano_atualizacao !== previous.parameters.ano_atualizacao;
      return {...values, [key]:{...next, automaticCompetence:changedDate ? false : next.automaticCompetence, humanReviewed:false, result:null, confirmedRequest:null, revision:previous.revision + 1}};
    });
  }

  /** Atualiza um parâmetro e registra a alteração humana de forma desacoplada do cálculo. */
  updateParameter(key: ParameterKey, value: string | number | boolean | null): void {
    const snapshot = this.active();
    const previous = snapshot.parameters[key] ?? null;
    if (JSON.stringify(previous) === JSON.stringify(value)) return;
    this.update(draft => ({...draft, parameters:{...draft.parameters, [key]:value}}));
    this.queueParameterAudit(snapshot, key, previous, value);
  }

  /** Agrupa digitação contínua para registrar mudanças sem transformar cada tecla em evento. */
  private queueParameterAudit(
    snapshot: WorkspaceDraft,
    key: ParameterKey,
    previous: string | number | boolean | null,
    next: string | number | boolean | null,
  ): void {
    const auditKey = `${snapshot.draftId}:${key}`;
    const existing = this.pendingAudits.get(auditKey);
    if (existing) clearTimeout(existing.timer);
    const payload: ParameterChangeInput = existing?.payload
      ? {...existing.payload, valor_novo:next}
      : {
          origem_calculo:snapshot.calculationOrigin,
          numero_processo:snapshot.calculationOrigin === 'processo' ? snapshot.numeroProcesso : null,
          rascunho_id:snapshot.draftId,
          campo:key,
          valor_anterior:previous,
          valor_novo:next,
          extracao_id:snapshot.appliedExtractionId || null,
        };
    const timer = setTimeout(() => void this.flushParameterAudit(auditKey, false), 650);
    this.pendingAudits.set(auditKey, {payload, timer});
  }

  private async flushParameterAudit(auditKey: string, required: boolean): Promise<void> {
    const pending = this.pendingAudits.get(auditKey);
    if (!pending) return;
    clearTimeout(pending.timer);
    try {
      const record = await firstValueFrom(this.revisionAuditApi.record(pending.payload));
      this.pendingAudits.delete(auditKey);
      const current = this.active();
      const sameTarget = record.origem_calculo === 'processo'
        ? current.calculationOrigin === 'processo' && current.numeroProcesso === record.numero_processo
        : current.calculationOrigin === 'manual' && current.draftId === record.rascunho_id;
      if (sameTarget) this.parameterChanges.update(rows => [...rows, record]);
    } catch (error) {
      // Mantém o evento pendente. O timer tenta novamente de forma assíncrona; revisão,
      // troca de contexto e cálculo tratam a falha como bloqueante para não perder auditoria.
      const retryTimer = setTimeout(() => void this.flushParameterAudit(auditKey, false), 3000);
      this.pendingAudits.set(auditKey, {payload:pending.payload, timer:retryTimer});
      if (required) throw error;
      this.notices.error(error);
    }
  }

  /** Persiste imediatamente todas as edições pendentes antes de mudar contexto ou calcular. */
  private async flushAllParameterAudits(): Promise<void> {
    const keys = [...this.pendingAudits.keys()];
    for (const key of keys) await this.flushParameterAudit(key, true);
  }

  private async loadParameterChanges(reference: string): Promise<void> {
    if (!reference) { this.parameterChanges.set([]); return; }
    const draft = this.active();
    try {
      const rows = draft.calculationOrigin === 'processo'
        ? await firstValueFrom(this.revisionAuditApi.listProcess(reference))
        : await firstValueFrom(this.revisionAuditApi.listDraft(reference));
      const current = this.active();
      const sameTarget = draft.calculationOrigin === 'processo'
        ? current.calculationOrigin === 'processo' && current.numeroProcesso === reference
        : current.calculationOrigin === 'manual' && current.draftId === reference;
      if (sameTarget) this.parameterChanges.set(rows);
    } catch (error) {
      this.notices.error(error);
    }
  }

  async review(confirmed: boolean): Promise<void> {
    try { await this.flushAllParameterAudits(); }
    catch (error) { this.notices.error(error); return; }
    const key = this.draftKey();
    if (!key || this.reviewing()) return;
    if (!confirmed) {this.drafts.update(values => ({...values,[key]:{...values[key],humanReviewed:false}})); return;}
    const snapshot = this.drafts()[key]; this.reviewing.set(true);
    try {
      const automatic = snapshot.automaticCompetence || (!snapshot.parameters.mes_atualizacao && !snapshot.parameters.ano_atualizacao);
      const current = automatic ? await firstValueFrom(this.calculationApi.defaults()) : null;
      if (this.drafts()[key].revision !== snapshot.revision || this.draftKey() !== key) return;
      this.drafts.update(values => ({...values,[key]:{...values[key],parameters:current ? {...values[key].parameters,mes_atualizacao:current.mes,ano_atualizacao:current.ano} : values[key].parameters,automaticCompetence:automatic,humanReviewed:true,result:null,confirmedRequest:null}}));
    } catch(error) {this.notices.error(error);} finally {this.reviewing.set(false);}
  }

  /** Valores dependentes voltam do backend e sempre exigem nova confirmação. */
  async refreshFees(): Promise<void> {
    const key = this.draftKey(); const snapshot = this.active();
    if (!key || !snapshot.feesOnMoralDamages) return;
    try {
      const rows = await firstValueFrom(this.calculationApi.prepareFees({parcelas:snapshot.installments.map(row => ({...row,valor_singelo:decimalText(row.valor_singelo)})),percentual:decimalText(String(snapshot.parameters.honorarios ?? ''))}));
      if (key !== this.draftKey() || snapshot.revision !== this.active().revision) {this.notices.show('Os dados mudaram. Atualize os honorários novamente.');return;}
      this.update(draft => ({...draft,installments:rows}));
      this.notices.show('Honorários atualizados. Confira as parcelas e confirme novamente a revisão.');
    } catch(error) {this.notices.error(error);}
  }

  /** Polling usa cancelamento por seleção e termina em todos os estados finais. */
  private watchExtraction(process: string): void {
    this.polling?.unsubscribe();
    this.polling = timer(0, this.config.pollInterval).pipe(exhaustMap(() => this.extractionApi.status(process)), takeWhile(status => ['aguardando','executando'].includes(status.estado), true)).subscribe({
      next: status => {
        if (this.selectedProcess() !== process) return;
        this.extractionStatus.set(status);
        if (status.estado === 'pronto' && this.drafts()[process].appliedExtractionId !== status.identificador) void this.loadExtraction(process, status.identificador);
      },
      error: error => this.notices.error(error)
    });
  }

  private async loadExtraction(process: string, job: string): Promise<void> {
    try {
      const result = await firstValueFrom(this.extractionApi.result(process));
      const current = await firstValueFrom(this.extractionApi.status(process));
      if (current.identificador !== job || current.estado !== 'pronto') return;
      // applyExtraction só preenche lacunas: edições humanas feitas no processo selecionado continuam prevalecendo.
      this.drafts.update(values => ({...values, [process]:applyExtraction(values[process] ?? blankDraft(process, 'processo'), result, job, current.atualizado_em)}));
      const documents = await firstValueFrom(this.documentsApi.documents(process));
      if (this.selectedProcess() === process) this.documents.set(documents);
    } catch (error) { this.notices.error(error); }
  }

  async retryExtraction(): Promise<void> {
    const process = this.selectedProcess();
    if (!process) return;
    try { await firstValueFrom(this.extractionApi.start(process)); this.watchExtraction(process); }
    catch (error) { this.notices.error(error); }
  }

  /** Um retorno só é exibido se corresponder à revisão que originou a requisição. */
  async calculate(): Promise<void> {
    if (this.calculating()) return;
    try { await this.flushAllParameterAudits(); }
    catch (error) { this.notices.error(error); return; }
    const key = this.draftKey();
    if (!key) return;
    const draft = this.active();
    this.calculating.set(true);
    try {
      const request = toCalculationRequest(draft);
      const result = await firstValueFrom(this.calculationApi.calculate(request));
      if (this.draftKey() !== key || this.drafts()[key].revision !== draft.revision) {
        this.notices.show('Os dados mudaram durante o cálculo. Revise e calcule novamente.'); return;
      }
      this.drafts.update(values => ({...values, [key]:{...values[key], result, confirmedRequest:request}}));
    } catch (error) { this.notices.error(error); }
    finally { this.calculating.set(false); }
  }

  /** Exportação usa a entrada confirmada do resultado, não um rascunho posterior. */
  async downloadPdf(audit: boolean): Promise<void> {
    const request = this.active().confirmedRequest;
    if (!request || this.exporting()) return;
    this.exporting.set(true);
    const hash = this.active().result?.metadata.indices_sha256 ?? '';
    try { saveBlob(await firstValueFrom(this.calculationApi.pdf(request, audit, hash)), audit ? 'memoria_auditavel.pdf' : 'memoria_calculo.pdf'); }
    catch (error) { this.notices.error(error); }
    finally { this.exporting.set(false); }
  }
}

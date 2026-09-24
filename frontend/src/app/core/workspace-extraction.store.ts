/** Upload, polling e aplicação de extração vivem isolados do restante da UI. */
import { Injectable, inject, signal } from '@angular/core';
import { Subscription, exhaustMap, firstValueFrom, takeWhile, timer } from 'rxjs';
import { ApiConfiguration } from './config';
import { ConnectionApiService } from './connection-api.service';
import { DocumentApiService } from './document-api.service';
import { ExtractionApiService } from './extraction-api.service';
import { Notifications } from './notifications';
import { ExtractionStatus } from './contracts';
import { applyExtraction, blankDraft } from './calculation-mapper';
import { WorkspaceStateStore } from './workspace-state.store';

@Injectable({providedIn:'root'})
export class WorkspaceExtractionStore {
  private readonly documentsApi = inject(DocumentApiService);
  private readonly extractionApi = inject(ExtractionApiService);
  private readonly config = inject(ApiConfiguration);
  private readonly state = inject(WorkspaceStateStore);
  private readonly notices = inject(Notifications);
  private readonly connection = inject(ConnectionApiService);
  readonly extractionStatus = signal<ExtractionStatus|null>(null);
  readonly uploading = signal(false);
  private polling: Subscription|null = null;

  stopPolling(): void { this.polling?.unsubscribe(); this.polling = null; }

  async upload(files: File[], selectProcess: (process: string) => Promise<void>): Promise<void> {
    if (!files.length || this.uploading()) return;
    this.uploading.set(true);
    try {
      if (!await this.connection.check()) { this.notices.show(this.connection.message(), 'error'); return; }
      const response = await firstValueFrom(this.documentsApi.upload(files));
      this.state.processes.set(await firstValueFrom(this.documentsApi.processes()));
      const blocked = response.extracoes.find(status => status.estado === 'bloqueada');
      if (blocked) this.notices.show(blocked.mensagem, 'error');
      const uploadedProcesses = [...new Set(response.documentos.map(row => row.numero_processo))];
      const selected = this.state.selectedProcess();
      const target = uploadedProcesses.length === 1 ? uploadedProcesses[0] : selected;
      if (target && uploadedProcesses.includes(target)) {
        this.state.drafts.update(values => ({
          ...values,
          [target]: {...(values[target] ?? blankDraft(target, 'processo')), extraction:null, appliedExtractionId:''},
        }));
        await selectProcess(target);
        this.notices.show(`${response.documentos.length} documento(s) recebido(s). Leitura local e consolidação dos parâmetros iniciadas automaticamente.`);
      } else {
        this.notices.show(`${response.documentos.length} documento(s) recebido(s). A extração foi iniciada para todos os processos enviados; selecione um processo para acompanhar.`);
      }
    } catch (error) { this.notices.error(error); }
    finally { this.uploading.set(false); }
  }

  watch(process: string): void {
    this.stopPolling();
    this.polling = timer(0, this.config.pollInterval).pipe(
      exhaustMap(() => this.extractionApi.status(process)),
      takeWhile(status => ['aguardando','executando'].includes(status.estado), true),
    ).subscribe({
      next: status => {
        if (this.state.selectedProcess() !== process) return;
        this.extractionStatus.set(status);
        if (status.estado === 'pronto' && this.state.drafts()[process]?.appliedExtractionId !== status.identificador) {
          void this.load(process, status.identificador);
        }
      },
      error: error => this.notices.error(error),
    });
  }

  async load(process: string, job: string): Promise<void> {
    try {
      const result = await firstValueFrom(this.extractionApi.result(process));
      const current = await firstValueFrom(this.extractionApi.status(process));
      if (current.identificador !== job || current.estado !== 'pronto') return;
      this.state.drafts.update(values => ({
        ...values,
        [process]:applyExtraction(values[process] ?? blankDraft(process, 'processo'), result, job, current.atualizado_em),
      }));
      const documents = await firstValueFrom(this.documentsApi.documents(process));
      if (this.state.selectedProcess() === process) this.state.documents.set(documents);
    } catch (error) { this.notices.error(error); }
  }

  async retry(): Promise<void> {
    const process = this.state.selectedProcess();
    if (!process) return;
    try {
      await firstValueFrom(this.extractionApi.start(process));
      this.watch(process);
    } catch (error) { this.notices.error(error); }
  }
}

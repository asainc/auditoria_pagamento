/** Estado puro da área de trabalho; não executa HTTP nem regras de negócio remotas. */
import { Injectable, computed, signal } from '@angular/core';
import { DocumentMetadata, IndexOption, ProcessSummary } from './contracts';
import { WorkspaceDraft, blankDraft } from './calculation-mapper';

export const MANUAL_DRAFT_KEY = '__manual__';

@Injectable({providedIn:'root'})
export class WorkspaceStateStore {
  readonly processes = signal<ProcessSummary[]>([]);
  readonly selectedProcess = signal('');
  readonly documents = signal<DocumentMetadata[]>([]);
  readonly selectedDocument = signal('');
  readonly pdfPage = signal(1);
  readonly pdfHighlight = signal('');
  readonly drafts = signal<Record<string, WorkspaceDraft>>({});
  readonly mockMode = signal(false);
  readonly indices = signal<IndexOption[]>([]);
  readonly draftKey = computed(() => this.selectedProcess() || (this.mockMode() ? MANUAL_DRAFT_KEY : ''));
  readonly canEdit = computed(() => Boolean(this.draftKey()));
  readonly mockWithoutProcess = computed(() => this.mockMode() && !this.selectedProcess());
  readonly active = computed(() => {
    const key = this.draftKey();
    if (!key) return blankDraft('', 'processo');
    return this.drafts()[key] ?? (key === MANUAL_DRAFT_KEY ? blankDraft('', 'manual') : blankDraft(key, 'processo'));
  });

  ensureDraft(key: string, origin: 'manual'|'processo' = 'processo'): void {
    if (!key || this.drafts()[key]) return;
    this.drafts.update(values => ({...values, [key]:blankDraft(origin === 'manual' ? '' : key, origin)}));
  }

  update(transform: (draft: WorkspaceDraft) => WorkspaceDraft): void {
    const key = this.draftKey();
    if (!key) return;
    this.drafts.update(values => {
      const previous = values[key] ?? (key === MANUAL_DRAFT_KEY ? blankDraft('', 'manual') : blankDraft(key, 'processo'));
      const next = transform(previous);
      const changedDate = next.parameters.mes_atualizacao !== previous.parameters.mes_atualizacao
        || next.parameters.ano_atualizacao !== previous.parameters.ano_atualizacao;
      return {
        ...values,
        [key]:{
          ...next,
          automaticCompetence:changedDate ? false : next.automaticCompetence,
          humanReviewed:false,
          result:null,
          confirmedRequest:null,
          revision:previous.revision + 1,
        },
      };
    });
  }
}

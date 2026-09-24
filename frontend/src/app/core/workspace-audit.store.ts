/** Trilha de revisão humana isolada do restante da área de trabalho. */
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { ParameterChangeInput, ParameterChangeRecord } from './contracts';
import { WorkspaceDraft } from './calculation-mapper';
import { RevisionAuditApiService } from './revision-audit-api.service';
import { Notifications } from './notifications';
import { WorkspaceStateStore } from './workspace-state.store';
import { ParameterKey } from '../calculation/parameter-fields';

@Injectable({providedIn:'root'})
export class WorkspaceAuditStore {
  private readonly api = inject(RevisionAuditApiService);
  private readonly state = inject(WorkspaceStateStore);
  private readonly notices = inject(Notifications);
  readonly parameterChanges = signal<ParameterChangeRecord[]>([]);
  private readonly pending = new Map<string, {payload: ParameterChangeInput; timer: ReturnType<typeof setTimeout>}>();

  queue(snapshot: WorkspaceDraft, key: ParameterKey, previous: string|number|boolean|null, next: string|number|boolean|null): void {
    const auditKey = `${snapshot.draftId}:${key}`;
    const existing = this.pending.get(auditKey);
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
    const timer = setTimeout(() => void this.flush(auditKey, false), 650);
    this.pending.set(auditKey, {payload, timer});
  }

  private async flush(auditKey: string, required: boolean): Promise<void> {
    const pending = this.pending.get(auditKey);
    if (!pending) return;
    clearTimeout(pending.timer);
    try {
      const record = await firstValueFrom(this.api.record(pending.payload));
      this.pending.delete(auditKey);
      const current = this.state.active();
      const sameTarget = record.origem_calculo === 'processo'
        ? current.calculationOrigin === 'processo' && current.numeroProcesso === record.numero_processo
        : current.calculationOrigin === 'manual' && current.draftId === record.rascunho_id;
      if (sameTarget) this.parameterChanges.update(rows => [...rows, record]);
    } catch (error) {
      const retryTimer = setTimeout(() => void this.flush(auditKey, false), 3000);
      this.pending.set(auditKey, {payload:pending.payload, timer:retryTimer});
      if (required) throw error;
      this.notices.error(error);
    }
  }

  async flushAll(): Promise<void> {
    for (const key of [...this.pending.keys()]) await this.flush(key, true);
  }

  async load(reference: string): Promise<void> {
    if (!reference) { this.parameterChanges.set([]); return; }
    const draft = this.state.active();
    try {
      const rows = draft.calculationOrigin === 'processo'
        ? await firstValueFrom(this.api.listProcess(reference))
        : await firstValueFrom(this.api.listDraft(reference));
      const current = this.state.active();
      const sameTarget = draft.calculationOrigin === 'processo'
        ? current.calculationOrigin === 'processo' && current.numeroProcesso === reference
        : current.calculationOrigin === 'manual' && current.draftId === reference;
      if (sameTarget) this.parameterChanges.set(rows);
    } catch (error) { this.notices.error(error); }
  }
}

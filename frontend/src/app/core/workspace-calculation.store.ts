/** Revisão, cálculo e exportação ficam separados da navegação e extração. */
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { CalculationApiService } from './calculation-api.service';
import { Notifications, saveBlob } from './notifications';
import { decimalText, toCalculationRequest } from './calculation-mapper';
import { WorkspaceStateStore } from './workspace-state.store';
import { WorkspaceAuditStore } from './workspace-audit.store';

@Injectable({providedIn:'root'})
export class WorkspaceCalculationStore {
  private readonly api = inject(CalculationApiService);
  private readonly state = inject(WorkspaceStateStore);
  private readonly audits = inject(WorkspaceAuditStore);
  private readonly notices = inject(Notifications);
  readonly calculating = signal(false);
  readonly exporting = signal(false);
  readonly reviewing = signal(false);

  async review(confirmed: boolean): Promise<void> {
    try { await this.audits.flushAll(); }
    catch (error) { this.notices.error(error); return; }
    const key = this.state.draftKey();
    if (!key || this.reviewing()) return;
    if (!confirmed) {
      this.state.drafts.update(values => ({...values,[key]:{...values[key],humanReviewed:false}}));
      return;
    }
    const snapshot = this.state.drafts()[key];
    this.reviewing.set(true);
    try {
      const automatic = snapshot.automaticCompetence || (!snapshot.parameters.mes_atualizacao && !snapshot.parameters.ano_atualizacao);
      const selectedIndex = String(snapshot.parameters.indice ?? '').trim();
      const current = automatic ? await firstValueFrom(this.api.defaults(selectedIndex || undefined)) : null;
      if (this.state.drafts()[key].revision !== snapshot.revision || this.state.draftKey() !== key) return;
      this.state.drafts.update(values => ({
        ...values,
        [key]:{
          ...values[key],
          parameters:current ? {...values[key].parameters,mes_atualizacao:current.mes,ano_atualizacao:current.ano} : values[key].parameters,
          automaticCompetence:automatic,
          humanReviewed:true,
          result:null,
          confirmedRequest:null,
        },
      }));
    } catch(error) { this.notices.error(error); }
    finally { this.reviewing.set(false); }
  }

  async refreshFees(): Promise<void> {
    const key = this.state.draftKey(); const snapshot = this.state.active();
    if (!key || !snapshot.feesOnMoralDamages) return;
    try {
      const rows = await firstValueFrom(this.api.prepareFees({
        parcelas:snapshot.installments.map(row => ({...row,valor_singelo:decimalText(row.valor_singelo)})),
        percentual:decimalText(String(snapshot.parameters.honorarios ?? '')),
      }));
      if (key !== this.state.draftKey() || snapshot.revision !== this.state.active().revision) {
        this.notices.show('Os dados mudaram. Atualize os honorários novamente.'); return;
      }
      this.state.update(draft => ({...draft,installments:rows}));
      this.notices.show('Honorários atualizados. Confira as parcelas e confirme novamente a revisão.');
    } catch(error) { this.notices.error(error); }
  }

  async calculate(): Promise<void> {
    if (this.calculating()) return;
    try { await this.audits.flushAll(); }
    catch (error) { this.notices.error(error); return; }
    const key = this.state.draftKey();
    if (!key) return;
    const draft = this.state.active();
    this.calculating.set(true);
    try {
      const request = toCalculationRequest(draft);
      const result = await firstValueFrom(this.api.calculate(
        request,
        draft.calculationId,
        draft.calculationVersion,
        draft.expectedCurrentVersion,
      ));
      if (this.state.draftKey() !== key || this.state.drafts()[key].revision !== draft.revision) {
        this.notices.show('Os dados mudaram durante o cálculo. Revise e calcule novamente.'); return;
      }
      this.state.drafts.update(values => ({
        ...values,
        [key]:{
          ...values[key],
          result,
          confirmedRequest:request,
          calculationId:result.registro?.calculo_id ?? values[key].calculationId,
          calculationVersion:result.registro?.versao ?? values[key].calculationVersion,
          expectedCurrentVersion:result.registro?.criada
            ? result.registro.versao
            : values[key].expectedCurrentVersion,
          loadedFromHistory:false,
        },
      }));
      if (result.registro?.criada) {
        this.notices.show(`Cálculo cadastrado como versão ${result.registro.versao}; a execução foi registrada separadamente.`);
      } else if (result.registro) {
        this.notices.show(`Parâmetros e parcelas não mudaram; a versão ${result.registro.versao} foi mantida e uma nova execução foi registrada.`);
      }
    } catch(error) { this.notices.error(error); }
    finally { this.calculating.set(false); }
  }

  async downloadPdf(): Promise<void> {
    const draft = this.state.active();
    const request = draft.confirmedRequest;
    if (!request || this.exporting()) return;
    this.exporting.set(true);
    try {
      const registration = draft.result?.registro;
      const execution = draft.result?.execucao;
      const blob = registration && execution
        ? await firstValueFrom(this.api.executionPdf(registration.calculo_id, execution.execucao_id, false))
        : registration
          ? await firstValueFrom(this.api.versionPdf(registration.calculo_id, registration.versao, false))
          : await firstValueFrom(this.api.pdf(request, draft.result?.metadata.indices_sha256 ?? ''));
      saveBlob(blob, 'memoria_calculo.pdf');
    } catch(error) { this.notices.error(error); }
    finally { this.exporting.set(false); }
  }
}

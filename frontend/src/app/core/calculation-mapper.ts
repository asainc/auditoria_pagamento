/** Único adaptador de formulário camelCase para os contratos snake_case. */
import { CalculationParameters_Input, CalculationRequest, CalculationResponse, ExtractionResult, Installment_Input } from './contracts';
import { MANUAL_DEFAULT_PARAMETERS, PARAM_FIELDS, ParameterKey, REQUIRED_PARAMETER_KEYS } from '../calculation/parameter-fields';

export type CalculationOrigin = 'manual' | 'processo';
export type ParameterForm = Partial<Record<ParameterKey, string | number | boolean | null>>;
export type InstallmentForm = Omit<Installment_Input, 'valor_singelo'> & {valor_singelo: string};

export interface WorkspaceDraft {
  calculationOrigin: CalculationOrigin;
  draftId: string;
  numeroProcesso: string;
  installments: InstallmentForm[];
  parameters: ParameterForm;
  humanReviewed: boolean;
  revision: number;
  result: CalculationResponse | null;
  confirmedRequest: CalculationRequest | null;
  extraction: ExtractionResult | null;
  appliedExtractionId: string;
  appliedExtractionAt: string;
  feesOnMoralDamages: boolean;
  automaticCompetence: boolean;
}

/** Gera um identificador técnico local sem usar dados do processo ou da pessoa operadora. */
function newDraftId(): string {
  const randomUuid = globalThis.crypto?.randomUUID?.();
  if (randomUuid) return randomUuid.replace(/-/g, '');
  return `draft_${Date.now()}_${Math.random().toString(36).slice(2, 14)}`;
}

/**
 * Cria um rascunho isolado para processo real ou cálculo manual.
 *
 * O modo manual não usa número de processo. Seus padrões iniciais são um artefato
 * gerado a partir de ``config/calculation_policy.json``; portanto, a tela não possui
 * valores padrão escritos manualmente em outro ponto do código.
 */
export function blankDraft(process: string, origin: CalculationOrigin = 'processo'): WorkspaceDraft {
  return {
    calculationOrigin: origin,
    draftId: newDraftId(),
    numeroProcesso: origin === 'processo' ? process : '',
    installments: [],
    parameters: origin === 'manual' ? {...MANUAL_DEFAULT_PARAMETERS} as ParameterForm : {},
    humanReviewed: false,
    revision: 0,
    result: null,
    confirmedRequest: null,
    extraction: null,
    appliedExtractionId: '',
    appliedExtractionAt: '',
    feesOnMoralDamages: false,
    automaticCompetence: false,
  };
}

/** Valores decimais permanecem texto até a validação Decimal no backend. */
export function decimalText(value: string | number): string {
  const text = String(value).trim().replace(/R\$/g, '').replace(/\s/g, '');
  const canonical = text.includes(',') ? text.replace(/\./g, '').replace(',', '.') : text;
  if (!/^\d+(\.\d+)?$/.test(canonical)) throw new Error('Informe um valor numérico válido, sem sinais ou letras.');
  return canonical;
}

/** Checagens locais orientam preenchimento; a validação oficial ocorre no FastAPI. */
export function missingFields(draft: WorkspaceDraft): string[] {
  const labels = REQUIRED_PARAMETER_KEYS.filter(key => !draft.parameters[key]).map(key => PARAM_FIELDS.find(field => field.key === key)?.label ?? key);
  if (draft.calculationOrigin === 'processo' && !draft.numeroProcesso) labels.push('Processo a calcular');
  if (!draft.installments.some(row => row.data || row.valor_singelo)) labels.push('Ao menos uma parcela');
  if (draft.installments.some(row => (row.data || row.valor_singelo || row.descricao) && (!row.data || !row.valor_singelo))) labels.push('Data e valor de todas as parcelas preenchidas');
  return labels;
}

/** Conversões de nomes e formatos ficam aqui, sem fórmulas do motor. */
export function toCalculationRequest(draft: WorkspaceDraft): CalculationRequest {
  const missing = missingFields(draft);
  if (missing.length) throw new Error('Complete: ' + missing.join('; ') + '.');
  if (!draft.humanReviewed) throw new Error('Confirme a revisão dos dados antes de calcular.');
  const params: ParameterForm = {};
  for (const field of PARAM_FIELDS) {
    const value = draft.parameters[field.key];
    if (value === '' || value === null || value === undefined) continue;
    if (field.type === 'number') params[field.key] = Number(value);
    else if (field.type === 'text' && /taxa$|percentual$|honorarios$|valor$|valor_parcela$/.test(field.key)) params[field.key] = decimalText(String(value));
    else params[field.key] = value;
  }
  return {
    origem_calculo: draft.calculationOrigin,
    numero_processo: draft.calculationOrigin === 'processo' ? draft.numeroProcesso : null,
    parcelas: draft.installments.filter(row => row.data || row.valor_singelo || row.descricao).map(row => ({...row, valor_singelo:decimalText(row.valor_singelo)})),
    parametros: params as CalculationParameters_Input,
    revisao_humana_confirmada:true,
    honorarios_sobre_danos_morais:draft.feesOnMoralDamages,
    competencia_automatica:draft.automaticCompetence,
  };
}

/** Sugestões só preenchem campos vazios e sem conflito; a revisão é sempre invalidada. */
export function applyExtraction(draft: WorkspaceDraft, result: ExtractionResult, job: string, extractedAt = ''): WorkspaceDraft {
  if (draft.calculationOrigin !== 'processo') return draft;
  const parameters = {...draft.parameters};
  for (const field of PARAM_FIELDS) {
    const current = parameters[field.key];
    if (current !== undefined && current !== '' && current !== null) continue;
    const path = `parametros.${field.key}`;
    const consolidated = result.parametros_consolidados?.[field.key];
    if (consolidated !== undefined && consolidated !== null) {
      parameters[field.key] = consolidated;
      continue;
    }
    const chronologyDecision = [...(result.decisoes_cronologicas ?? [])].reverse().find(item => item.campo === path);
    if (chronologyDecision) {
      if (chronologyDecision.valor !== null && chronologyDecision.valor !== undefined) parameters[field.key] = chronologyDecision.valor;
      continue;
    }
    const candidates = result.campos.filter(row => row.campo === path && row.escopo === 'caso_concreto' && row.valor !== null);
    const values = new Set(candidates.map(row => JSON.stringify(row.valor)));
    if (values.size === 1) parameters[field.key] = candidates[0].valor;
  }
  for (const adjustment of result.ajustes_operacionais ?? []) {
    const field = PARAM_FIELDS.find(field => `parametros.${field.key}` === adjustment.campo);
    const chronologyDecision = [...(result.decisoes_cronologicas ?? [])].reverse().find(item => item.campo === adjustment.campo);
    const currentValue = field ? parameters[field.key] : undefined;
    if (field && !chronologyDecision && (currentValue === undefined || currentValue === '' || currentValue === null)) parameters[field.key] = adjustment.valor;
  }
  const hasRows = draft.installments.some(row => row.data || row.valor_singelo);
  return {
    ...draft,
    parameters,
    installments:hasRows ? draft.installments : result.parcelas,
    feesOnMoralDamages:hasRows ? draft.feesOnMoralDamages : Boolean(result.honorarios_sobre_danos_morais),
    automaticCompetence:!draft.parameters.mes_atualizacao && !draft.parameters.ano_atualizacao ? Boolean(result.competencia_automatica) : draft.automaticCompetence,
    humanReviewed:false,
    result:null,
    confirmedRequest:null,
    extraction:result,
    appliedExtractionId:job,
    appliedExtractionAt:extractedAt,
    revision:draft.revision + 1,
  };
}

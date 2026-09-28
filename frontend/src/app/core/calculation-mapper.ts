/** Único adaptador de formulário camelCase para os contratos snake_case. */
import {
  CalculationParameters_Input,
  DamageFinancialCriteria_Input,
  CalculationRequest,
  CalculationVersionDetail,
  ExtractionResult,
  Installment_Input,
  VersionedCalculationResponse,
} from './contracts';
import { DAMAGE_SCOPED_PARAMETER_KEYS, MANUAL_DEFAULT_PARAMETERS, PARAM_FIELDS, PROCESS_DEFAULT_PARAMETERS, ParameterKey, REQUIRED_PARAMETER_KEYS } from '../calculation/parameter-fields';

export type CalculationOrigin = 'manual' | 'processo';
export type ParameterForm = Partial<Record<ParameterKey, string | number | boolean | null>>;
export type DamageTypeKey = 'dano_material' | 'dano_moral';
export type DamageParameterForms = Record<DamageTypeKey, ParameterForm>;
export type InstallmentForm = Omit<Installment_Input, 'valor_singelo'> & {valor_singelo: string};

export interface WorkspaceDraft {
  calculationOrigin: CalculationOrigin;
  draftId: string;
  numeroProcesso: string;
  identificadorCalculo: string;
  installments: InstallmentForm[];
  parameters: ParameterForm;
  damageParameters: DamageParameterForms;
  humanReviewed: boolean;
  revision: number;
  result: VersionedCalculationResponse | null;
  confirmedRequest: CalculationRequest | null;
  calculationId: string;
  calculationVersion: number | null;
  expectedCurrentVersion: number | null;
  loadedFromHistory: boolean;
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

function damageDefaults(origin: CalculationOrigin): DamageParameterForms {
  // Em processo real, defaults operacionais só podem entrar depois da extração:
  // preencher antes faria um padrão bloquear um valor explicitamente documentado.
  const defaults = origin === 'manual' ? MANUAL_DEFAULT_PARAMETERS : {};
  const scoped = Object.fromEntries(DAMAGE_SCOPED_PARAMETER_KEYS
    .filter(key => defaults[key] !== undefined)
    .map(key => [key, defaults[key]])) as ParameterForm;
  return {dano_material:{...scoped}, dano_moral:{...scoped}};
}

function scopedParameters(source: Partial<CalculationParameters_Input>): ParameterForm {
  return Object.fromEntries(DAMAGE_SCOPED_PARAMETER_KEYS
    .filter(key => source[key] !== undefined && source[key] !== null && source[key] !== '')
    .map(key => [key, source[key]])) as ParameterForm;
}

function serializeParameters(source: ParameterForm): ParameterForm {
  const result: ParameterForm = {};
  for (const field of PARAM_FIELDS) {
    const value = source[field.key];
    if (value === '' || value === null || value === undefined) continue;
    if (field.type === 'number') result[field.key] = Number(value);
    else if (field.type === 'text' && /taxa$|percentual$|honorarios$|valor$|valor_parcela$/.test(field.key)) result[field.key] = decimalText(String(value));
    else result[field.key] = value;
  }
  return result;
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
    identificadorCalculo: origin === 'processo' ? process : '',
    installments: [],
    parameters: origin === 'manual' ? {...MANUAL_DEFAULT_PARAMETERS} as ParameterForm : {},
    damageParameters: damageDefaults(origin),
    humanReviewed: false,
    revision: 0,
    result: null,
    confirmedRequest: null,
    calculationId: '',
    calculationVersion: null,
    expectedCurrentVersion: null,
    loadedFromHistory: false,
    extraction: null,
    appliedExtractionId: '',
    appliedExtractionAt: '',
    feesOnMoralDamages: false,
    automaticCompetence: false,
  };
}

/** Reabre uma versão persistida como base editável, preservando seu resultado histórico. */
export function draftFromCalculationVersion(detail: CalculationVersionDetail): WorkspaceDraft {
  const request = detail.requisicao;
  return {
    calculationOrigin:detail.origem_calculo,
    draftId:newDraftId(),
    numeroProcesso:detail.numero_processo ?? '',
    identificadorCalculo:detail.identificador_calculo,
    installments:request.parcelas.map(row => ({
      ...row,
      valor_singelo:String(row.valor_singelo),
    })),
    parameters:{...request.parametros} as ParameterForm,
    damageParameters: request.parametros_por_dano
      ? {
          dano_material:{...request.parametros_por_dano.dano_material} as ParameterForm,
          dano_moral:{...request.parametros_por_dano.dano_moral} as ParameterForm,
        }
      : {
          dano_material:scopedParameters(request.parametros),
          dano_moral:scopedParameters(request.parametros),
        },
    humanReviewed:false,
    revision:0,
    result:{
      ...detail.resultado,
      registro:{
        calculo_id:detail.calculo_id,
        versao:detail.versao,
        versao_base:detail.versao_base ?? null,
        criado_em:detail.criado_em,
        criada:false,
      },
    },
    confirmedRequest:request as CalculationRequest,
    calculationId:detail.calculo_id,
    calculationVersion:detail.versao,
    expectedCurrentVersion:detail.versao_atual,
    loadedFromHistory:true,
    extraction:null,
    appliedExtractionId:'',
    appliedExtractionAt:'',
    feesOnMoralDamages:Boolean(request.honorarios_sobre_danos_morais),
    automaticCompetence:Boolean(request.competencia_automatica),
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
  const labels: string[] = [];
  const activeDamages = new Set(draft.installments
    .filter(row => row.data || row.valor_singelo)
    .map(row => row.verba_tipo)
    .filter((value): value is DamageTypeKey => value === 'dano_material' || value === 'dano_moral'));
  for (const damage of activeDamages) {
    const title = damage === 'dano_material' ? 'Dano Material' : 'Dano Moral';
    for (const key of REQUIRED_PARAMETER_KEYS) {
      const value = DAMAGE_SCOPED_PARAMETER_KEYS.includes(key)
        ? (draft.damageParameters[damage][key] ?? draft.parameters[key])
        : draft.parameters[key];
      if (!value) labels.push(`${PARAM_FIELDS.find(field => field.key === key)?.label ?? key} (${title})`);
    }
  }
  if (draft.calculationOrigin === 'processo' && !draft.numeroProcesso) labels.push('Processo a calcular');
  if (draft.calculationOrigin === 'manual' && !draft.identificadorCalculo.trim()) labels.push('Identificador do cálculo manual');
  if (!draft.installments.some(row => row.data || row.valor_singelo)) labels.push('Ao menos uma parcela');
  if (draft.installments.some(row => (row.data || row.valor_singelo || row.descricao) && (!row.data || !row.valor_singelo))) labels.push('Data e valor de todas as parcelas preenchidas');
  return labels;
}

/** Conversões de nomes e formatos ficam aqui, sem fórmulas do motor. */
export function toCalculationRequest(draft: WorkspaceDraft): CalculationRequest {
  const missing = missingFields(draft);
  if (missing.length) throw new Error('Complete: ' + missing.join('; ') + '.');
  if (!draft.humanReviewed) throw new Error('Confirme a revisão dos dados antes de calcular.');
  const globalParams = serializeParameters(draft.parameters);
  const materialParams = serializeParameters(draft.damageParameters.dano_material);
  const moralParams = serializeParameters(draft.damageParameters.dano_moral);
  // Quando o bloco por tipo de dano não está preenchido, os campos financeiros
  // gerais são usados somente para preencher campos ainda vazios daquele dano.
  for (const key of DAMAGE_SCOPED_PARAMETER_KEYS) {
    const fallbackValue = globalParams[key];
    if (fallbackValue === undefined || fallbackValue === null || fallbackValue === '') continue;
    if (materialParams[key] === undefined || materialParams[key] === null || materialParams[key] === '') materialParams[key] = fallbackValue;
    if (moralParams[key] === undefined || moralParams[key] === null || moralParams[key] === '') moralParams[key] = fallbackValue;
  }
  const hasMaterial = draft.installments.some(row => row.verba_tipo === 'dano_material');
  const fallbackFinancial = hasMaterial ? materialParams : moralParams;
  const params = {...globalParams, ...fallbackFinancial};
  return {
    origem_calculo: draft.calculationOrigin,
    numero_processo: draft.calculationOrigin === 'processo' ? draft.numeroProcesso : null,
    identificador_calculo: draft.calculationOrigin === 'processo' ? draft.numeroProcesso : draft.identificadorCalculo.trim(),
    parcelas: draft.installments.filter(row => row.data || row.valor_singelo || row.descricao).map(row => ({...row, valor_singelo:decimalText(row.valor_singelo)})),
    parametros: params as CalculationParameters_Input,
    parametros_por_dano:{
      dano_material:materialParams as DamageFinancialCriteria_Input,
      dano_moral:moralParams as DamageFinancialCriteria_Input,
    },
    revisao_humana_confirmada:true,
    honorarios_sobre_danos_morais:draft.feesOnMoralDamages,
    competencia_automatica:draft.automaticCompetence,
  };
}

/** Sugestões só preenchem campos vazios e sem conflito; a revisão é sempre invalidada. */
export function applyExtraction(draft: WorkspaceDraft, result: ExtractionResult, job: string, extractedAt = ''): WorkspaceDraft {
  if (draft.calculationOrigin !== 'processo') return draft;
  const parameters = {...draft.parameters};
  const damageParameters: DamageParameterForms = {
    dano_material:{...draft.damageParameters.dano_material},
    dano_moral:{...draft.damageParameters.dano_moral},
  };
  // Quando um rascunho contém somente o valor financeiro geral, esse valor
  // revisado é tratado como valor existente dos dois danos até que cada ramo
  // seja editado/extraído de forma independente.
  for (const key of DAMAGE_SCOPED_PARAMETER_KEYS) {
    const fallbackValue = parameters[key];
    if (fallbackValue === undefined || fallbackValue === null || fallbackValue === '') continue;
    for (const damage of ['dano_material','dano_moral'] as DamageTypeKey[]) {
      const current = damageParameters[damage][key];
      if (current === undefined || current === null || current === '') damageParameters[damage][key] = fallbackValue;
    }
  }
  for (const field of PARAM_FIELDS) {
    const isScoped = DAMAGE_SCOPED_PARAMETER_KEYS.includes(field.key);
    const targets: Array<DamageTypeKey | null> = isScoped ? ['dano_material','dano_moral'] : [null];
    for (const damage of targets) {
      const target = damage ? damageParameters[damage] : parameters;
      const current = target[field.key];
      if (current !== undefined && current !== '' && current !== null) continue;
      const scopedKey = damage ? `${damage}.${String(field.key)}` : String(field.key);
      const scopedPath = damage ? `parametros_por_dano.${damage}.${String(field.key)}` : `parametros.${String(field.key)}`;
      const fallbackPath = `parametros.${String(field.key)}`;
      const consolidated = result.parametros_consolidados?.[scopedKey] ?? result.parametros_consolidados?.[String(field.key)];
      if (consolidated !== undefined && consolidated !== null) {
        target[field.key] = consolidated;
        continue;
      }
      const chronologyDecision = [...(result.decisoes_cronologicas ?? [])].reverse().find(item => item.campo === scopedPath)
        ?? [...(result.decisoes_cronologicas ?? [])].reverse().find(item => item.campo === fallbackPath);
      if (chronologyDecision) {
        if (chronologyDecision.valor !== null && chronologyDecision.valor !== undefined) target[field.key] = chronologyDecision.valor;
        continue;
      }
      const candidates = result.campos.filter(row => (row.campo === scopedPath || row.campo === fallbackPath) && row.escopo === 'caso_concreto' && row.valor !== null);
      const values = new Set(candidates.map(row => JSON.stringify(row.valor)));
      if (values.size === 1) target[field.key] = candidates[0].valor;
    }
  }
  // Mantém o bloco plano apenas como espelho do contrato plano quando ambos os
  // danos continuam iguais. Divergências reais permanecem somente nos ramos.
  for (const key of DAMAGE_SCOPED_PARAMETER_KEYS) {
    const material = damageParameters.dano_material[key];
    const moral = damageParameters.dano_moral[key];
    if (material !== undefined && material !== null && material !== '' && material === moral) parameters[key] = material;
  }
  for (const adjustment of result.ajustes_operacionais ?? []) {
    const field = PARAM_FIELDS.find(field => `parametros.${field.key}` === adjustment.campo);
    if (!field) continue;
    const chronologyDecision = [...(result.decisoes_cronologicas ?? [])].reverse().find(item => item.campo === adjustment.campo);
    if (chronologyDecision) continue;
    if (DAMAGE_SCOPED_PARAMETER_KEYS.includes(field.key)) {
      for (const damage of ['dano_material','dano_moral'] as DamageTypeKey[]) {
        const currentValue = damageParameters[damage][field.key];
        if (currentValue === undefined || currentValue === '' || currentValue === null) damageParameters[damage][field.key] = adjustment.valor;
      }
      const material = damageParameters.dano_material[field.key];
      const moral = damageParameters.dano_moral[field.key];
      if (material === moral && material !== undefined && material !== null && material !== '') parameters[field.key] = material;
      continue;
    }
    const currentValue = parameters[field.key];
    if (currentValue === undefined || currentValue === '' || currentValue === null) parameters[field.key] = adjustment.valor;
  }
  const hasRows = draft.installments.some(row => row.data || row.valor_singelo);
  return {
    ...draft,
    parameters,
    damageParameters,
    installments:hasRows ? draft.installments : result.parcelas,
    feesOnMoralDamages:hasRows ? draft.feesOnMoralDamages : Boolean(result.honorarios_sobre_danos_morais),
    automaticCompetence:(!draft.damageParameters.dano_material.mes_atualizacao && !draft.damageParameters.dano_moral.mes_atualizacao) ? Boolean(result.competencia_automatica) : draft.automaticCompetence,
    humanReviewed:false,
    result:null,
    confirmedRequest:null,
    extraction:result,
    appliedExtractionId:job,
    appliedExtractionAt:extractedAt,
    revision:draft.revision + 1,
  };
}

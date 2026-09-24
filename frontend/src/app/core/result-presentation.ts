/** Rótulos de apresentação: os valores são sempre os retornados pelo motor. */
import { CalculationResponse, IndexOption, SummaryEntry } from './contracts';
import { PARAM_FIELDS } from '../calculation/parameter-fields';
const LABELS: Record<string,string> = {
  total_singelo:'Principal original',total_atualizado:'Principal atualizado',total_juros_compensatorios:'Juros compensatórios',total_juros_moratorios:'Juros moratórios',total_multa:'Multa',honorarios:'Honorários',total_art_523:'Encargos do art. 523',valor_compensacao:'Compensação'
};
export function summaryRows(result: CalculationResponse): SummaryEntry[] {
  return result.resumo.filter(row => Object.hasOwn(LABELS,row.campo)).map(row => ({campo:LABELS[row.campo],valor:row.valor}));
}
/** Apenas seleciona o total já produzido; não recompõe o cálculo no navegador. */
export function finalTotal(result: CalculationResponse): string {
  return result.resumo.find(row => row.campo === 'total_geral')?.valor ?? 'Não disponível';
}


export type DamageCalculationSummary = {
  tipo: 'dano_material'|'dano_moral';
  titulo: string;
  indexador: string;
  periodoCorrecao: string;
  periodoJuros: string;
  juros: string;
};

type MemoryRow = Record<string,string|number|boolean|null>;

function memoryRows(result: CalculationResponse): MemoryRow[] {
  return result.memoria.linhas.map(line => Object.fromEntries(result.memoria.colunas.map((column,index) => [column,line[index] ?? null])) as MemoryRow);
}

function values(rows: MemoryRow[], field: string): string[] {
  return [...new Set(rows.map(row => String(row[field] ?? '').trim()).filter(Boolean))];
}

function brDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : value;
}

function competenceEnd(value: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(value);
  if (!match) return value;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const end = new Date(Date.UTC(year,month,0));
  return `${String(end.getUTCDate()).padStart(2,'0')}/${String(month).padStart(2,'0')}/${year}`;
}

function rangeText(rows: MemoryRow[], startField: string, endField: string, varyingLabel: string, forceVaryingLabel = false): string {
  const starts = values(rows,startField);
  const ends = values(rows,endField);
  const start = !forceVaryingLabel && starts.length === 1 ? brDate(starts[0]) : varyingLabel;
  const end = ends.length === 1 ? competenceEnd(ends[0]) : (ends.length ? ends.map(competenceEnd).join(' / ') : 'Não informado');
  return `${start || 'Não informado'} - ${end || 'Não informado'}`;
}

function indexName(key: string, options: IndexOption[]): string {
  const option = options.find(item => item.chave === key);
  return option?.nome_base || option?.nome || key.replace(/_/g,' ').replace(/\b\w/g,letter => letter.toUpperCase());
}

function interestLabel(result: CalculationResponse, damage: 'dano_material'|'dano_moral'): string {
  const key = damage === 'dano_material' ? 'juros_compensatorios_tipo' : 'juros_moratorios_tipo';
  const rateKey = damage === 'dano_material' ? 'juros_compensatorios_taxa' : 'juros_moratorios_taxa';
  const periodicityKey = damage === 'dano_material' ? 'juros_compensatorios_periodicidade' : 'juros_moratorios_periodicidade';
  const value = String(result.parametros[key] ?? 'sem_juros');
  const field = PARAM_FIELDS.find(item => item.key === key);
  let label = String(field?.options?.find(option => String(option.value) === value)?.label ?? value.replace(/_/g,' '));
  const rate = result.parametros[rateKey];
  if ((value === 'capitalizacao_simples' || value === 'capitalizacao_composta') && rate) {
    const period = result.parametros[periodicityKey];
    const suffix = period === 'diaria' ? 'a.d.' : period === 'anual' ? 'a.a.' : 'a.m.';
    label += ` — ${rate}% ${suffix}`;
  }
  return label;
}

function damageIndex(result: CalculationResponse, damage: 'dano_material'|'dano_moral', options: IndexOption[]): string {
  if (damage === 'dano_material' && result.parametros.duplo_indice_flag) {
    const first = result.parametros.duplo_indice_primeiro_indice;
    const second = result.parametros.duplo_indice_segundo_indice;
    const labels = [first,second].filter((value): value is string => Boolean(value)).map(value => indexName(value,options));
    if (labels.length) return labels.join(' → ');
  }
  return indexName(result.parametros.indice, options);
}

/** Resume somente informações já materializadas pelo motor; não recalcula valores no navegador. */
export function damageCalculationSummaries(result: CalculationResponse, options: IndexOption[]): DamageCalculationSummary[] {
  const rows = memoryRows(result);
  const definitions: Array<{tipo:'dano_material'|'dano_moral';titulo:string;interestStart:string;varyCorrection:string;varyInterest:string}> = [
    {tipo:'dano_material',titulo:'Dano Material',interestStart:'data_inicio_juros_compensatorios_efetiva',varyCorrection:'DATA DE CORREÇÃO DE CADA DANO MATERIAL',varyInterest:'DATA DE JUROS DE CADA DANO MATERIAL'},
    {tipo:'dano_moral',titulo:'Dano Moral',interestStart:'data_inicio_juros_moratorios_efetiva',varyCorrection:'DATA DE CORREÇÃO DE CADA DANO MORAL',varyInterest:'DATA DE JUROS DE CADA DANO MORAL'},
  ];
  return definitions.flatMap(definition => {
    const selected = rows.filter(row => row['verba_tipo'] === definition.tipo);
    if (!selected.length) return [];
    return [{
      tipo:definition.tipo,
      titulo:definition.titulo,
      indexador:damageIndex(result,definition.tipo,options),
      periodoCorrecao:rangeText(selected,'data','competencia_final_correcao',definition.varyCorrection,definition.tipo === 'dano_material'),
      periodoJuros:rangeText(selected,definition.interestStart,'competencia_final_correcao',definition.varyInterest,definition.tipo === 'dano_material'),
      juros:interestLabel(result,definition.tipo),
    }];
  });
}

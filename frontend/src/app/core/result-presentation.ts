/** Rótulos de apresentação: os valores são sempre os retornados pelo motor. */
import { CalculationResponse, SummaryEntry } from './contracts';
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

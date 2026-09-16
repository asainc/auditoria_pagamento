/** Meses/anos mantêm o dia original, limitado ao último dia válido de cada mês. */
export function recurringDate(start: string, position: number, period: string): string {
  const [year, month, day] = start.split('-').map(Number);
  const source = new Date(Date.UTC(year, month - 1, day));
  if (!start || source.toISOString().slice(0,10) !== start) throw new Error('Informe uma data inicial válida.');
  let result: Date;
  if (period === 'mensal' || period === 'anual') {
    const shift = position * (period === 'anual' ? 12 : 1);
    const first = new Date(Date.UTC(year, month - 1 + shift, 1));
    const lastDay = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate();
    result = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), Math.min(day, lastDay)));
  } else { result = new Date(source); result.setUTCDate(day + position * (period === 'semanal' ? 7 : 1)); }
  return result.toISOString().slice(0,10);
}


import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const app = readFileSync(new URL('../src/app/app.component.ts', import.meta.url), 'utf8');
const policy = readFileSync(new URL('../../config/calculation_policy.json', import.meta.url), 'utf8');
const styles = readFileSync(new URL('../src/styles.scss', import.meta.url), 'utf8');
const fields = readFileSync(new URL('../src/app/calculation/parameter-fields.ts', import.meta.url), 'utf8');

test('menu superior exibe apenas cálculo e histórico para Auditoria de Pagamentos', () => {
  assert.match(app, />Cálculo<\/a>/);
  assert.match(app, />Histórico<\/a>/);
  assert.doesNotMatch(app, />Execução em lote<\/a>/);
  assert.doesNotMatch(app, />Índices<\/a>/);
});

test('multa aceita percentual ou valor fixo no catálogo visual', () => {
  const parsed = JSON.parse(policy);
  const valueField = parsed.fields.find((field) => field.key === 'multa_valor');
  const typeField = parsed.fields.find((field) => field.key === 'multa_tipo');
  assert.equal(valueField.label, 'Multa');
  assert.deepEqual(typeField.options.map((option) => option.value), ['', 'percentual', 'fixo']);
  assert.match(fields, /"key":"multa_tipo"/);
  assert.doesNotMatch(fields, /"key":"multa_percentual"/);
});

test('Conferência do cálculo muda somente para a família tipográfica do corpo/aplicação', () => {
  assert.match(styles, /\.page-title-line h1\{font-family:var\(--body\)\}/);
});


test('Resultado usa memória PDF, Histórico e card de versão sem botão auditável', () => {
  const resultPanel = readFileSync(new URL('../src/app/calculation/result-panel.component.ts', import.meta.url), 'utf8');
  assert.match(resultPanel, />Memória PDF<\/button>/);
  assert.match(resultPanel, />Histórico<\/a>/);
  assert.match(resultPanel, /result-version-card/);
  assert.doesNotMatch(resultPanel, /PDF auditável/);
  assert.match(resultPanel, /app-result-calculation-summary/);
});

test('Resumo do Resultado separa dano material e moral sem alterar Histórico', () => {
  const summary = readFileSync(new URL('../src/app/calculation/result-calculation-summary.component.ts', import.meta.url), 'utf8');
  assert.match(summary, /Resumo do cálculo/);
  assert.match(summary, /Indexador:/);
  assert.match(summary, /Período de correção:/);
  assert.match(summary, /Período de incidência de juros:/);
  assert.match(summary, /Juros:/);
});

test('Histórico não oferece PDF auditável e permite abrir qualquer versão ativa para edição', () => {
  const historyPage = readFileSync(new URL('../src/app/history/calculation-history-page.component.ts', import.meta.url), 'utf8');
  const executions = readFileSync(new URL('../src/app/history/history-executions.component.ts', import.meta.url), 'utf8');
  assert.doesNotMatch(historyPage, /PDF auditável/);
  assert.doesNotMatch(executions, />Auditável<\/button>/);
  assert.match(historyPage, /@if\(calculation\.estado==='ativo'\)\{<button[^>]+>Abrir e editar<\/button>\}/);
  assert.doesNotMatch(historyPage, /version\.versao===calculation\.versao_atual\)\{<button[^>]+>Abrir e editar/);
});

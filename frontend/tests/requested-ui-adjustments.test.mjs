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


test('Resultado usa memória PDF, Histórico e card de versão', () => {
  const resultPanel = readFileSync(new URL('../src/app/calculation/result-panel.component.ts', import.meta.url), 'utf8');
  assert.match(resultPanel, />Memória PDF<\/button>/);
  assert.match(resultPanel, />Histórico<\/a>/);
  assert.match(resultPanel, /result-version-card/);
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

test('Histórico permite abrir qualquer versão ativa para edição', () => {
  const historyPage = readFileSync(new URL('../src/app/history/calculation-history-page.component.ts', import.meta.url), 'utf8');
  const executions = readFileSync(new URL('../src/app/history/history-executions.component.ts', import.meta.url), 'utf8');
  assert.match(historyPage, /@if\(calculation\.estado==='ativo'\)\{<button[^>]+>Abrir e editar<\/button>\}/);
  assert.doesNotMatch(historyPage, /version\.versao===calculation\.versao_atual\)\{<button[^>]+>Abrir e editar/);
});


test('Parâmetros separa Dano Material e Dano Moral e incorpora parcelas como primeiro bloco', () => {
  const page = readFileSync(new URL('../src/app/calculation/calculation-page.component.ts', import.meta.url), 'utf8');
  const panel = readFileSync(new URL('../src/app/calculation/parameter-panel.component.ts', import.meta.url), 'utf8');
  assert.doesNotMatch(page, />Parcelas <span>/);
  assert.match(page, /tab = signal<'parametros' \| 'logs' \| 'resultado'>\('parametros'\)/);
  assert.doesNotMatch(page, />Evidências<\/button>/);
  assert.match(panel, />Dano Material<\/button>/);
  assert.match(panel, />Dano Moral<\/button>/);
  assert.match(panel, /'Dano \(Parcelas\)', 'Atualização monetária', 'Juros moratórios', 'Prescrição', 'Honorários', 'Multa', 'Compensação', 'Duplo índice'/);
  assert.match(panel, /<app-installment-editor/);
});

test('danos morais ocultam prescrição, multa e compensação sem alterar honorários globais', () => {
  const parsed = JSON.parse(policy);
  for (const field of parsed.fields.filter((item) => ['Prescrição', 'Multa', 'Compensação'].includes(item.section))) {
    assert.deepEqual(field.damageTypes, ['dano_material'], field.key);
  }
  for (const field of parsed.fields.filter((item) => item.section === 'Honorários')) {
    assert.deepEqual(field.damageTypes, ['dano_material', 'dano_moral'], field.key);
  }
});

test('evidências saem da navegação e ficam contextuais com link para documento e página', () => {
  const page = readFileSync(new URL('../src/app/calculation/calculation-page.component.ts', import.meta.url), 'utf8');
  const panel = readFileSync(new URL('../src/app/calculation/parameter-panel.component.ts', import.meta.url), 'utf8');
  const installments = readFileSync(new URL('../src/app/calculation/installment-editor.component.ts', import.meta.url), 'utf8');
  const info = readFileSync(new URL('../src/app/calculation/evidence-info.component.ts', import.meta.url), 'utf8');
  assert.doesNotMatch(page, /app-evidence-panel|Evidências<\/button>/);
  assert.match(panel, /app-evidence-info/);
  assert.match(installments, /app-evidence-info/);
  assert.match(info, /abrir no documento/);
  assert.match(info, /selectedDocument\.set/);
  assert.match(info, /pdfPage\.set/);
  assert.match(info, /pdfHighlight\.set/);
});

test('visualizador de PDF cede mais largura ao painel direito', () => {
  const layout = readFileSync(new URL('../src/workspace-layout.scss', import.meta.url), 'utf8');
  assert.match(layout, /clamp\(340px,40%,520px\)/);
});

test('frontend usa apenas juros moratórios e uma única memória PDF', () => {
  const resultPresentation = readFileSync(new URL('../src/app/core/result-presentation.ts', import.meta.url), 'utf8');
  const api = readFileSync(new URL('../src/app/core/calculation-api.service.ts', import.meta.url), 'utf8');
  const generatedFields = readFileSync(new URL('../src/app/calculation/parameter-fields.ts', import.meta.url), 'utf8');
  assert.match(resultPresentation, /juros_moratorios/i);
  assert.match(generatedFields, /juros_moratorios/i);
  assert.match(api, /versionPdf/);
  assert.match(api, /executionPdf/);
});


test('valor em dobro fica visível no topo do bloco de dano material', () => {
  const panel = readFileSync(new URL('../src/app/calculation/parameter-panel.component.ts', import.meta.url), 'utf8');
  assert.match(panel, /<strong>Valor em dobro<\/strong>/);
  assert.match(panel, /Aplicar valor em dobro/);
  assert.match(panel, /parameterPath\('valor_dobrado_flag'\)/);
  assert.match(panel, /field.key === 'valor_dobrado_flag'/);
  assert.match(fields, /"key":"valor_dobrado_flag"/);
});

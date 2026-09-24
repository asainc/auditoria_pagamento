/** Contratos estáticos do histórico avançado; não dependem do runtime Angular. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const read = file => fs.readFileSync(path.resolve(__dirname, '../src/app/history', file), 'utf8');
const history = read('calculation-history-page.component.ts');
const filters = read('history-filters.component.ts');
const comparator = read('history-version-comparator.component.ts');
const executions = read('history-executions.component.ts');
const diff = read('history-diff.component.ts');
const api = fs.readFileSync(path.resolve(__dirname, '../src/app/core/calculation-api.service.ts'), 'utf8');

test('histórico usa paginação e filtros enviados ao backend', () => {
  for (const term of ['tamanho_pagina', 'busca', 'estado', 'indice', 'criado_por', 'atualizado_de', 'atualizado_ate', 'ordenacao']) {
    assert.match(filters, new RegExp(term));
  }
  assert.match(history, /pagina:this\.page\(\)/);
  assert.match(api, /\/calculos\/historico/);
});

test('versões são carregadas sob demanda ao expandir o cálculo', () => {
  assert.match(history, /toggle\(calculation/);
  assert.match(history, /loadVersions\(calculation\.calculo_id,1,false\)/);
  assert.match(api, /\/versoes`/);
});

test('comparador VxV consulta endpoint próprio e exibe impacto financeiro', () => {
  assert.match(history, /app-history-version-comparator/);
  assert.match(comparator, /Comparador de versões/);
  assert.match(comparator, /diferenca_total/);
  assert.match(api, /\/comparar/);
});

test('execuções técnicas são componente separado e paginado', () => {
  assert.match(history, /app-history-executions/);
  assert.match(history, /Ver execuções/);
  assert.match(executions, /Carregar mais execuções/);
  assert.match(executions, /result\.itens/);
  assert.match(executions, /result\.total_paginas/);
  assert.match(api, /\/execucoes/);
  assert.match(api, /pagina:page,tamanho_pagina:pageSize/);
  assert.match(api, /executionPdf/);
});

test('estado do cálculo preserva ações de arquivar cancelar e reativar', () => {
  assert.match(history, /Arquivar/);
  assert.match(history, /Cancelar/);
  assert.match(history, /Reativar/);
  assert.match(api, /changeState/);
});

test('diff de parcela exibe valores antes e depois por campo alterado', () => {
  assert.match(history, /app-history-diff/);
  assert.match(diff, /installmentFieldValue\(item\.antes, field\)/);
  assert.match(diff, /installmentFieldValue\(item\.depois, field\)/);
});


test('diff não usa optional chaining redundante no input obrigatório', () => {
  assert.doesNotMatch(diff, /diff\?\.campos/);
  assert.doesNotMatch(diff, /diff\?\.parcelas/);
  assert.match(diff, /diff\.campos/);
  assert.match(diff, /diff\.parcelas/);
});

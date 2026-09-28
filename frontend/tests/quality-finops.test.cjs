const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const read = (relative) => fs.readFileSync(path.join(root, relative), 'utf8');

test('Qualidade IA captura revisão, permite curadoria e exibe FinOps sem tratar estimativa como faturamento', () => {
  const api = read('src/app/core/quality-api.service.ts');
  const page = read('src/app/quality/quality-page.component.ts');
  const review = read('src/app/core/workspace-calculation.store.ts');

  assert.match(api, /qualidade\/revisoes/);
  assert.match(api, /qualidade\/feedback/);
  assert.match(api, /qualidade\/datasets\/snapshot/);
  assert.match(api, /qualidade\/finops/);
  assert.match(review, /captureReview/);
  assert.match(page, /Uma correção humana não vira ground truth automaticamente/);
  assert.match(page, /Tokens estimados são indicadores locais, não faturamento/);
  assert.match(page, /Falhas de API/);
  assert.match(page, /Orçamento mensal/);
});

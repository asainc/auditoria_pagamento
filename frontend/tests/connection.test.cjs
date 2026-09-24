/** Protege o caminho HTTP que falhava no upload entregue anteriormente. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {connectionMessage} = require('../.test-build/core/api-errors.js');

test('runtime e dev-server encaminham /api e suas subrotas ao FastAPI', () => {
  const read = name => JSON.parse(fs.readFileSync(path.resolve(__dirname, '..', name), 'utf8'));
  assert.equal(read('public/app-config.json').apiBaseUrl, '/api/v2');
  assert.equal(read('angular.json').projects['judicial-calculator'].architect.serve.options.proxyConfig, 'proxy.conf.json');
  assert.equal(read('proxy.conf.json')['/api/**'].target, 'http://127.0.0.1:8000');
});
test('falha de conexão orienta inicialização e diferencia acesso e rota incorreta', () => {
  for (const status of [0,500,502,503,504]) assert.match(connectionMessage(status), /start-dev/);
  assert.match(connectionMessage(401), /autenticação/);
  assert.match(connectionMessage(404), /apiBaseUrl/);
});

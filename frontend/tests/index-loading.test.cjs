/** Regressões executam os serviços reais, com transporte e injeção isolados. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

/** Substitui apenas dependências externas para testar o fluxo sem navegador/rede. */
function loadService(file, dependencies) {
  const source = fs.readFileSync(path.join(__dirname, '../src/app/core', file), 'utf8');
  const compiled = ts.transpileModule(source, {compilerOptions:{target:ts.ScriptTarget.ES2022,
    module:ts.ModuleKind.CommonJS, experimentalDecorators:true}}).outputText;
  const exports = {};
  const signal = value => Object.assign(() => value, {set: next => {value = next;}});
  class HttpErrorResponse extends Error {}
  const requireMock = name => {
    if (name === '@angular/core') return {Injectable: () => value => value, signal,
      inject: token => dependencies[token]};
    if (name === 'rxjs') return {firstValueFrom: value => Promise.resolve(value), timeout: () => null};
    if (name === '@angular/common/http') return {HttpClient:'HttpClient', HttpErrorResponse};
    if (name === './api-errors') return {connectionMessage: () => 'Falha de conexão'};
    return new Proxy({}, {get: (_, key) => key});
  };
  vm.runInNewContext(compiled, {exports, require:requireMock, Promise, Error, Map, JSON});
  return exports;
}

/** Resposta simula somente o contrato HTTP público do backend. */
function response(value) { return {then: resolve => resolve(value), pipe() { return this; }}; }

test('backend 2.0.0 é aceito e a verificação chega à configuração de extração', async () => {
  const paths = [];
  const {ConnectionApiService} = loadService('connection-api.service.ts', {
    ApiConfiguration:{baseUrl:'/api'}, HttpClient:{get(url) {
      paths.push(url);
      return response(url.endsWith('/saude') ? {status:'ok',versao_api:'2.0.0'} :
        {provedor:'bradesco_iagen',configurada:false});
    }},
  });
  const service = new ConnectionApiService();
  assert.equal(await service.check(), true);
  assert.equal(service.state(), 'online');
  assert.equal(paths.length, 2);
});

test('versão incompatível continua bloqueada', async () => {
  const {ConnectionApiService} = loadService('connection-api.service.ts', {
    ApiConfiguration:{baseUrl:'/api'}, HttpClient:{get: () => response({status:'ok',versao_api:'99.0.0'})},
  });
  assert.equal(await new ConnectionApiService().check(), false);
});

/** Mantém o estado mínimo necessário à inicialização real da área de trabalho. */
function workspace(processResult, indexResult) {
  const cell = value => Object.assign(() => value, {set: next => {value = next;}});
  const state = {processes:cell([]), indices:cell([])};
  const errors = [];
  const {WorkspaceStore} = loadService('workspace.store.ts', {
    WorkspaceStateStore:state, WorkspaceAuditStore:{}, WorkspaceExtractionStore:{},
    WorkspaceCalculationStore:{}, ConnectionApiService:{check:async () => true},
    Notifications:{error: error => errors.push(error)},
    DocumentApiService:{processes:processResult}, IndexApiService:{options:indexResult},
  });
  return {store:new WorkspaceStore(), state, errors};
}

test('falha de processos não elimina o catálogo retornado pela API', async () => {
  const catalog = [{chave:'ipca_ibge',nome:'IPCA (IBGE)'}];
  const {store,state,errors} = workspace(() => Promise.reject(new Error('Falha simulada')),
    () => Promise.resolve(catalog));
  await store.initialize();
  assert.equal(state.indices(), catalog);
  assert.equal(errors.length, 1);
  assert.equal(store.loadingCatalog(), false);
});

test('falha de índices permite recuperação na tentativa seguinte', async () => {
  let attempt = 0;
  const catalog = [{chave:'sem_correcao',nome:'Sem correção'}];
  const {store,state} = workspace(() => Promise.resolve([]), () => ++attempt === 1 ?
    Promise.reject(new Error('Falha simulada')) : Promise.resolve(catalog));
  await store.initialize();
  assert.equal(state.indices().length, 0);
  await store.initialize();
  assert.equal(state.indices(), catalog);
});

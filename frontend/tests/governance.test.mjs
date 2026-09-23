/** Testes locais da árvore de artefatos e do bloqueio de homologação, sem rede. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {collectArtifacts, evaluateApprovals, packageNameFromPath, toCsv} from '../scripts/governance-core.mjs';

const lockPath = new URL('../package-lock.json', import.meta.url);
const lock = existsSync(lockPath) ? JSON.parse(readFileSync(lockPath, 'utf8')) : null;
const lockOnly = lock ? test : test.skip;

test('identifica pacotes com escopo e aninhados', () => {
  assert.equal(packageNameFromPath('node_modules/@angular/core'), '@angular/core');
  assert.equal(packageNameFromPath('node_modules/a/node_modules/@scope/b'), '@scope/b');
});
lockOnly('todos os artefatos exigidos têm hash sha512 e versão', () => {
  const artifacts = collectArtifacts(lock);
  assert.ok(artifacts.length > 0);
  assert.ok(artifacts.every(row => row.integrity.startsWith('sha512-') && row.version));
  assert.equal(new Set(artifacts.map(row => `${row.name}@${row.version}`)).size, artifacts.length);
});
lockOnly('rejeita ausência de aprovação e divergência de integridade', () => {
  const artifact = collectArtifacts(lock)[0];
  assert.equal(evaluateApprovals([artifact], {schema_version:1, packages:[]})[0].status, 'PENDENTE');
  assert.equal(evaluateApprovals([artifact], {schema_version:1, packages:[{name:artifact.name,version:artifact.version,integrity:'sha512-falso',status:'approved'}]})[0].status, 'INTEGRIDADE_DIVERGENTE');
});
lockOnly('aceita somente aprovação explícita por versão e integridade', () => {
  const artifact = collectArtifacts(lock)[0];
  const status = evaluateApprovals([artifact], {schema_version:1, packages:[{name:artifact.name,version:artifact.version,integrity:artifact.integrity,status:'approved'}]});
  assert.equal(status[0].status, 'APROVADO');
});
lockOnly('interpreta restrições de sistemas e arquitetura', () => {
  const windows = collectArtifacts(lock, {platform:'win32',architecture:'x64'});
  const linux = collectArtifacts(lock, {platform:'linux',architecture:'x64'});
  assert.ok(windows.some(row => row.name === '@esbuild/win32-x64'));
  assert.ok(!linux.some(row => row.name === '@esbuild/win32-x64'));
});
test('CSV escapa fórmulas e aspas', () => {
  const csv = toCsv([{name:'=1+1',version:'"quoted"'}], ['name','version']);
  assert.ok(csv.includes("'=1+1"));
  assert.ok(csv.includes('""quoted""'));
});

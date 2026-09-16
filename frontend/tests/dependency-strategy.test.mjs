import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {resolve, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateCorporateRegistry} from '../scripts/validate-nexus-registry.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'));

test('Angular permanece exatamente em 21.2.19', () => {
  for (const [name, version] of Object.entries({...manifest.dependencies, ...manifest.devDependencies})) {
    if (name.startsWith('@angular/')) assert.equal(version, '21.2.19', name);
  }
});

test('baseline não usa overrides, forks ou dependências locais diretas', () => {
  assert.equal(manifest.overrides, undefined);
  for (const [name, spec] of Object.entries({...manifest.dependencies, ...manifest.devDependencies})) {
    assert.match(spec, /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/, `${name}: versão deve ser exata`);
  }
});

test('baseline fixa Node.js 22.12.x e npm 10.9.x', () => {
  assert.equal(manifest.engines.node, '22.12.x');
  assert.equal(manifest.engines.npm, '10.9.x');
  assert.equal(manifest.packageManager, 'npm@10.9.0');
});

test('registry corporativo esperado é aceito e npm público é recusado', () => {
  const accepted = validateCorporateRegistry('https://nexusrepository.bradesco.com.br:8443/repository/escp-npm-central/');
  assert.match(accepted, /^https:\/\/nexusrepository\.bradesco\.com\.br:8443\//);
  assert.throws(() => validateCorporateRegistry('https://registry.npmjs.org/'));
});

test('quando existe lockfile, ele não referencia registry npm público', () => {
  const lockPath = resolve(root, 'package-lock.json');
  if (!existsSync(lockPath)) return;
  const raw = readFileSync(lockPath, 'utf8');
  assert.doesNotMatch(raw, /registry\.npmjs\.org|registry\.yarnpkg\.com/i);
});

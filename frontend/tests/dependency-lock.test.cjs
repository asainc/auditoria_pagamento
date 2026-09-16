/** Testes de regressão dos pacotes oficiais; não dependem de downloads. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync, existsSync} = require('node:fs');
const {join} = require('node:path');
const {spawnSync} = require('node:child_process');

const root = join(__dirname, '..');
const readJson = (file) => JSON.parse(readFileSync(join(root, file), 'utf8'));
const manifest = readJson('package.json');
const packages = readJson('package-lock.json').packages;

test('sem vendor/fork e sem URLs locais ou dependências Git no lockfile', () => {
  assert.equal(existsSync(join(root, 'vendor')), false);
  assert.equal(manifest.devDependencies.browserslist, undefined);
  for (const [path, pkg] of Object.entries(packages)) {
    if (!path) continue;
    assert.match(pkg.resolved, /^https:\/\/registry\.npmjs\.org\//, path);
    assert.match(pkg.integrity, /^sha512-/, path);
  }
});

test('Angular 21.2.21 conserva Browserslist oficial com updater oficial 1.3.3', () => {
  assert.equal(manifest.devDependencies['@angular/build'], '21.2.21');
  assert.equal(packages['node_modules/browserslist'].version, '4.28.9');
  assert.equal(packages['node_modules/update-browserslist-db'].version, '1.3.3');
  assert.equal(manifest.overrides['update-browserslist-db'], '1.3.3');
});

test('negotiator oficial 1.0.0 remove dependência de content-type sem violar faixa ^1.0.0', () => {
  assert.equal(manifest.overrides.negotiator, '1.0.0');
  assert.equal(packages['node_modules/negotiator'].version, '1.0.0');
  assert.equal(packages['node_modules/negotiator'].dependencies?.['content-type'], undefined);
  assert.equal(packages['node_modules/accepts'].dependencies.negotiator, '^1.0.0');
  assert.equal(packages['node_modules/make-fetch-happen'].dependencies.negotiator, '^1.0.0');
  assert.equal(packages['node_modules/negotiator/node_modules/content-type'], undefined);
});

test('content-type 2.0.0 oficial só é usado em consumidores que aceitam ^2.0.0', () => {
  assert.equal(packages['node_modules/content-type'].version, '1.0.5');
  for (const consumer of ['body-parser', 'type-is']) {
    assert.equal(packages[`node_modules/${consumer}`].dependencies['content-type'], '^2.0.0');
    assert.equal(manifest.overrides[consumer]['content-type'], '2.0.0');
    assert.equal(packages[`node_modules/${consumer}/node_modules/content-type`].version, '2.0.0');
  }
});

test('versões que tiveram 403 não reapareceram em nenhum nível do lockfile', () => {
  for (const [path, pkg] of Object.entries(packages)) {
    if (path.endsWith('/update-browserslist-db')) assert.notEqual(pkg.version, '1.3.2', path);
    if (path.endsWith('/content-type')) assert.notEqual(pkg.version, '2.1.0', path);
  }
});

test('script de validação independente de rede confirma o contrato npm', () => {
  const run = spawnSync(process.execPath, [join(root, 'scripts/validate-dependency-lock.mjs')], {
    cwd: root, encoding: 'utf8', timeout: 10000,
  });
  assert.equal(run.status, 0, run.stderr);
  assert.match(run.stdout, /sem forks/);
});

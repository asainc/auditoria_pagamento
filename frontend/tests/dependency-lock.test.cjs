/**
 * Testes de regressão do contrato npm offline, sem instalar dependências,
 * efetuar downloads ou utilizar dados do ambiente corporativo.
 */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const {createHash} = require('node:crypto');
const {spawnSync} = require('node:child_process');

const root = join(__dirname, '..');
const readJson = (name) => JSON.parse(readFileSync(join(root, name), 'utf8'));
const lock = readJson('package-lock.json');
const manifest = readJson('package.json');

test('nenhum pacote na árvore npm depende do atualizador bloqueado', () => {
  for (const [path, pkg] of Object.entries(lock.packages)) {
    assert.ok(!path.split('/').includes('update-browserslist-db'), path);
    for (const field of ['dependencies', 'optionalDependencies', 'peerDependencies']) {
      assert.equal(pkg[field]?.['update-browserslist-db'], undefined, `${path}: ${field}`);
    }
  }
});

test('tarball de origem local possui integridade e versão coerentes', () => {
  const relativePath = 'vendor/browserslist-no-updater-4.28.1.tgz';
  const pkg = lock.packages['node_modules/browserslist'];
  const sha512 = createHash('sha512').update(readFileSync(join(root, relativePath))).digest('base64');
  assert.equal(pkg.integrity, `sha512-${sha512}`);
  assert.equal(pkg.resolved, `file:${relativePath}`);
  assert.equal(pkg.version, '4.28.1');
  assert.equal(manifest.overrides.browserslist, '$browserslist');
  assert.equal(manifest.devDependencies.browserslist, `file:${relativePath}`);
});

test('o código do fork mantém a API pública e não importa o atualizador', () => {
  const fork = readJson('vendor/browserslist-no-updater/package.json');
  assert.equal(fork.dependencies['update-browserslist-db'], undefined);
  const cli = readFileSync(join(root, 'vendor/browserslist-no-updater/cli.js'), 'utf8');
  assert.doesNotMatch(cli, /require\(['"]update-browserslist-db['"]\)/);
  assert.match(cli, /--update-db/);
  assert.equal(fork.bin.browserslist, 'cli.js');
  assert.equal(fork.types, './index.d.ts');
});

test('verificação de dependências funciona sem rede', () => {
  const result = spawnSync(process.execPath, [join(root, 'scripts/validate-dependency-lock.mjs')], {
    cwd: root, encoding: 'utf8', timeout: 10000,
  });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /update-browserslist-db ausente/);
});

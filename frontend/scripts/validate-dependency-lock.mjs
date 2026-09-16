/**
 * Confere a origem oficial e as versões compatíveis do lockfile npm, sem rede.
 *
 * Entradas: package.json e package-lock.json versionados no frontend.
 * Saída: mensagem de confirmação ou erro explícito com o pacote envolvido.
 * Motivo: impedir que alterações futuras reintroduzam forks, versões recusadas
 * pelo Nexus ou overrides incompatíveis com os consumidores conhecidos.
 */
import {readFileSync} from 'node:fs';

/** Carrega JSON local e preserva o erro original de leitura/parse. */
const readJson = (file) => JSON.parse(readFileSync(new URL(file, import.meta.url), 'utf8'));
const manifest = readJson('../package.json');
const lock = readJson('../package-lock.json');
const packages = lock.packages ?? {};

/** Interrompe a validação na primeira divergência, com diagnóstico acionável. */
function assert(condition, message) {
  if (!condition) throw new Error(message);
}

/** Verifica coerência exata das dependências diretas que o npm ci exige. */
function validateRoot() {
  const root = packages[''];
  assert(lock.lockfileVersion === 3 && root, 'Lockfile v3 ou pacote raiz ausente.');
  for (const section of ['dependencies', 'devDependencies']) {
    assert(JSON.stringify(root[section] ?? {}) === JSON.stringify(manifest[section] ?? {}),
      `${section}: package.json e package-lock.json divergentes.`);
  }
  assert(!manifest.devDependencies?.browserslist, 'Remova o Browserslist direto; o Angular já declara essa dependência.');
  assert(JSON.stringify(manifest.overrides ?? {}) === JSON.stringify({
    'update-browserslist-db': '1.3.3',
    negotiator: '1.0.0',
    'body-parser': {'content-type': '2.0.0'},
    'type-is': {'content-type': '2.0.0'},
  }), 'Overrides diferentes dos aprovados para análise técnica; revise a árvore e a documentação.');
}

/** Confirma que todos os pacotes resolvidos vêm da origem npm oficial, sem caminhos locais. */
function validateOfficialSources() {
  for (const [path, pkg] of Object.entries(packages)) {
    if (!path) continue;
    // Pacotes opcionais podem não registrar resolved quando são apenas links.
    assert(typeof pkg.resolved === 'string' &&
      pkg.resolved.startsWith('https://registry.npmjs.org/') &&
      typeof pkg.integrity === 'string' && pkg.integrity.startsWith('sha512-'),
      `${path}: origem npm oficial ou integridade SHA-512 não verificada no lockfile.`);
  }
}

/** Confere as substituições sem forçar uma dependência abaixo da faixa exigida. */
function validateAlternatives() {
  const lookup = (name) => packages[`node_modules/${name}`];
  const browserslist = lookup('browserslist');
  const updater = lookup('update-browserslist-db');
  const negotiator = lookup('negotiator');
  assert(browserslist?.version === '4.28.9' &&
    browserslist.dependencies?.['update-browserslist-db'] === '^1.3.2' &&
    updater?.version === '1.3.3',
  'Browserslist oficial deve resolver update-browserslist-db@1.3.3 (não 1.3.2).');
  assert(negotiator?.version === '1.0.0' && !negotiator.dependencies?.['content-type'],
    'negotiator@1.0.0 oficial não deve solicitar content-type@2.1.0.');
  assert(lookup('accepts')?.dependencies?.negotiator === '^1.0.0' &&
    lookup('make-fetch-happen')?.dependencies?.negotiator === '^1.0.0',
    'Revisar consumidores: negotiator@1.0.0 precisa satisfazer suas faixas declaradas.');
  assert(lookup('body-parser')?.dependencies?.['content-type'] === '^2.0.0' &&
    lookup('type-is')?.dependencies?.['content-type'] === '^2.0.0',
    'Revisar consumidores: content-type@2.0.0 precisa satisfazer suas faixas declaradas.');
  assert(lookup('content-type')?.version === '1.0.5',
    'content-type@1.0.5 é necessário para os consumidores 1.x.');
  for (const consumer of ['body-parser', 'type-is']) {
    assert(packages[`node_modules/${consumer}/node_modules/content-type`]?.version === '2.0.0',
      `content-type@2.0.0 ausente no consumidor ${consumer}.`);
  }
  assert(!packages['node_modules/negotiator/node_modules/content-type'],
    'negotiator@1.0.0 não deve instalar content-type próprio.');
  for (const [path, pkg] of Object.entries(packages)) {
    if (path.endsWith('/update-browserslist-db')) {
      assert(pkg.version !== '1.3.2', `${path}: versão 1.3.2 recusada.`);
    }
    if (path.endsWith('/content-type')) {
      assert(pkg.version !== '2.1.0', `${path}: versão 2.1.0 recusada.`);
    }
  }
}

validateRoot();
validateOfficialSources();
validateAlternatives();
console.log(`OK: ${Object.keys(packages).length - 1} pacotes oficiais no lockfile; sem forks; bloqueios 1.3.2/2.1.0 ausentes; overrides compatíveis.`);

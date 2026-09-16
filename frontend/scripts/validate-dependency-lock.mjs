/**
 * Verifica se a instalação utiliza uma cópia local auditável do Browserslist,
 * sem depender do pacote de atualização bloqueado pelo repositório corporativo.
 *
 * Entradas: package.json, package-lock.json, manifesto do fork e tarball local.
 * Saída: confirmação ou erro explícito; não acessa rede nem credenciais.
 */
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';

const readJson = (path) => JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf8'));
const manifest = readJson('../package.json');
const lock = readJson('../package-lock.json');
const fork = readJson('../vendor/browserslist-no-updater/package.json');
const packagePath = 'file:vendor/browserslist-no-updater-4.28.1.tgz';
const browserPackage = lock.packages?.['node_modules/browserslist'];
const blockedPackage = 'update-browserslist-db';

// A dependência direta faz o npm resolver o caminho relativo a partir da raiz
// do frontend, inclusive quando o Browserslist é solicitado pelo Angular/Babel.
if (manifest.devDependencies?.browserslist !== packagePath ||
    manifest.overrides?.browserslist !== '$browserslist' ||
    lock.packages?.['']?.devDependencies?.browserslist !== packagePath) {
  throw new Error('O Browserslist local não está fixado de forma coerente no manifesto e lockfile.');
}

// A integridade criptográfica do tarball é conferida antes de utilizar o npm.
const bytes = readFileSync(new URL('../vendor/browserslist-no-updater-4.28.1.tgz', import.meta.url));
const actualIntegrity = `sha512-${createHash('sha512').update(bytes).digest('base64')}`;
if (!browserPackage || browserPackage.version !== '4.28.1' ||
    browserPackage.resolved !== packagePath || browserPackage.integrity !== actualIntegrity ||
    fork.name !== 'browserslist' || fork.version !== browserPackage.version) {
  throw new Error('Origem, versão ou integridade do Browserslist local não correspondem ao lockfile.');
}

// A árvore completa não pode solicitar o pacote desautorizado, nem em
// subdiretórios ou dependências opcionais.
for (const [path, dependency] of Object.entries(lock.packages ?? {})) {
  const names = [
    ...Object.keys(dependency.dependencies ?? {}),
    ...Object.keys(dependency.optionalDependencies ?? {}),
    ...Object.keys(dependency.peerDependencies ?? {}),
  ];
  if (path.split('/').includes(blockedPackage) || names.includes(blockedPackage)) {
    throw new Error(`Dependência não permitida encontrada em ${path || 'raiz'}.`);
  }
}
if (fork.dependencies?.[blockedPackage]) {
  throw new Error('O manifesto da cópia local ainda solicita o atualizador.');
}
const cli = readFileSync(new URL('../vendor/browserslist-no-updater/cli.js', import.meta.url), 'utf8');
if (/require\(['"]update-browserslist-db['"]\)/.test(cli)) {
  throw new Error('O CLI local ainda importa o atualizador.');
}
console.log('OK: Browserslist local verificado (SHA-512); update-browserslist-db ausente da árvore npm.');

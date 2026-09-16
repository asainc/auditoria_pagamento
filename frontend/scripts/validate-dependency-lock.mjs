/**
 * Valida um package-lock.json criado pelo Nexus corporativo.
 *
 * Entradas: package.json, package-lock.json e registry npm configurado.
 * Saída: confirmação ou lista de violações bloqueantes.
 * Motivo: garantir reprodutibilidade sem forks, arquivos locais, Git ou registry público.
 */
import {readFileSync, existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, resolve} from 'node:path';
import {validateCorporateRegistry, readConfiguredRegistry} from './validate-nexus-registry.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const lockPath = resolve(root, 'package-lock.json');
if (!existsSync(lockPath)) throw new Error('package-lock.json ausente. Execute npm run nexus:lock no ambiente corporativo.');

const manifest = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'));
const lock = JSON.parse(readFileSync(lockPath, 'utf8'));
const packages = lock.packages ?? {};
const corporateRegistry = new URL(validateCorporateRegistry(readConfiguredRegistry()));

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(lock.lockfileVersion === 3, 'package-lock.json deve usar lockfileVersion 3.');
assert(packages[''], 'Pacote raiz ausente no package-lock.json.');
for (const section of ['dependencies', 'devDependencies']) {
  assert(JSON.stringify(packages[''][section] ?? {}) === JSON.stringify(manifest[section] ?? {}),
    `${section}: package.json e package-lock.json divergentes.`);
}
assert(!manifest.overrides, 'Overrides não são permitidos no baseline Nexus-first.');

let registryPackages = 0;
for (const [path, pkg] of Object.entries(packages)) {
  if (!path) continue;
  assert(!pkg.link, `${path}: links locais não são permitidos.`);
  if (pkg.resolved) {
    assert(!/^(file:|git\+|git:|github:|https?:\/\/github\.com)/i.test(pkg.resolved),
      `${path}: origem local/Git não permitida: ${pkg.resolved}`);
    const resolved = new URL(pkg.resolved);
    assert(resolved.hostname.toLowerCase() === corporateRegistry.hostname.toLowerCase(),
      `${path}: artefato fora do Nexus corporativo: ${resolved.hostname}`);
    assert(resolved.pathname.startsWith(corporateRegistry.pathname),
      `${path}: artefato fora do repositório corporativo esperado: ${resolved.pathname}`);
    registryPackages += 1;
  }
  if (pkg.integrity) {
    assert(pkg.integrity.startsWith('sha512-'), `${path}: integridade SHA-512 ausente.`);
  }
}
assert(registryPackages > 0, 'Nenhum artefato do Nexus foi encontrado no lockfile.');
console.log(`Lockfile corporativo validado: ${registryPackages} artefatos resolvidos exclusivamente pelo Nexus.`);

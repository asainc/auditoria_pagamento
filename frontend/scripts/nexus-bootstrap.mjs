/**
 * Gera o package-lock.json diretamente pelo Nexus e, opcionalmente, executa npm ci.
 *
 * Entradas: package.json, ambiente Node/npm e registry corporativo já configurado.
 * Saídas: package-lock.json resolvido pelo Nexus e instalação determinística opcional.
 * Motivo: não distribuir um lockfile produzido contra registry público ou outra versão
 * do Angular. A árvore corporativa nasce do próprio Nexus e depois é versionada.
 */
import {execFileSync} from 'node:child_process';
import {existsSync, readFileSync, rmSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, resolve} from 'node:path';
import {validateCorporateRegistry, readConfiguredRegistry} from './validate-nexus-registry.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const frontendDir = resolve(here, '..');
const lockPath = resolve(frontendDir, 'package-lock.json');
const npmExecutable = process.platform === 'win32' ? 'npm.cmd' : 'npm';

function runNodeScript(script) {
  execFileSync(process.execPath, [resolve(here, script)], {cwd: frontendDir, stdio: 'inherit'});
}

function runNpm(args) {
  execFileSync(npmExecutable, args, {cwd: frontendDir, stdio: 'inherit', timeout: 10 * 60 * 1000});
}

function validateLockExists() {
  if (!existsSync(lockPath)) throw new Error('package-lock.json não foi criado pelo Nexus.');
  const lock = JSON.parse(readFileSync(lockPath, 'utf8'));
  if (lock.lockfileVersion !== 3) throw new Error('O lockfile corporativo deve usar lockfileVersion 3.');
}

runNodeScript('validate-environment.mjs');
const registry = validateCorporateRegistry(readConfiguredRegistry());
console.log(`Resolução restrita ao Nexus: ${registry}`);

if (process.argv.includes('--lock-only')) {
  rmSync(lockPath, {force: true});
  runNpm([
    'install', '--package-lock-only', '--ignore-scripts', '--strict-peer-deps',
    '--no-audit', '--no-fund', `--registry=${registry}`,
  ]);
  validateLockExists();
  runNodeScript('validate-dependency-lock.mjs');
  console.log('Lockfile corporativo gerado. Revise/versione o package-lock.json antes de usar npm ci em outros ambientes.');
} else if (process.argv.includes('--install')) {
  if (!existsSync(lockPath)) {
    throw new Error('package-lock.json ausente. Execute primeiro: npm run nexus:lock');
  }
  runNodeScript('validate-dependency-lock.mjs');
  execFileSync(process.execPath, [resolve(here, 'nexus-preflight.mjs'), '--artifacts'], {
    cwd: frontendDir, stdio: 'inherit', timeout: 20 * 60 * 1000,
  });
  runNpm(['ci', '--strict-peer-deps', '--no-audit', '--no-fund', `--registry=${registry}`]);
  console.log('Instalação concluída após validar todos os artefatos exigidos no Nexus.');
} else {
  throw new Error('Use --lock-only ou --install.');
}

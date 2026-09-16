/**
 * Garante que a resolução npm ocorrerá somente pelo Nexus corporativo.
 *
 * Entrada: `npm config get registry` ou NPM_CONFIG_REGISTRY.
 * Saída: URL normalizada do registry corporativo ou erro antes da instalação.
 * Motivo: impedir fallback acidental para registry público ou origem não homologada.
 */
import {execFileSync} from 'node:child_process';

const DEFAULT_HOST = 'nexusrepository.bradesco.com.br';
const DEFAULT_REPOSITORY_FRAGMENT = '/repository/escp-npm-central/';

export function normalizeRegistry(value) {
  const url = new URL(String(value).trim());
  if (url.protocol !== 'https:') throw new Error('O registry npm corporativo deve usar HTTPS.');
  if (!url.pathname.endsWith('/')) url.pathname += '/';
  return url;
}

export function validateCorporateRegistry(value, {
  expectedHost = process.env.CORPORATE_NPM_HOST || DEFAULT_HOST,
  expectedPath = process.env.CORPORATE_NPM_PATH || DEFAULT_REPOSITORY_FRAGMENT,
} = {}) {
  const url = normalizeRegistry(value);
  if (url.hostname.toLowerCase() !== expectedHost.toLowerCase()) {
    throw new Error(`Registry não corporativo: ${url.origin}. Esperado host ${expectedHost}.`);
  }
  if (expectedPath && !url.pathname.includes(expectedPath)) {
    throw new Error(`Registry corporativo inesperado: ${url.pathname}. Esperado caminho contendo ${expectedPath}.`);
  }
  return url.toString();
}

export function readConfiguredRegistry() {
  if (process.env.NPM_CONFIG_REGISTRY?.trim()) return process.env.NPM_CONFIG_REGISTRY.trim();
  const npmExecutable = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  return execFileSync(npmExecutable, ['config', 'get', 'registry'], {encoding: 'utf8', timeout: 30000}).trim();
}

if (import.meta.url === `file://${process.argv[1]?.replaceAll('\\', '/')}` || process.argv[1]?.endsWith('validate-nexus-registry.mjs')) {
  const registry = validateCorporateRegistry(readConfiguredRegistry());
  console.log(`Registry corporativo validado: ${registry}`);
}

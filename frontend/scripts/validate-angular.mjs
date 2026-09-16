/** Verifica o baseline oficial do Angular antes de build ou geração do lockfile. */
import {readFileSync} from 'node:fs';

const EXPECTED_ANGULAR = '21.2.19';
const manifest = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
const angularPackages = Object.entries({...manifest.dependencies, ...manifest.devDependencies})
  .filter(([name]) => name.startsWith('@angular/'));

for (const [name, version] of angularPackages) {
  if (version !== EXPECTED_ANGULAR) {
    throw new Error(`${name}: esperado ${EXPECTED_ANGULAR}, encontrado ${version}.`);
  }
}
if (manifest.overrides) throw new Error('Não use overrides no baseline corporativo; resolva a árvore pelo Nexus.');
if (manifest.packageManager !== 'npm@10.9.0') throw new Error('packageManager deve permanecer npm@10.9.0.');
console.log(`Baseline Angular validado: ${EXPECTED_ANGULAR}.`);

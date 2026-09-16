/** Verifica a versão exigida antes do build e, opcionalmente, sua publicação. */
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
const manifest = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
for (const [name, version] of Object.entries({...manifest.dependencies, ...manifest.devDependencies})) {
  if (!name.startsWith('@angular/') && !name.startsWith('@angular-devkit/')) continue;
  if (version !== '21.2.21') throw new Error(`${name}: versão diferente de 21.2.21.`);
  if (process.argv.includes('--registry')) {
    const result = execFileSync(process.platform === 'win32' ? 'npm.cmd' : 'npm', ['view', `${name}@${version}`, 'version', '--json'], {encoding:'utf8', timeout:60000});
    if (JSON.parse(result) !== version) throw new Error(`${name}: versão ausente no registry.`);
    console.log(`${name}@${version}: publicado`);
  }
}
console.log('Versões Angular coerentes: 21.2.21.');

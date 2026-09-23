/** Testes estáticos dos pacotes oficiais compatíveis com o Windows corporativo. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateCorporateRegistry} from '../scripts/validate-nexus-registry.mjs';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const manifest=JSON.parse(readFileSync(resolve(root,'package.json'),'utf8'));

test('Angular alinhado ao baseline oficial 21.2.19',()=>{
  for(const [name,version] of Object.entries({...manifest.dependencies,...manifest.devDependencies})) {
    if(name.startsWith('@angular/')) assert.equal(version,'21.2.19',name);
  }
});
test('dependências diretas oficiais e com versões exatas',()=>{
  for(const [name,version] of Object.entries({...manifest.dependencies,...manifest.devDependencies})) {
    assert.match(version,/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/,name);
  }
});
test('Rollup e binário Windows declarados na mesma versão',()=>{
  assert.equal(manifest.devDependencies['@rollup/rollup-win32-x64-msvc'],'4.60.1');
  assert.equal(manifest.overrides.rollup,manifest.devDependencies['@rollup/rollup-win32-x64-msvc']);
});
test('overrides explícitos correspondem às versões informadas pelo usuário',()=>{
  assert.deepEqual(manifest.overrides,{rollup:'4.60.1',chokidar:{readdirp:'4.1.2'},postcss:'8.5.25'});
});
test('Node e npm fixados como baseline da instalação corporativa',()=>{
  assert.equal(manifest.engines.node,'22.12.x');
  assert.equal(manifest.engines.npm,'10.9.x');
  assert.equal(manifest.packageManager,'npm@10.9.0');
});
test('aceita caminho informado do Nexus e rejeita URL duplicada e pública',()=>{
  assert.match(validateCorporateRegistry('https://nexusrepository.bradesco.com.br:8443/repository/jurianl-npm-central/'),/jurianl-npm-central/);
  assert.match(validateCorporateRegistry('https://nexusrepository.bradesco.com.br:8443/repository/escp-npm-central/'),/escp-npm-central/);
  assert.throws(()=>validateCorporateRegistry('https://registry.npmjs.org/'));
  assert.throws(()=>validateCorporateRegistry('https://nexusrepository.bradesco.com.br:8443/repository/jurianl-npm-central/repository/jurianl-npm-central/'));
  assert.throws(()=>validateCorporateRegistry('https://user:password@nexusrepository.bradesco.com.br/repository/jurianl-npm-central/'));
});
test('não reescreve URLs que já apontam para o Nexus',()=>{
  const npmrc=readFileSync(resolve(root,'.npmrc'),'utf8');
  assert.match(npmrc,/replace-registry-host=never/);
});
test('quando presente, lockfile não referencia registry público',()=>{
  const path=resolve(root,'package-lock.json');
  if(!existsSync(path)) return;
  assert.doesNotMatch(readFileSync(path,'utf8'),/registry\.npmjs\.org|registry\.yarnpkg\.com/i);
});

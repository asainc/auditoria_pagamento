/** Testes sem dependências externas da identificação e integridade dos downloads locais. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {gzipSync} from 'node:zlib';
import {readTarballIdentity,tarballIntegrity,lockIdentityMap} from '../scripts/local-tarballs-core.mjs';

/** Produz fixture sintética de pacote npm, sem dados ou artefatos reais. */
function makeTarball(name,version){
  const json=Buffer.from(JSON.stringify({name,version}),'utf8');
  const header=Buffer.alloc(512);
  header.write('package/package.json',0,'utf8');
  header.write('0000644\0',100,'ascii');
  header.write('0000000\0',108,'ascii');
  header.write('0000000\0',116,'ascii');
  header.write(json.length.toString(8).padStart(11,'0')+'\0',124,'ascii');
  header.write('00000000000\0',136,'ascii');
  header.write('        ',148,'ascii');
  header.write('0',156,'ascii');
  header.write('ustar\0',257,'ascii');
  header.write('00',263,'ascii');
  const checksum=header.reduce((sum,value)=>sum+value,0);
  header.write(checksum.toString(8).padStart(6,'0')+'\0 ',148,'ascii');
  const padded=Buffer.alloc(Math.ceil(json.length/512)*512);
  json.copy(padded);
  return gzipSync(Buffer.concat([header,padded,Buffer.alloc(1024)]));
}
test('identifica pacote scoped pela metadata do tarball, não pelo nome externo',()=>{
  const buffer=makeTarball('@rollup/rollup-win32-x64-msvc','4.60.1');
  assert.deepEqual(readTarballIdentity(buffer),{name:'@rollup/rollup-win32-x64-msvc',version:'4.60.1'});
  assert.match(tarballIntegrity(buffer),/^sha512-/);
});
test('rejeita gzip corrompido e manifesto sem formato npm',()=>{
  assert.throws(()=>readTarballIdentity(Buffer.from('arquivo invalido')));
  assert.throws(()=>readTarballIdentity(makeTarball('not valid package','4.60.1')));
});
test('correspondência por nome, versão e hash do lockfile',()=>{
  const buf=makeTarball('rollup','4.60.1');
  const lock={packages:{'node_modules/rollup':{version:'4.60.1',integrity:tarballIntegrity(buf)}}};
  const lookup=lockIdentityMap(lock);
  assert.equal(lookup.get('rollup@4.60.1').integrity,tarballIntegrity(buf));
  assert.notEqual(lookup.get('rollup@4.60.1').integrity,tarballIntegrity(makeTarball('rollup','4.61.0')));
});

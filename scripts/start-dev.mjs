/** Inicia as duas camadas e confirma a API antes de abrir o servidor Angular. */
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { createServer } from 'node:net';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const windows = process.platform === 'win32';
const python = process.env.BACKEND_PYTHON || join(root, '.venv', windows ? 'Scripts/python.exe' : 'bin/python');
const angular = join(root, 'frontend/node_modules/@angular/cli/bin/ng.js');
const children = [];
let closing = false;

/** Só encerra os processos criados por este iniciador, incluindo seus filhos. */
function stop(code = 0) {
  if (closing) return;
  closing = true;
  for (const child of children) {
    if (!child.pid || child.exitCode !== null) continue;
    if (windows) spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], {stdio:'ignore'});
    else { try { process.kill(-child.pid, 'SIGTERM'); } catch { /* Já encerrado. */ } }
  }
  process.exitCode = code;
}
process.on('SIGINT', () => stop());
process.on('SIGTERM', () => stop());

function launch(command, args, cwd, frontend = false) {
  const environment = {...process.env};
  if (frontend) for (const key of ['BRADESCO_AUTHORIZATION_TOKEN','BRADESCO_IDENTIFICADOR','BRADESCO_SENHA','GATEWAY_TOKEN']) delete environment[key];
  const child = spawn(command, args, {cwd, stdio:'inherit', detached:!windows, env:environment});
  children.push(child);
  child.on('error', () => { console.error('Não foi possível iniciar um serviço. Confira as dependências no README.'); stop(1); });
  child.on('exit', code => { if (!closing) { console.error('Um dos serviços encerrou. Confira a mensagem no terminal acima.'); stop(code || 1); } });
  return child;
}

async function requireFreePort(port) {
  await new Promise((accept, reject) => {
    const server = createServer();
    server.once('error', () => reject(new Error(`Porta ${port} já está ocupada. Encerre a instância anterior antes de iniciar a versão corrigida.`)));
    server.listen(port, '127.0.0.1', () => server.close(accept));
  });
}

try {
  if (!existsSync(python)) throw new Error('Ambiente Python não encontrado. Instale as dependências seguindo o README.');
  if (!existsSync(angular)) throw new Error('Dependências Angular ausentes. Execute npm install na pasta frontend.');
  await requireFreePort(8000); await requireFreePort(4200);
  launch(python, ['-m','uvicorn','backend.principal:aplicacao','--host','127.0.0.1','--port','8000','--workers','1','--no-access-log'], root);
  let ready = false;
  const deadline = Date.now() + 20000;
  while (!closing && Date.now() < deadline) {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/saude', {signal:AbortSignal.timeout(1000)});
      const value = await response.json();
      if (response.ok && value.status === 'ok' && value.versao_api === '1.0.0') { ready = true; break; }
    } catch { /* O Uvicorn ainda pode estar iniciando. */ }
    await delay(250);
  }
  if (!ready) throw new Error('O backend não iniciou. Confira a instalação Python e a configuração do .env.');
  if (!closing) {
    launch(process.execPath, [angular,'serve','--host','127.0.0.1','--port','4200'], join(root,'frontend'), true);
    console.log('API confirmada. Aguarde o build do Angular e abra http://127.0.0.1:4200. Ctrl+C encerra as duas camadas.');
  }
} catch (error) {
  console.error(error.message); stop(1);
}

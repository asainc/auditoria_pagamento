# Guia de manutenção

## 1. Antes de alterar código

Identifique em qual camada a mudança pertence:

- tela, interação ou estado visual: `frontend/`;
- formato HTTP: `backend/contracts/`;
- endpoint: `backend/routers/`;
- coordenação de um caso de uso: `backend/services/`;
- acesso a banco: `backend/repositories/` e `backend/persistence/`;
- fórmula financeira: `src/judicial_calc/`;
- regra configurável: `config/`;
- extração documental: `prompts/` e serviços de extração.

Evite resolver um problema na camada errada. Exemplo: não copie uma fórmula para o Angular só para mostrar um total antecipadamente; solicite ao backend ou use o resultado calculado.

## 2. Como adicionar uma configuração

1. Determine se o valor é segredo.
2. Se for segredo, crie variável de ambiente e adicione apenas a chave vazia ao `.env.example`.
3. Se não for segredo e for operacional, adicione ao JSON apropriado.
4. Adicione o campo tipado ao modelo que carrega a configuração.
5. Valide tipo e intervalo na fronteira.
6. Escreva teste para valor válido e inválido.
7. Documente a finalidade em `docs/CONFIGURACAO.md`.

## 3. Como alterar uma fórmula

1. Crie ou escolha um cenário sintético que represente a regra.
2. Registre entrada e saída esperadas no teste.
3. Faça a alteração no módulo específico do motor.
4. Execute os testes focados.
5. Execute a suíte completa.
6. Regere `docs/motor_sha256.json`.
7. Registre a decisão e a justificativa em `docs/DECISOES.md` quando a mudança alterar arquitetura, responsabilidade ou regra importante.
8. Solicite validação jurídica quando a mudança envolver interpretação de critério jurídico, e não apenas correção técnica já definida.

## 4. Como adicionar endpoint

1. Crie contratos de entrada/saída em `backend/contracts/`.
2. Implemente a coordenação em um serviço.
3. Se houver banco, use um repositório do domínio correspondente.
4. Deixe o router somente com validação HTTP, chamada do serviço e resposta.
5. Adicione teste de integração da rota.
6. Regere os contratos se a API pública mudar.

## 5. Como alterar extração por IA

1. Identifique a tarefa específica em `prompts/`.
2. Não misture fórmula financeira com instrução de extração.
3. Preserve evidência, documento e página quando disponíveis.
4. Execute avaliação com dados sintéticos ou conjuntos devidamente governados.
5. Compare precisão antes/depois; não aceite melhoria apenas por impressão visual.
6. Mudanças de modelo, prompt ou conjunto de exemplos devem ser registradas com justificativa e resultado de avaliação.

## 6. Como investigar um warning de recarga

O backend deve ser iniciado por `scripts/run_backend.py`. Se aparecer novamente uma mensagem citando `frontend/node_modules`:

1. confirme que o comando usado é `python scripts/run_backend.py --reload` ou um dos wrappers `start-backend-dev`;
2. confira `config/runtime.json`;
3. confirme que `frontend` não está em `reload.directories`;
4. confirme que `frontend/node_modules` está em `reload.exclude_paths`;
5. execute `pytest -q tests/test_runtime_bootstrap.py`.

Não corrija adicionando exceções aleatórias ao código do frontend; o problema pertence à configuração do watcher do backend.

## 7. Checklist de qualidade

Antes de entregar uma alteração:

- entradas são validadas;
- falhas geram mensagem explícita;
- não há credenciais ou dados pessoais reais no diff;
- não há código morto evidente;
- comentários explicam o motivo, não apenas repetem a linha;
- funções críticas têm entrada e saída tipadas;
- logs não expõem conteúdo sensível;
- testes unitários/integrados foram executados;
- documentação gerada foi atualizada;
- decisão técnica relevante foi registrada com justificativa.

## 8. Comandos de validação

```bash
PYTHONPATH="src:." pytest -q
python scripts/validate_architecture.py
python -m compileall -q backend src scripts
python scripts/generate_parameter_catalog.py
python scripts/generate_parameter_docs.py
python scripts/generate_code_reference.py
python scripts/generate_engine_manifest.py
node --check scripts/start-dev.mjs
```

Quando as dependências do Angular estiverem instaladas:

```bash
cd frontend
npm test
npm run build
```

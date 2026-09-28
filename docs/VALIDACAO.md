# Validação do projeto

## 1. Objetivo

A validação deve comprovar que o código compila, que as fronteiras arquiteturais continuam respeitadas e que cenários financeiros já cobertos pela suíte permanecem estáveis. Números de testes executados não ficam gravados neste documento, porque mudam com a evolução da suíte; o resultado válido é o produzido pela execução atual ou pela CI.

## 2. Backend e motor

Na raiz do projeto:

```bash
PYTHONPATH="src:." pytest -q
python scripts/validate_architecture.py
python -m compileall -q backend src scripts
```

A suíte cobre, entre outros pontos:

- normalização de parâmetros;
- cálculo e cenários de referência;
- dano material e dano moral;
- persistência e auditoria;
- contratos HTTP;
- extração documental com dublês, sem enviar documentos reais;
- atualização e resiliência de índices;
- regras do bootstrap e escopo do WatchFiles.

## 3. Frontend

Depois de instalar as dependências pelo processo autorizado:

```bash
cd frontend
npm test
npm run build
```

Também é possível validar a sintaxe do iniciador conjunto sem instalar o Angular:

```bash
node --check scripts/start-dev.mjs
```

## 4. Artefatos gerados

Quando código, política ou contratos mudarem, regere os artefatos aplicáveis:

```bash
python scripts/generate_parameter_catalog.py
python scripts/generate_parameter_docs.py
python scripts/generate_code_reference.py
python scripts/generate_module_guide.py
python scripts/generate_engine_manifest.py
```

Se a API pública mudar, execute também o gerador de contratos conforme o procedimento do projeto.

## 5. Integração corporativa

Testes automatizados não substituem uma validação no ambiente corporativo. A conectividade real do `text_generator`, o deployment configurado, a autorização e a rede precisam ser verificados no ambiente autorizado. Comece com conteúdo sintético; não use documentos reais apenas para diagnóstico de infraestrutura.

## 6. Gate de segurança

Antes da entrega confirme que:

- não há segredos versionados;
- não há dados reais de produção não anonimizados em fixtures ou documentação;
- logs não reproduzem conteúdo integral dos documentos;
- critérios jurídicos alterados foram encaminhados para validação do responsável aplicável;
- o manifesto do motor corresponde ao código atual.

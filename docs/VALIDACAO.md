# Validação e qualidade

## 1. Princípio

A validação separa estabilidade financeira de qualidade da extração. O resultado do motor é comparado com cenários de referência; a extração é avaliada por regras determinísticas e, quando houver benchmark rotulado validado, por métricas de campo. Inspeção visual isolada não é tratada como evidência de qualidade.

## 2. Testes Python

Execute:

```bash
python -m pytest
```

A suíte inclui validação de contratos, documentos, política operacional, integração do cálculo, jobs, arquitetura, orientação de erros, cronologia e motor.

### Golden master do motor

`tests/test_engine_golden_master.py` lê `tests/fixtures/golden_calculations.json`. Os resultados esperados ficam versionados em `tests/fixtures/golden_calculations.json` e representam o comportamento financeiro de referência da suíte.

A fixture cobre, sem rede:

- cálculo base sem juros;
- juros simples + multa + honorários + Art. 523;
- compensação percentual + evento financeiro;
- duplo índice com faixas sem correção.

Divergência entre o resultado e a fixture deve ser investigada; a referência só deve ser atualizada quando a regra financeira correspondente estiver formalmente validada.

### Regressão da extração

`tests/test_extraction_evaluation.py` testa `ChronologyReducer` e requisitos críticos dos prompts com exemplos sintéticos. Ele não chama LLM e não deve ser citado como acurácia do modelo.

### Benchmark de extração rotulado

`evals/` contém apenas casos sintéticos de regressão. Para um benchmark de qualidade do LLM, use um conjunto autorizado e revisado pelo time jurídico e compare predições offline com:

```bash
python scripts/evaluate_extraction.py --gold <gabarito.json> --predictions <predicoes.json>
```

A taxa de correspondência exata só deve ser reportada quando o gabarito tiver validação adequada.

### OpenAI

`tests/test_openai_provider.py` e `tests/test_openai_schema.py` usam o SDK real com transporte HTTP simulado. Eles verificam serialização, Structured Outputs e diagnóstico de falhas sem enviar documento para a internet. O ambiente de teste precisa instalar as dependências do `requirements.lock`.

## 3. Frontend

Na primeira preparação dentro do ambiente corporativo:

```powershell
cd frontend
npm run env:check
npm run nexus:check
npm run nexus:lock
npm run install:corporate
npm test
npm run build
```

Depois que o lockfile corporativo estiver versionado, `npm run install:corporate` executa `npm ci` de forma determinística. `npm test` compila os módulos usados nos testes e valida contratos/mappers.

## 4. Artefatos gerados

Para garantir coerência entre contratos, política e artefatos derivados:

```bash
python scripts/generate_contracts.py
python scripts/generate_parameter_catalog.py
python scripts/generate_parameter_docs.py
python scripts/generate_code_reference.py
```

Testes devem falhar se o catálogo visual divergir dos campos Pydantic.

## 5. Integridade do motor

`docs/motor_sha256.json` contém SHA-256 dos arquivos Python de `src/`. O teste de arquitetura compara o manifesto com o conteúdo real. O manifesto é regenerado a partir do source validado e deve corresponder exatamente aos arquivos Python do motor.

## 6. Validações antes de produção

Além de testes automatizados, ainda são necessários conforme o ambiente:

- benchmark rotulado da extração por IA;
- validação jurídica dos padrões e regras de cronologia;
- avaliação de segurança do gateway/cabeçalhos de identidade;
- definição de retenção e base legal com DPO/Compliance;
- teste de carga e concorrência;
- verificação da atualidade/cobertura das séries de índices;
- teste de recuperação de backup e de atualização de planilhas.

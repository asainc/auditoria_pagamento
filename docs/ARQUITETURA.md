# Arquitetura do projeto

## 1. Objetivo arquitetural

O sistema separa quatro responsabilidades que não devem se misturar:

1. **interação**: Angular apresenta documentos, formulários, evidências e resultados;
2. **aplicação**: FastAPI valida contratos, coordena jobs, auditoria e políticas;
3. **extração**: o componente de IA transforma documentos em fatos/evidências, sem executar fórmulas;
4. **cálculo**: `judicial_calc` executa fórmulas determinísticas sobre entradas já revisadas.

A regra de projeto é: **LLM extrai e classifica; Python consolida e calcula; humano confirma**.

## 2. Diagrama de componentes

```text
┌──────────────────────── Angular 21.2.19 ────────────────────────┐
│ App shell │ WorkspaceStore │ editores │ PDF │ logs │ resultado │
└──────────────────────────────┬──────────────────────────────────┘
                               │ /api/v2
┌──────────────────────────────▼──────────────────────────────────┐
│ FastAPI                                                         │
│ routers → contratos Pydantic → serviços                         │
│                                                                 │
│ DocumentService ──→ ExtractionService ──→ ChronologyReducer     │
│                                  │              │                │
│                                  └→ OperationalPolicy           │
│                                                                 │
│ RevisionAuditService                  CalculationService         │
│                                              │                  │
│                                         EngineFacade             │
└──────────────────────────────────────────────┬──────────────────┘
                                               │
┌──────────────────────────────────────────────▼──────────────────┐
│ judicial_calc                                                     │
│ normalização de parâmetros │ índices │ juros │ cálculo │ PDF     │
└──────────────────────────────────────────────────────────────────┘
```

## 3. Fonte única dos parâmetros

`config/calculation_policy.json` é a fonte de verdade para:

- chaves de parâmetros;
- rótulos e agrupamentos da interface;
- opções de campos `select`;
- campos mínimos;
- defaults do modo `manual`;
- defaults de `processo`.

`backend/calculation_policy.py` lê e valida essa política. O frontend não mantém uma segunda lista manual: `scripts/generate_parameter_catalog.py` produz `frontend/src/app/calculation/parameter-fields.ts` a partir do JSON. `scripts/generate_parameter_docs.py` produz `docs/PARAMETROS.md` da mesma fonte.

## 4. Frontend Angular

### `app.component.ts`

Responsável pelo shell da plataforma e navegação entre Auditoria de Pagamentos, BJN e AI Ready. Não contém regras financeiras.

### `calculation-page.component.ts`

Compõe a tela de conferência. Alterna Parcelas, Evidências, Parâmetros, Logs e Resultado.

### `workspace.store.ts`

Mantém rascunhos por processo e um rascunho manual isolado. Responsabilidades principais:

- seleção de processo/documento;
- polling da extração;
- invalidação de revisão após edição;
- envio de alterações humanas à auditoria;
- confirmação humana;
- execução e exportação do cálculo.

O modo manual usa `calculationOrigin='manual'` e `numeroProcesso=''` apenas no estado visual; na API ele vira `origem_calculo='manual'` e `numero_processo=null`.

### `calculation-mapper.ts`

É a fronteira de conversão entre formulário e contrato HTTP. Ele não reproduz fórmulas do backend.

## 5. FastAPI e contratos

`backend/principal.py` cria a aplicação e registra a API canônica sob `/api/v2`. Os prefixos `/api` e `/api/v1` permanecem somente como aliases transitórios e são ocultos do OpenAPI. `X-API-Version` e o health check expõem o contrato `2.0.0`.

Os contratos Pydantic foram divididos por domínio em `backend/contracts/`. `backend/models.py` permanece somente como fachada retrocompatível. Dinheiro/taxas são validados como `Decimal` internamente, enquanto a interface envia texto decimal para preservar precisão.

Rotas são deliberadamente finas:

- `documents.py`: upload/listagem/leitura;
- `extractions.py`: configuração, start, status e resultado;
- `calculations.py`: competência, política, cálculo, honorários e PDF;
- `indices.py`: catálogo/status/atualização;
- `batches.py`: importação e execução em lote;
- `audit.py`: trilha de alteração humana dos parâmetros.

## 5.1 Persistência por domínio

A composição de persistência é explícita em `backend/container.py`. O código novo usa repositórios especializados:

- `DocumentRepository`: documentos/processos;
- `ExtractionRepository`: fila, status e resultados de extração;
- `AuditRepository`: trilha de auditoria;
- `CalculationRepository`: cadastro, versões, execuções e artefatos;
- `IndexRepository`: estado operacional dos índices.

`backend/repository.py` não contém SQL e existe apenas para compatibilidade com integrações anteriores. Conexão, transações, schema e migrações ficam em `backend/persistence/`.

O agregado de cálculo é persistido como `Cálculo → Versão → Execução → Artefato`. Versões são estados funcionais imutáveis; execuções registram cada materialização técnica; PDFs são artefatos ligados à execução por SHA-256. Constraints/triggers do SQLite reforçam identidade, hashes válidos e imutabilidade.

## 6. Extração documental

`backend/services/extraction.py` orquestra dez tarefas especializadas. O contexto comum é montado uma única vez por `PromptContextBuilder` com:

- regras universais de `_base.md`;
- cronologia de anexos;
- catálogo real de índices;
- schema dos parâmetros.

Cada chamada recebe esse contexto mais o prompt especializado. A resposta externa passa por modelos de transporte estritos (`extraction_wire.py`) e depois pela validação interna.

`ChronologyReducer` consolida somente `parametros.*`. As evidências brutas permanecem intactas. A consolidação utiliza `natureza`, `efeito`, sequência e página; não escolhe por “documento mais recente” quando o tipo de evidência não permite essa conclusão.

`OperationalPolicy` roda depois da consolidação e adiciona defaults rastreáveis apenas quando necessário.

## 7. Auditoria de revisão humana

`RevisionAuditService` e a tabela SQLite `parameter_changes` mantêm eventos imutáveis de edição. Cada evento pode conter:

- origem do cálculo;
- processo ou id do rascunho manual;
- campo alterado;
- valor anterior e novo;
- id da extração associada;
- valor/origem automáticos conhecidos pelo servidor;
- data/hora;
- ator técnico.

Em ambiente não local, o backend não grava o subject recebido em claro; deriva um identificador por SHA-256. O frontend mantém eventos não persistidos na fila e força o envio antes de revisão, troca de processo e cálculo, evitando prosseguir quando a trilha obrigatória não pôde ser registrada. A política de retenção e o contrato com o gateway devem ser validados na implantação.

## 8. Motor de cálculo

`backend/services/engine.py` é a fachada do backend para `judicial_calc`.

Dentro do motor:

- `services/calculation_parameters.py` normaliza e valida parâmetros, inclusive prescrição, compensação, valor em dobro, duplo índice e Art. 523;
- `services/calculation_prescription.py` aplica o corte temporal das parcelas;
- `services/calculation_penalties.py` concentra multa, rateio monetário e Art. 523;
- `services/calculation_adjustments.py` aplica compensação;
- `services/calculation_summary.py` agrega honorários e totais do resumo;
- `services/calculation_service.py` permanece como orquestrador de tabelas, correção, juros e composição das etapas;
- módulos `indices/`, `interest/` e `data_sources/` implementam estratégias especializadas.

As fronteiras acima isolam responsabilidades sem duplicar fórmulas financeiras. `tests/test_engine_golden_master.py` congela cenários completos e verifica que o resultado numérico permanece compatível com a referência esperada.

## 9. Erros estruturados

O motor usa `CalculationValidationError(code, fields, message)` para validações de combinação de parâmetros. `backend/services/engine_guidance.py` utiliza `fields` e o catálogo central para orientar o operador. Ele não faz regex em texto de exceção e não ecoa valores recebidos.

Na fronteira HTTP, falhas esperadas usam `ServiceError` com `code`, `message`, `fields`, `retryable` e `request_id`. O frontend decide comportamento pelo código estável e usa a mensagem somente para apresentação; valores de entrada não são devolvidos no envelope de erro.

## 10. Interfaces públicas do pacote de cálculo

A extração por IA é responsabilidade da camada de aplicação e não faz parte de `judicial_calc`. O pacote expõe `judicial_calc.calculator`, `judicial_calc.cli` e as funções públicas de `judicial_calc.__init__` como interfaces determinísticas de cálculo/exportação. O processamento em lote da aplicação web é coordenado por `backend/services/batches.py`, reutilizando a mesma fachada de cálculo.

## 11. Reprodutibilidade

- dependências Python: `requirements.lock`;
- dependências Angular: `package-lock.json` gerado no Nexus corporativo com Node.js 22.12.0/npm 10.9.0 e depois versionado;
- contratos gerados: `docs/openapi.json` e `contracts.ts`;
- integridade do motor: `docs/motor_sha256.json`;
- hash canônico da entrada e hash da política retornados em cada cálculo;
- política de cálculo versionada: `calculation_policy.json`;
- fixtures golden-master: `tests/fixtures/golden_calculations.json`.

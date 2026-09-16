# Plataforma Jurídica — Auditoria de Pagamentos

Aplicação web para extração assistida, revisão e cálculo de débitos judiciais. O projeto separa apresentação, políticas operacionais, extração documental e fórmulas financeiras para que cada decisão seja rastreável e testável.

A arquitetura principal é:

```text
Angular 21.2.19
      ↓ HTTP/REST
FastAPI + serviços de aplicação
      ↓
EngineFacade
      ↓
judicial_calc (motor determinístico)
```

A IA não executa fórmulas. Ela extrai fatos e relações dos documentos, associa evidências e classifica o efeito cronológico de decisões. O Python consolida a linha do tempo, aplica políticas operacionais explícitas e somente então apresenta os dados para revisão humana. O cálculo final exige confirmação humana.

## Modos de cálculo

O contrato possui `origem_calculo` explícita:

| Origem | `numero_processo` | Uso |
| --- | --- | --- |
| `manual` | `null` | teste com parcelas e parâmetros digitados manualmente |
| `processo` | obrigatório | cálculo apoiado por documentos e extração |

Não existe número de processo sentinela para representar cálculo manual.

## Padrões operacionais

A fonte única de verdade é `config/calculation_policy.json`. Ela define metadados dos parâmetros, campos obrigatórios e padrões por origem.

| Contexto | Índice ausente | Juros moratórios ausentes | Juros compensatórios ausentes | Art. 523 ausente |
| --- | --- | --- | --- | --- |
| Manual | sem padrão | `sem_juros` | `sem_juros` | `nao_aplicar` |
| Processo real | `tjsp_inpc_ipca15_lei_14905` | `taxa_legal_12_aa_6_aa` | `taxa_legal_12_aa_6_aa` | `nao_aplicar` |

Em processo real, um valor documental consolidado prevalece sobre o padrão. A aplicação de padrão é registrada separadamente em `ajustes_operacionais`; ela não vira citação fictícia.

## Estrutura do repositório

```text
backend/                         API FastAPI e serviços de aplicação
  calculation_policy.py         leitura do catálogo central
  routers/                       endpoints HTTP
  services/                      orquestração, IA, cronologia, cálculo e auditoria
config/
  calculation_policy.json       fonte de verdade de parâmetros/defaults
  app.settings.json             configuração não secreta da aplicação
  extraction_tasks.json         orçamento máximo de saída por tarefa de IA
  model_pricing.json             tarifas verificadas usadas na estimativa de custo
frontend/                        Angular 21.2.19
prompts/
  _base.md                       regras comuns de extração
  00_...09_*.md                  tarefas especializadas
src/judicial_calc/               motor financeiro determinístico
scripts/                         geração, validação e inicialização
  generate_contracts.py          OpenAPI + contratos TypeScript
  generate_parameter_catalog.py  catálogo Angular a partir da política central
  generate_parameter_docs.py     documentação dos parâmetros
  generate_code_reference.py     referência técnica a partir do próprio source
  evaluate_extraction.py         comparação offline contra benchmark rotulado
tests/                           testes Python
docs/                            documentação técnica
examples/                        exemplos sintéticos de lote
```

A extração documental pertence à camada `backend/services/extraction.py` e seus colaboradores. O pacote `judicial_calc` contém somente componentes determinísticos de cálculo, índices, juros, exportação e suas fachadas públicas.

## Fluxo resumido de processo real

```text
PDFs
 ↓
DocumentService
 ↓
ExtractionService
 ↓
PromptContextBuilder + prompts especializados
 ↓
validação de evidências
 ↓
ChronologyReducer
 ↓
OperationalPolicy
 ↓
revisão/edição humana + trilha de auditoria
 ↓
CalculationRequest
 ↓
CalculationService → EngineFacade → judicial_calc.calcular_debitos
 ↓
memória + resumo + hashes técnicos
```

A ordem documental é derivada de `<processo>_<sequencia>.pdf`, sendo a maior sequência o anexo mais recente. Recência não é, por si só, reforma: cada evidência recebe `natureza` e `efeito`, e a consolidação determinística só altera o estado quando há suporte estruturado suficiente. Conflitos não resolvidos permanecem para revisão humana.

> **Dependências corporativas do frontend:** esta variante usa estratégia **Nexus-first**. O repositório distribuído não traz um `package-lock.json` resolvido no registry público. O lock deve ser criado uma única vez dentro do ambiente corporativo com `npm run nexus:lock`; depois, ele deve ser revisado e versionado para que `npm ci` seja determinístico.

## Instalação local

### Backend

Pré-requisito recomendado: Python 3.12.

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .\.venv\Scripts\Activate.ps1 # Windows
python -m pip install -r requirements.txt
cp .env.example .env
```

Configure `API_TOKEN`/`OPENAI_API_KEY` somente no ambiente ou `.env`. Nunca versione credenciais.

Inicie:

```bash
python -m uvicorn backend.principal:aplicacao --reload --host 127.0.0.1 --port 8000
```

### Frontend

Baseline de reprodução: **Node.js 22.12.0 + npm 10.9.0 + Angular 21.2.19**. O projeto usa apenas dependências diretas oficiais com versões exatas e não possui `overrides`, forks, `file:`, Git ou pacotes vendorizados.

O primeiro lockfile deve nascer no próprio Nexus corporativo:

```powershell
cd frontend
npm run env:check
npm run nexus:check
npm run nexus:lock
```

Revise e versione o `frontend/package-lock.json` gerado. A partir daí, as instalações reproduzíveis usam:

```powershell
npm run install:corporate
npm run build
npm start
```

O script `nexus:lock` executa somente a resolução de metadados (`--package-lock-only --ignore-scripts`), valida a origem dos artefatos e não envia credenciais para logs. A instalação real ocorre depois com `npm ci`.

O proxy de desenvolvimento encaminha `/api` ao FastAPI.

## Artefatos gerados

Quando alterar contratos ou política central, regenere os artefatos antes de testar:

```bash
python scripts/generate_contracts.py
python scripts/generate_parameter_catalog.py
python scripts/generate_parameter_docs.py
python scripts/generate_code_reference.py
python scripts/generate_engine_manifest.py
```

`frontend/src/app/core/contracts.ts`, `frontend/src/app/calculation/parameter-fields.ts`, `docs/openapi.json`, `docs/PARAMETROS.md` e `docs/REFERENCIA_CODIGO.md` não devem divergir de suas fontes.

## Visibilidade de tokens e custo da IA

Cada chamada de extração registra o consumo real informado pela API: tokens de entrada, entrada em cache, saída, total, duração e custo estimado. O custo usa `config/model_pricing.json`; se o modelo configurado não tiver uma tarifa verificada nesse catálogo, os tokens continuam disponíveis e o custo fica explicitamente como não calculado.

Os limites de saída são definidos por tarefa em `config/extraction_tasks.json`. O objetivo é reduzir payload e saída excessiva sem fundir domínios de extração que precisam de avaliação independente. Veja `docs/IA_CUSTOS_E_OTIMIZACAO.md`.

## Testes

```bash
python -m pytest
cd frontend && npm test
```

`tests/test_engine_golden_master.py` verifica estabilidade numérica do motor em cenários congelados. `tests/test_extraction_evaluation.py` cobre regras determinísticas de cronologia e requisitos dos prompts; ele não é uma métrica de acurácia do LLM. `evals/` contém a estrutura de avaliação sintética e o contrato para benchmarks rotulados.

## Documentação

- `docs/ARQUITETURA.md`: fronteiras e responsabilidades.
- `docs/FLUXO_CALCULO.md`: percurso completo da entrada até a memória final.
- `docs/EXTRACAO_IA.md`: prompts, evidências e consolidação cronológica.
- `docs/IA_CUSTOS_E_OTIMIZACAO.md`: tokens, custos, cache e decisões de otimização de payload.
- `docs/FLUXO_EXTRACAO_VISUAL.md`: diagramas Mermaid e exemplo visual de uma evidência até a revisão.
- `docs/PARAMETROS.md`: catálogo gerado e padrões por origem.
- `docs/OPERACAO.md`: configuração, execução, persistência e segurança.
- `docs/DECISOES.md`: decisões técnicas vigentes e justificativas.
- `docs/MODEL_CARD.md`: escopo, limites e governança do componente de IA.
- `docs/VALIDACAO.md`: estratégia e comandos de validação.
- `docs/REFERENCIA_CODIGO.md`: referência gerada de classes e funções Python.

## Segurança, privacidade e governança

PDFs são tratados como conteúdo não confiável. Prompts instruem o modelo a ignorar comandos contidos nos documentos. Logs HTTP não armazenam payloads nem credenciais. A trilha de revisão de parâmetros grava eventos imutáveis; em ambiente não local, o identificador técnico do operador é derivado de um subject confiável do gateway por hash, sem persistir identidade em claro.

A retenção de documentos, eventos de auditoria, identificadores técnicos e o uso de dados pessoais devem ser definidos com Segurança, Compliance e DPO conforme a implantação. Critérios jurídicos, inclusive interpretação de sucessão de decisões, precisam de validação do time jurídico antes de serem tratados como política institucional.

## Preparação para validação das dependências do frontend no Nexus

O frontend foi alinhado ao baseline Node.js 22.12.0 + npm 10.9.0 + Angular 21.2.19 e não força dependências transitivas. O primeiro lockfile deve ser resolvido pelo próprio Nexus com `npm run nexus:lock`; depois disso ele é validado, revisado e versionado. Consulte [o procedimento de validação corporativa](docs/VALIDACAO_GOVERNANCA_FRONTEND.md).

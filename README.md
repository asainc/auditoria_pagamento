# Plataforma Jurídica — Auditoria de Pagamentos

Aplicação web para extração assistida, revisão humana e cálculo de débitos judiciais. O frontend utiliza Angular 21.2.19; o backend usa FastAPI; o motor `judicial_calc` permanece determinístico e separado da camada de IA.

## Arquitetura

```text
PDFs enviados pelo usuário
        ↓
DocumentService (persistência local controlada)
        ↓
gpt_bradesco.py → File Manager corporativo
        ↓
OCR híbrido corporativo
        ↓
texto por documento/página
        ↓
prompts especializados 00..09
        ↓
gpt_bradesco.text_generator
        ↓
JSON validado pelo Pydantic
        ↓
ChronologyReducer + OperationalPolicy
        ↓
revisão humana obrigatória
        ↓
CalculationService → EngineFacade → judicial_calc
```

A IA não executa fórmulas financeiras. Ela transforma conteúdo documental em sugestões estruturadas, sempre acompanhadas de evidência rastreável. O cálculo final só é liberado após revisão humana.

## Integração corporativa de IA

Toda geração de texto passa exclusivamente por `gpt_bradesco.text_generator`. Ao anexar um PDF, o backend inicia automaticamente upload corporativo, OCR e consolidação dos parâmetros. O adaptador prioriza `ocr_hibrido`, mas também reconhece `ocr`, `ocr_generator` e `get_text_ocr`. Para upload/listagem/limpeza, reconhece tanto as assinaturas legadas (`file_manager_upload`, `file_manager_list_files`, `file_manager_delete`) quanto wrappers mais novos. Funções como `configure_iagen` e `wait_for_workflow` são opcionais e só são usadas quando existirem.

O payload padrão do OCR inclui:

- `detailed_output=true`;
- `async_mode=true`;
- `workflow_configuration_code=CD_WRFL_OCR_HYBRID_ASYNC`;
- modelo de visão configurável;
- saída de tabelas em Markdown;
- `locale=pt-BR`;
- avisos habilitados.

Os arquivos remotos são removidos após a extração do texto sempre que o serviço devolve o identificador necessário para a limpeza. Uma falha de limpeza é registrada somente como evento técnico, sem conteúdo documental.

## Configuração do backend

Copie `.env.example` para `.env` na raiz. Nunca versione credenciais reais.

A autenticação pode permanecer integralmente dentro do `gpt_bradesco.py` corporativo. Os campos `BRADESCO_AUTHORIZATION_TOKEN`, `BRADESCO_IDENTIFICADOR` e `BRADESCO_SENHA` só precisam ser preenchidos quando a versão do módulo expuser `configure_iagen` e a equipe responsável determinar esse fluxo. Configure obrigatoriamente um container aprovado para o OCR:

```text
BRADESCO_OCR_CONTAINER=CONTAINER_AUTORIZADO
```

Parâmetros principais:

```text
BRADESCO_IAGEN_AMBIENTE=dev
BRADESCO_TEXT_MODEL=gpt-5.1
BRADESCO_TEXT_REASONING_EFFORT=medium
BRADESCO_TEXT_VERBOSITY=medium
BRADESCO_TEXT_TEMPERATURE=1
BRADESCO_TEXT_MAX_TOKENS=16384
BRADESCO_OCR_WORKFLOW=CD_WRFL_OCR_HYBRID_ASYNC
BRADESCO_OCR_VISION_MODEL=gpt-4o
BRADESCO_OCR_LANGUAGE_MODEL=gpt-4o
BRADESCO_OCR_LOCALE=pt-BR
```

Os nomes de deployment e workflow precisam existir no ambiente corporativo. A aplicação não inventa substitutos quando uma configuração não está disponível.

## Execução sem ambiente virtual

Em computadores onde ambientes virtuais não são permitidos, execute a partir da raiz do projeto e garanta que as dependências Python aprovadas estejam disponíveis no interpretador corporativo:

```cmd
set "PYTHONPATH=%CD%\src;%CD%"
python -m uvicorn backend.principal:aplicacao --reload --host 127.0.0.1 --port 8000
```

Teste antes:

```cmd
python -c "import judicial_calc.data; import gpt_bradesco; print('Imports OK')"
```

O projeto inclui `src/judicial_calc/data/` com as planilhas exigidas pelo motor.

## Frontend corporativo

Baseline utilizado:

- Node.js 22.12.0;
- npm 10.9.0;
- Angular 21.2.19.

A instalação corporativa aceita os `.tgz` oficiais baixados localmente conforme `docs/INSTALACAO_FRONTEND_NEXUS_TARBALLS.md`. Os overrides atuais refletem as versões informadas como disponíveis no ambiente corporativo e devem ser revalidados se o catálogo do Nexus mudar.

## Prompts especializados

Os prompts ficam em `prompts/`:

- `_base.md`: regras comuns, segurança e contrato de evidência;
- `00_classificacao.md`: tipo documental e marcos processuais;
- `01_parcelas.md`: dano material, moral, honorários e custas;
- `02_correcao.md`: atualização monetária;
- `03_moratorios.md`: juros moratórios;
- `04_compensatorios.md`: juros compensatórios;
- `05_encargos.md`: multa, honorários e art. 523;
- `06_prescricao.md`: prescrição;
- `07_compensacao.md`: compensação;
- `08_duplo_indice.md`: períodos com índices diferentes;
- `09_eventos.md`: depósitos, pagamentos, levantamentos e compensações.

O backend envia somente o subcontrato de parâmetros necessário a cada tarefa. Se o texto OCR ultrapassar o limite configurado por chamada, ele é dividido por documento/página sem descartar conteúdo. Cada parte continua sendo processada por `text_generator`, e o backend reindexa parcelas/eventos antes da consolidação.

## Telemetria

A aplicação registra apenas informações observáveis: número de chamadas, modelo/serviço e duração. O contrato corporativo atualmente usado pelo projeto não devolve contagem de tokens nem cobrança; por isso esses campos ficam `null` e a interface mostra “Não disponibilizado”. Nenhum valor é estimado sem fonte verificável.

## Estrutura principal

```text
backend/
  services/bradesco_bridge.py   facade do módulo corporativo
  services/extraction.py        OCR, prompts e consolidação
  services/ai_usage.py          telemetria conservadora
config/
  app.settings.json             configuração não secreta
  calculation_policy.json       políticas operacionais
  extraction_tasks.json         limite de saída por tarefa
frontend/                        Angular 21.2.19
prompts/                         prompts especializados
src/judicial_calc/               motor financeiro determinístico
gpt_bradesco.py                  cliente corporativo integrado
tests/                           testes automatizados
docs/                            documentação técnica
```

## Regeneração de artefatos

Após alterar contratos Python:

```bash
python scripts/generate_contracts.py
python scripts/generate_parameter_catalog.py
python scripts/generate_parameter_docs.py
python scripts/generate_code_reference.py
python scripts/generate_engine_manifest.py
```

## Testes

```bash
python -m pytest
python scripts/validate_architecture.py
```

No frontend, quando as dependências estiverem instaladas:

```powershell
cd frontend
npm test
npm run build
```

Os testes corporativos de integração usam dublês e não chamam rede real. A primeira execução real deve ser feita em ambiente autorizado, com PDF sintético, antes de qualquer uso com documentos reais.

## Governança e privacidade

- segredos não ficam no código, exemplos, logs ou documentação;
- conteúdo OCR, prompts e PDFs não são registrados nos logs técnicos;
- o arquivo remoto usado pelo OCR é removido após o processamento quando possível;
- evidências são revalidadas contra o texto OCR antes de chegar à revisão;
- qualquer interpretação jurídica, política de retenção ou uso de dados pessoais precisa de validação do Jurídico/Compliance e do DPO conforme o caso de uso.

Consulte `docs/EXTRACAO_IA.md`, `docs/OPERACAO.md`, `docs/FLUXO_EXTRACAO_VISUAL.md`, `docs/MODEL_CARD.md` e `docs/VALIDACAO.md`.

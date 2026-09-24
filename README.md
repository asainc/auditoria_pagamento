# Plataforma Jurídica — Auditoria de Pagamentos

Aplicação web para extração assistida, revisão humana e cálculo de débitos judiciais. O frontend utiliza Angular 21.2.19; o backend usa FastAPI; o motor `judicial_calc` permanece determinístico e separado da camada de IA.

## Arquitetura

```text
PDFs enviados pelo usuário
        ↓
DocumentService (persistência local controlada)
        ↓
PyMuPDF (leitura local da camada de texto)
        ↓
string com documento/página
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

Os PDFs não são enviados para OCR nem para File Manager. O backend lê a camada de texto localmente com `PyMuPDF`, preserva marcadores de documento e página e monta uma string para cada lote de contexto. Cada string é combinada com o prompt especializado e enviada exclusivamente a `gpt_bradesco.text_generator`.

Não existe fallback automático para OCR. Se uma página for imagem sem camada textual, a aplicação gera um alerta para revisão humana em vez de inventar conteúdo.

## Configuração do backend

Copie `.env.example` para `.env` na raiz. Nunca versione credenciais reais.

A autenticação pode permanecer integralmente dentro do `gpt_bradesco.py` corporativo. Os campos `BRADESCO_AUTHORIZATION_TOKEN`, `BRADESCO_IDENTIFICADOR` e `BRADESCO_SENHA` só precisam ser preenchidos quando a versão do módulo expuser `configure_iagen` e a equipe responsável determinar esse fluxo. Não há configuração de container ou workflow de OCR.

Parâmetros principais:

```text
BRADESCO_IAGEN_AMBIENTE=dev
BRADESCO_TEXT_MODEL=gpt-5.1
BRADESCO_TEXT_TEMPERATURE=1
BRADESCO_TEXT_MAX_TOKENS=16384
BRADESCO_PROMPT_MAX_CHARS=55000
```

O nome do deployment precisa existir no ambiente corporativo. A aplicação não inventa substitutos quando ele não está disponível.

## Execução sem ambiente virtual

Em computadores onde ambientes virtuais não são permitidos, use o Python corporativo já instalado. Os scripts de inicialização configuram `PYTHONPATH` automaticamente para localizar `src/judicial_calc`, sem exigir instalação editável do projeto.

No CMD do Windows:

```cmd
scripts\start-backend.cmd
```

No PowerShell:

```powershell
.\scripts\start-backend.ps1
```

Ou manualmente, a partir da raiz:

```cmd
set "PYTHONPATH=%CD%\src;%CD%"
python -m uvicorn backend.principal:aplicacao --reload --host 127.0.0.1 --port 8000
```

Se o comando `python` corporativo tiver outro caminho, defina `BACKEND_PYTHON` antes de iniciar.

Teste antes:

```cmd
python -c "import judicial_calc.data; import gpt_bradesco; print('Imports OK')"
```

O projeto inclui `src/judicial_calc/data/` com as planilhas exigidas pelo motor.

### Atualização sobre instalações anteriores

Ao iniciar o backend, o repositório SQLite aplica migrações locais antes de criar os índices. Isso permite abrir uma base `business.sqlite3` criada por versões anteriores, inclusive quando a tabela `parameter_changes` ainda não possuía `draft` e `origin`. A tabela anterior é preservada como `parameter_changes_legacy_vN` antes da materialização do contrato atual.

O pacote `backend` também coloca `<raiz>/src` no início do caminho de importação. Esse comportamento evita que computadores corporativos sem ambiente virtual carreguem acidentalmente outra instalação de `judicial_calc` presente no perfil do usuário.

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
- `09_valor_dobrado.md`: restituição/devolução em dobro determinada pelo título, aplicada somente às parcelas de dano material.

O backend envia somente o subcontrato de parâmetros necessário a cada tarefa. Antes da chamada ao `text_generator`, o `PromptPageRouter` seleciona deterministicamente as páginas mais relevantes para aquela tarefa e preserva páginas representativas como fallback. O empacotamento respeita limites de caracteres sem cortar páginas silenciosamente; a telemetria registra quantas páginas e caracteres foram enviados para permitir auditoria da seleção.

## Telemetria

A aplicação registra apenas informações observáveis: número de chamadas, modelo/serviço, duração, páginas de contexto, caracteres enviados, uso de reparo estrutural, hashes dos prompts e contagem de evidências aceitas/rejeitadas. O contrato corporativo atualmente usado pelo projeto não devolve contagem de tokens nem cobrança; por isso esses campos ficam `null` e nenhum valor financeiro é estimado sem fonte verificável. Conteúdo documental, prompt integral e credenciais não são persistidos nos logs técnicos.

## Estrutura principal

```text
backend/
  services/bradesco_bridge.py   facade do módulo corporativo
  services/extraction.py        orquestrador da extração
  services/pdf_text_extractor.py leitura PyMuPDF + qualidade textual
  services/prompt_router.py     seleção determinística de páginas
  services/prompt_executor.py   execução e métricas do text_generator
  services/structured_output.py normalização estrutural local
  services/evidence_validator.py validação e consolidação de evidências
  services/extraction_jobs.py   workers da fila durável
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
- PDFs, texto extraído e prompts não são registrados nos logs técnicos;
- os PDFs permanecem no armazenamento controlado do backend e não são enviados ao serviço de OCR;
- evidências são revalidadas contra o texto extraído da página antes de chegar à revisão;
- qualquer interpretação jurídica, política de retenção ou uso de dados pessoais precisa de validação do Jurídico/Compliance e do DPO conforme o caso de uso.

Consulte `docs/EXTRACAO_IA.md`, `docs/OPERACAO.md`, `docs/FLUXO_EXTRACAO_VISUAL.md`, `docs/MODEL_CARD.md` e `docs/VALIDACAO.md`.

## Correção da conexão com text_generator — 24/09/2026

O backend agora encaminha ambiente e CA mesmo quando as credenciais vêm do
processo. O cliente distribuído recebe o timeout definido no backend e aceita
BRADESCO_TEXT_URL e BRADESCO_IDENTITY_URL no `.env` (URLs HTTPS completas,
confirmadas pela equipe da API). Campos vazios preservam as rotas existentes.

1. Extraia esta versão em uma pasta nova e mantenha seu `.env` local protegido.
2. Confira `BRADESCO_IAGEN_AMBIENTE`, `BRADESCO_TEXT_MODEL` e autenticação:
   token válido ou identificador e senha fornecidos pela equipe responsável.
3. Confira `BRADESCO_CA_BUNDLE` se houver CA corporativa e
   `BRADESCO_TIMEOUT_SECONDS` para o tempo máximo por requisição HTTP.
4. Reinicie o backend e execute a extração de um PDF sintético pesquisável.
5. Se persistir: envie somente a mensagem sanitizada/código HTTP, sem tokens,
   credenciais, documentos reais ou cabeçalhos Authorization.

Falhas TLS orientam a configuração da CA; falhas de rede orientam a verificação
 de VPN, DNS, proxy e URLs; HTTP 401/403 exige revisar autenticação/permissões;
HTTP 400 exige confirmar deployment e contrato; HTTP 404 pode indicar rota ou
recurso incorreto. Presença de configuração não comprova conectividade.

Validação desta correção usa transporte HTTP simulado. Não houve acesso ao
serviço corporativo real; a causa específica do incidente depende da mensagem
obtida no ambiente do usuário. O motor de cálculo não foi alterado.

## Correção da lista de índices — 24/09/2026

A verificação de conexão do frontend agora aceita a versão `2.0.0` informada
pelo backend deste pacote. Antes, exigia `1.0.0` e interrompia a inicialização
antes de consultar `/api/indices`. O carregamento de índices também foi separado
do resultado da busca de processos: uma falha nesta busca não descarta o catálogo.
Quando não houver índices carregados, o painel informa a falha/carregamento e
oferece **Tentar novamente**, mantendo o seletor indisponível até receber a lista.

Para aplicar, atualize o frontend com os arquivos deste pacote e reinicie o
servidor Angular. Em instalações com build publicado, gere e publique novamente
o frontend. Recarregue o navegador para remover a versão anterior da aplicação.
As correções anteriores de conexão com text_generator estão incluídas.

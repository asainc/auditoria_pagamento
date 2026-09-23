# Referência do código

> Arquivo gerado automaticamente por `scripts/generate_code_reference.py`.
> As descrições vêm das docstrings/comentários do source; não edite este arquivo manualmente.

## Como ler esta referência

Use esta referência para localizar responsabilidades. Para entender a sequência de execução, consulte `FLUXO_CALCULO.md`; para contratos e valores padrão, consulte `PARAMETROS.md`.

# Python

## `backend/__init__.py`

API HTTP da calculadora; a experiência visual pertence ao Angular.

Este módulo não expõe classes ou funções de nível superior.

## `backend/access.py`

Publicação protegida por gateway autenticado; local usa apenas loopback.

### `def require_access(request: Request) -> None`

Cabeçalho é inserido pelo gateway, nunca enviado ao navegador como segredo.

## `backend/calculation_policy.py`

Catálogo e padrões centrais do cálculo.

### `class CalculationPolicyConfigurationError(RuntimeError)`

Indica erro estrutural na política versionada da aplicação.


### `def load_calculation_policy() -> dict[str, Any]`

Carrega e valida a estrutura mínima da política de cálculo.

### `def parameter_catalog() -> list[dict[str, Any]]`

Retorna cópia rasa do catálogo central de parâmetros.

### `def parameter_keys() -> tuple[str, ...]`

Retorna as chaves na ordem usada pela interface e pela documentação.

### `def required_parameter_keys() -> tuple[str, ...]`

Retorna os campos mínimos necessários para disparar o motor.

### `def parameter_label(key: str) -> str`

Converte uma chave técnica no rótulo oficial da aplicação.

### `def defaults_for_origin(origin: CalculationOrigin) -> dict[str, Any]`

Retorna os valores padrão efetivos para a origem informada.

### `def apply_missing_defaults(parameters: dict[str, Any], origin: CalculationOrigin) -> dict[str, Any]`

Completa somente campos ausentes; valores explícitos nunca são sobrescritos.

### `def policy_hash() -> str`

Retorna SHA-256 canônico da política efetivamente carregada.

## `backend/config.py`

Configuração validada; erros não são substituídos silenciosamente por padrões.

### `class OperationalSettings(Contract)`

Visão tipada dos padrões documentais definidos no catálogo central.


### `class Settings(Contract)`

Parâmetros operacionais centralizados; segredos vêm do ambiente.

- `def validate_origins(cls, values: list[str]) -> list[str]` — Uma origem explícita evita conceder acesso CORS a sites arbitrários.
- `def require_gateway(self) -> Settings` — Publicação depende do gateway autenticado; não há login paralelo na UI.

### `def load_settings() -> Settings`

Prioridade: ambiente > .env > JSON > padrões; segredos corporativos não são persistidos.

## `backend/container.py`

Composição dos serviços por instância FastAPI, sem estado global de sessão.

### `class Services`

Proprietário das conexões curtas e executores da aplicação.

- `def __init__(self, settings: Settings, provider: ExtractionProvider | None=None)` — Cria os serviços da aplicação a partir de uma configuração validada e dependências opcionais.
- `def close(self) -> None` — Finaliza os recursos pertencentes a esta instância.

### `def services(request: Request) -> Services`

Injeção explicita facilita TestClient e evita dependências entre rotas.

## `backend/errors.py`

Falhas de domínio chegam às rotas sem expor arquivos ou dados internos.

### `class ServiceError(Exception)`

Erro esperado, com mensagem operacional segura e código HTTP explícito.

- `def __init__(self, message: str, status_code: int=422)` — Recebe dependências explicitamente para manter configuração e testes isolados.

## `backend/models.py`

Contratos oficiais: recusam campos desconhecidos e preservam decimais.

### `class Contract(BaseModel)`

Base fechada para impedir erros de digitação silenciosos nos contratos.


### `class Installment(Contract)`

Parcela informada ou revisada; sem identificadores pessoais.


### `class FinancialEvent(Contract)`

Evento segue os critérios já aceitos pelo motor, sem inferência jurídica.

- `def require_date(self) -> FinancialEvent` — Evita encaminhar eventos calculáveis sem data ao motor.

### `class CalculationParameters(Contract)`

Parâmetros normalizados que chegam ao motor de cálculo.

- `def require_active_fields(self) -> CalculationParameters` — Valida completude; a decisão sobre aplicação de regras fica no motor.

### `class CalculationDraft(Contract)`

Entrada completa de um cálculo antes da confirmação humana definitiva.

- `def apply_origin_defaults(cls, raw: object) -> object` — Aplica os padrões da origem antes de validar ``CalculationParameters``.
- `def validate_origin_identity(self) -> 'CalculationDraft'` — Impede que o modo manual seja confundido com um processo documental.

### `class CalculationRequest(CalculationDraft)`

Execução e exportação exigem confirmação humana explícita.


### `class DataTable(Contract)`

Tabela de saída: colunas variam conforme recursos ativados no motor.


### `class SummaryEntry(Contract)`

Campo e valor tal como retornados pelo resumo do motor.


### `class CalculationMetadata(Contract)`

Identifica de forma reproduzível a entrada, política, motor e séries usadas.


### `class CalculationResponse(Contract)`

Saída oficial que o Angular apresenta sem recalcular valores.


### `class DocumentMetadata(Contract)`

Metadados públicos do arquivo, sem expor caminhos de servidor.


### `class ProcessSummary(Contract)`

Processo e contagem obtidos dos documentos persistidos.


### `class AiUsage(Contract)`

Telemetria técnica de uma chamada corporativa, sem conteúdo documental.


### `class AiUsageSummary(Contract)`

Resumo de chamadas; tokens/custo ficam nulos quando o serviço não os informa.


### `class ExtractionRequest(Contract)`

Identifica exclusivamente o processo cuja extração será iniciada.


### `class ExtractionStatus(Contract)`

Estado de negócio persistido para acompanhamento e recuperação.


### `class ExtractionConfiguration(Contract)`

Presença da configuração corporativa sem expor segredos ou testar credenciais.


### `class UploadResponse(Contract)`

Documentos recebidos e seus trabalhos de extração associados.


### `class FieldEvidence(Contract)`

Trecho rastreável enriquecido com papel processual e efeito cronológico.


### `class OperationalAdjustment(Contract)`

Regra configurada pelo operador; não é citação de documento.


### `class CalculationDefaults(Contract)`

Competência do relógio do backend, em horário de Brasília.


### `class FeePreparation(Contract)`

Recalcula somente a composição nominal autorizada, antes da revisão.


### `class ChronologyDecision(Contract)`

Resultado explicável da consolidação temporal de um parâmetro.


### `class ExtractionResult(Contract)`

Sugestões rastreáveis que ainda exigem conferência humana.


### `class ParameterOption(Contract)`

Opção de seleção exibida no frontend a partir do catálogo central.


### `class ParameterCatalogItem(Contract)`

Metadados oficiais de apresentação e uso de um parâmetro.


### `class CalculationPolicyView(Contract)`

Padrões e catálogo fornecidos pelo backend para uma origem de cálculo.


### `class ParameterChangeInput(Contract)`

Alteração de parâmetro enviada pela interface para trilha imutável de revisão.

- `def validate_change(self) -> 'ParameterChangeInput'` — Restringe eventos às chaves do catálogo e à identidade da origem.

### `class ParameterChangeRecord(ParameterChangeInput)`

Evento persistido com carimbo de tempo e origem documental resolvida no servidor.


### `class IndexOption(Contract)`

Chave registrada no motor e rótulo de apresentação.


### `class IndexStatus(Contract)`

Estado observado da atualização e hashes dos arquivos existentes.


### `class BatchRequest(Contract)`

Lote limitado de requisições integralmente validadas.


### `class BatchItem(Contract)`

Sucesso ou falha identificável por processo, sem descarte silencioso.


### `class BatchResponse(Contract)`

Resultados de cada processo do lote, incluindo falhas.


### `class BatchImport(Contract)`

Prévia que não representa execução ou confirmação de revisão.


## `backend/principal.py`

Única inicialização FastAPI; não hospeda o frontend da aplicação.

### `class Health(Contract)`

Identifica disponibilidade da API e sua versão de contrato.


### `class AuditFormatter(logging.Formatter)`

Logs estruturados contêm apenas metadados técnicos selecionados.

- `def format(self, record: logging.LogRecord) -> str` — Seleciona metadados de auditoria sem serializar conteúdo de requisições.

### `def create_app(settings: Settings | None=None, provider: ExtractionProvider | None=None) -> FastAPI`

Cria uma instância FastAPI com configuração e dependências explicitamente injetáveis.

## `backend/repository.py`

Persistência transacional do estado de negócio; nenhum estado visual é salvo.

### `def timestamp() -> str`

Horário UTC torna eventos comparáveis em instalações distintas.

### `class Repository`

SQLite com conexão curta por operação e compare-and-set para trabalhos.

- `def __init__(self, data_dir: Path)` — Recebe dependências explicitamente para manter configuração e testes isolados.
- `def connection(self) -> Iterator[sqlite3.Connection]` — Commit ou rollback integral, sem conexões compartilhadas entre threads.
- `def add_document(self, document: DocumentMetadata) -> DocumentMetadata` — A unicidade por processo e hash torna o reenvio idempotente.
- `def documents(self, process: str) -> list[DocumentMetadata]` — Consulta documentos pelo processo com parâmetros SQL vinculados.
- `def document(self, identifier: str) -> DocumentMetadata | None` — Resolve identificador opaco sem aceitar caminhos do usuário.
- `def classify_document(self, identifier: str, classification: str) -> None` — Somente a classificação muda; hash e associação ao processo permanecem fixos.
- `def processes(self) -> list[ProcessSummary]` — Deriva a lista de processos do estado documental persistido.
- `def start_job(self, status: ExtractionStatus) -> None` — Registra a revisão vigente do trabalho e permite rejeitar resultados de outra revisão.
- `def update_job(self, status: ExtractionStatus, result: ExtractionResult | None=None) -> None` — Atualiza somente a revisão ainda vigente e rejeita retornos atrasados.
- `def status(self, process: str) -> ExtractionStatus | None` — Consulta estado persistido; ausência é distinta de falha de processamento.
- `def result(self, process: str) -> ExtractionResult | None` — Só disponibiliza resultado associado à revisão vigente.
- `def recover_jobs(self) -> None` — Reinício não simula conclusão: trabalhos pendentes ficam disponíveis para repetição.
- `def add_parameter_change(self, change: ParameterChangeInput, *, actor: str, extracted_value: object=None, extracted_source: str | None=None) -> ParameterChangeRecord` — Persiste evento imutável de revisão e devolve o registro materializado.
- `def parameter_changes(self, *, process: str | None=None, draft: str | None=None) -> list[ParameterChangeRecord]` — Consulta a trilha por processo real ou por rascunho manual, em ordem temporal.
- `def audit(self, event: str, payload: dict[str, str | int | float | bool]) -> None` — Somente identificadores técnicos, contagens e hashes; nunca conteúdo documental.

## `backend/routers/__init__.py`

Rotas apenas recebem, validam e delegam aos serviços.

Este módulo não expõe classes ou funções de nível superior.

## `backend/routers/audit.py`

Endpoints de auditoria da revisão humana de parâmetros.

### `def _technical_actor(request: Request) -> str`

Deriva identificador técnico sem persistir identidade pessoal em claro.

### `def record_parameter_change(payload: ParameterChangeInput, request: Request, service: Dependency)`

Registra uma alteração de parâmetro como evento imutável.

### `def list_parameter_changes(service: Dependency, numero_processo: str | None=Query(default=None), rascunho_id: str | None=Query(default=None))`

Consulta por processo real ou por rascunho manual; exige exatamente um filtro.

## `backend/routers/batches.py`

Lotes reutilizam o mesmo serviço de cálculo e a confirmação humana.

### `async def import_batch(service: Dependency, file: UploadFile=File(...))`

Importar apenas prepara a prévia; não executa nem confirma o lote.

### `def run(payload: BatchRequest, service: Dependency)`

Falhas são explícitas por processo; sucessos não são descartados.

## `backend/routers/calculations.py`

Cálculo e exportações compartilham o mesmo contrato validado.

### `def defaults()`

A data corrente é fornecida pelo backend, sem relógio jurídico no Angular.

### `def calculation_policy(origem_calculo: CalculationOrigin)`

Expõe padrões e metadados oficiais sem duplicá-los no frontend.

### `def prepare_fees(payload: FeePreparation)`

Mostra os valores nominais para revisão antes da chamada ao motor.

### `def calculate(payload: CalculationRequest, service: Dependency)`

Calcula somente após a confirmação humana enviada no contrato.

### `def memory_pdf(payload: CalculationRequest, service: Dependency, auditavel: bool=False, indices_sha256: str | None=None)`

Retorna bytes do PDF, sem template de interface nem arquivo temporário remanescente.

## `backend/routers/documents.py`

Documentos chegam por multipart e são obtidos por identificador opaco.

### `async def upload(service: Dependency, files: list[UploadFile]=File(...))`

A extração é iniciada no servidor imediatamente após a persistência.

### `def processes(service: Dependency)`

Lista processos armazenados sem selecionar automaticamente nenhum na UI.

### `def process_documents(numero_processo: str, service: Dependency)`

A seleção filtra no backend e evita misturar documentos de processos.

### `def file(identificador_documento: str, service: Dependency)`

A autorização global da API também protege o conteúdo PDF.

### `async def import_installments(service: Dependency, verba_tipo: DamageType, file: UploadFile=File(...))`

O limite também se aplica a planilhas antes de sua leitura pelo importador.

## `backend/routers/extractions.py`

Consulta e repetição da extração não dependem de estado do navegador.

### `def configuration(service: Dependency)`

Expõe somente disponibilidade operacional da integração corporativa.

### `def start(payload: ExtractionRequest, service: Dependency)`

Retentativa manual é útil após configurar o provedor ou reiniciar o serviço.

### `def status(numero_processo: str, service: Dependency)`

Ausência de trabalho é 404; falha do provedor é estado explícito.

### `def result(numero_processo: str, service: Dependency)`

Somente extração consolidada é devolvida para revisão humana.

## `backend/routers/indices.py`

Catálogo e atualização de índices passam exclusivamente pela API.

### `def options(service: Dependency)`

Devolve somente chaves registradas no motor.

### `def status(service: Dependency)`

Informa estado real, sem afirmar atualização não verificada.

### `def update(service: Dependency)`

Atualização segue assíncrona e pode ser acompanhada por polling.

## `backend/services/__init__.py`

Serviços de aplicação independentes dos componentes Angular.

Este módulo não expõe classes ou funções de nível superior.

## `backend/services/ai_usage.py`

Telemetria de chamadas corporativas sem estimar consumo não informado.

### `class UsageMeter`

Cria telemetria conservadora a partir dos dados realmente observáveis.

- `def from_call(*, model: str, stage: str, duration_ms: float) -> AiUsage` — Sem descrição específica no código.

### `class RequestTimer`

Cronômetro monotônico para medir somente latência técnica.

- `def __init__(self) -> None` — Sem descrição específica no código.
- `def elapsed_ms(self) -> float` — Sem descrição específica no código.

## `backend/services/batches.py`

Orquestração de lotes reaproveita o cálculo unitário, sem duplicar o motor.

### `class BatchService`

Execução sequencial limita memória e mantém erros separados por processo.

- `def __init__(self, calculation: CalculationService)` — Recebe dependências explicitamente para manter configuração e testes isolados.
- `def execute(self, payload: BatchRequest) -> BatchResponse` — Preserva os sucessos e informa explicitamente cada falha de domínio.

## `backend/services/bradesco_bridge.py`

Integração única com os serviços corporativos de IA e OCR.

### `class BradescoBridgeError(ServiceError)`

Erro sanitizado da integração corporativa, com código operacional estável.

- `def __init__(self, code: str, message: str, status_code: int=502)` — Sem descrição específica no código.

### `class OcrPage`

Texto OCR de uma página, sem persistência adicional no serviço remoto.


### `class OcrDocument`

Documento OCR normalizado para consumo pelos prompts especializados.

- `def texto_prompt(self) -> str` — Expõe nome e página de forma explícita para manter evidência rastreável.

### `class BradescoBridgeClient`

Facade de baixo acoplamento sobre ``gpt_bradesco.py``.

- `def __init__(self, settings: Settings)` — Sem descrição específica no código.
- `def configured(self) -> bool` — Valida somente presença de configuração; não faz chamada de rede.
- `def _load(self) -> Any` — Importa e configura o módulo corporativo no primeiro uso.
- `def _safe_request_id(value: Any) -> str | None` — Aceita somente IDs técnicos curtos antes de incluí-los em mensagem.
- `def _classify_error(self, exc: Exception, operation: str) -> BradescoBridgeError` — Traduz falhas externas sem ecoar corpo, documento ou segredo.
- `def _call(self, operation: str, function_name: str, *args: Any, **kwargs: Any) -> Any` — Executa uma função corporativa e centraliza tratamento de erro.
- `def _walk(value: Any) -> Iterable[tuple[str | None, Any]]` — Percorre respostas JSON sem pressupor um único envelope do gateway.
- `def _find_first_text(self, payload: Any, keys: tuple[str, ...]) -> str | None` — Sem descrição específica no código.
- `def _extract_identifier(self, payload: Any, keys: tuple[str, ...]) -> str | None` — Sem descrição específica no código.
- `def _resolve_file_id(self, upload_result: Any, remote_name: str) -> str` — Obtém o ID do upload; consulta a listagem somente se a resposta não o trouxer.
- `def _upload_pdf(self, name: str, content: bytes) -> str` — Envia PDF em base64 apenas durante a chamada e retorna o ID remoto.
- `def _ocr_payload(self, file_id: str) -> dict[str, Any]` — Monta o OCR híbrido seguindo o contrato exemplificado para a plataforma.
- `def _wait_if_needed(self, result: Any) -> Any` — Aguarda workflow assíncrono somente quando a resposta fornece seu ID.
- `def _page_number(mapping: Mapping[str, Any], page_keys: tuple[str, ...]) -> int | None` — Converte identificadores de página sem aceitar booleanos ou negativos.
- `def _pages_from_payload(self, payload: Any) -> list[OcrPage]` — Normaliza diferentes envelopes detalhados de OCR preservando a página.
- `def ocr_pdf(self, name: str, content: bytes, expected_pages: int) -> OcrDocument` — Envia um PDF ao OCR e remove o objeto remoto após obter o texto.
- `def generate_text(self, payload: str, *, max_tokens: int) -> str` — Executa qualquer prompt exclusivamente por ``text_generator``.

## `backend/services/calculation.py`

Orquestra cálculo, exportação e auditoria fora das rotas HTTP.

### `class CalculationService`

Uma execução coerente usa a mesma versão de índices até o fim.

- `def __init__(self, repository: Repository, facade: EngineFacade)` — Recebe dependências explicitamente para manter configuração e testes isolados.
- `def execute(self, payload: CalculationRequest, pdf: bool=False, audit: bool=False, expected_indices_hash: str | None=None) -> CalculationResponse | bytes` — Validação Pydantic antecede a fachada; falhas não expõem conteúdo sensível.

## `backend/services/chronology.py`

Consolidação determinística da evolução documental de um processo.

### `def document_sequence(name: str) -> int`

Obtém a sequência cronológica do padrão ``processo_sequencia*.pdf``.

### `def ordered_documents(documents: list[DocumentMetadata]) -> list[DocumentMetadata]`

Ordena anexos do mais antigo para o mais recente de forma determinística.

### `class ChronologyReducer`

Resolve valores efetivos sem apagar as evidências históricas que os originaram.

- `def reduce(self, evidences: Iterable[FieldEvidence]) -> tuple[dict[str, Scalar], list[ChronologyDecision], list[str]]` — Consolida apenas ``parametros.*`` e devolve valor, decisão e alertas.
- `def _resolve_commands(self, path: str, commands: list[FieldEvidence]) -> tuple[Scalar, FieldEvidence, str] | None` — Aplica os efeitos dos comandos em ordem cronológica.
- `def _value_key(value: Scalar) -> str` — Compara escalares sem depender de hash de tipos heterogêneos.
- `def _sort_key(item: FieldEvidence) -> tuple[int, int, str]` — Ordenação estável para escolher a evidência mais recente entre concordantes.
- `def _decision(path: str, evidence: FieldEvidence, reason: str) -> ChronologyDecision` — Materializa a decisão de consolidação para auditoria e UI.

## `backend/services/documents.py`

Upload validado, persistente e organizado exclusivamente no backend.

### `class DocumentService`

Identifica o processo pelo nome exigido; conteúdo não altera a associação.

- `def __init__(self, settings: Settings, repository: Repository)` — Recebe dependências explicitamente para manter configuração e testes isolados.
- `async def receive(self, files: list[UploadFile]) -> list[DocumentMetadata]` — Valida o lote completo antes de persistir; leitura limitada evita alocações ilimitadas.
- `def path(self, identifier: str) -> tuple[Path, DocumentMetadata]` — Somente documento registrado pode ser obtido pelo identificador opaco.

## `backend/services/engine.py`

Única fachada do cálculo: adapta tipos sem reproduzir fórmulas.

### `def file_hashes(directory: Path, pattern: str) -> dict[str, str]`

Hash de conteúdo identifica código e séries sem incluir dados nos logs.

### `def digest(values: dict[str, str]) -> str`

Ordenação torna o identificador independente da ordem do filesystem.

### `def scalar(value: object) -> Scalar`

Decimais viram texto para evitar arredondamento binário na serialização.

### `def dataframe_table(frame: pd.DataFrame) -> DataTable`

O formato tabular admite colunas adicionais produzidas pelo próprio motor.

### `class EngineFacade`

Isola o motor de cálculo dos contratos HTTP e das estruturas da interface.

- `def __init__(self, settings: Settings)` — Recebe dependências explicitamente para manter configuração e testes isolados.
- `def calculate(self, payload: CalculationRequest) -> ResultadoCalculo` — Converte a requisição validada para o formato esperado pelo motor e executa o cálculo.
- `def pdf(self, result: ResultadoCalculo, audit: bool=False) -> bytes` — O arquivo é exportação de negócio; nenhum HTML é produzido no backend.
- `def index_hash(self) -> str` — A versão das séries é capturada enquanto o cálculo detém o lock.

## `backend/services/engine_guidance.py`

Transforma erros estruturados do motor em orientação operacional segura.

### `def _labels(keys: tuple[str, ...]) -> str`

Formata os campos do erro usando a mesma nomenclatura exibida na interface.

### `def engine_error_guidance(error: Exception) -> str`

Retorna orientação para correção sem analisar nem devolver o texto da exceção.

## `backend/services/extraction.py`

Extração documental usando exclusivamente os serviços corporativos configurados.

### `class ExtractionFragment(Contract)`

Fragmento especializado já validado pelo contrato interno.


### `class ProviderResult(Contract)`

Fragmento estruturado e telemetria observável das chamadas corporativas.


### `class ExtractionProviderError(ServiceError)`

Erro público estável; nunca inclui corpo da resposta, prompt ou credencial.

- `def __init__(self, code: str, message: str, status_code: int=502)` — Sem descrição específica no código.

### `class ExtractionProvider`

Executa OCR e prompts somente pelo módulo ``gpt_bradesco.py``.

- `def __init__(self, settings: Settings, bridge: BradescoBridgeClient | None=None)` — Sem descrição específica no código.
- `def configured(self) -> bool` — Indica se há autenticação, deployment de texto e container de OCR configurados.
- `def _translate_error(exc: Exception) -> ExtractionProviderError` — Sem descrição específica no código.
- `def ocr_documents(self, files: list[tuple[str, bytes, int]]) -> tuple[list[OcrDocument], list[AiUsage]]` — Extrai texto de cada PDF por OCR corporativo antes de qualquer prompt.
- `def _split_large_block(header: str, text: str, max_chars: int) -> list[str]` — Divide uma página muito grande por parágrafos sem perder referência de página.
- `def _pack_ocr(self, documents: list[OcrDocument]) -> list[str]` — Agrupa páginas para limitar payload sem descartar texto OCR.
- `def _json_object(text: str) -> dict` — Aceita JSON puro ou bloco cercado; qualquer outra saída é rejeitada.
- `def _shift_evidence(field: FieldEvidence, parcel_offset: int, event_offset: int) -> FieldEvidence` — Reindexa referências ao combinar respostas de múltiplos chunks.
- `def _deduplicate_fields(fields: list[FieldEvidence]) -> list[FieldEvidence]` — Remove duplicatas exatas sem resolver conflitos materiais.
- `def extract(self, prompt: str, documents: list[OcrDocument], *, stage: str, max_output_tokens: int) -> ProviderResult` — Executa o prompt especializado por ``text_generator`` sobre texto OCR.

### `class ExtractionService`

Orquestra OCR, prompts, cronologia, consolidação e persistência da extração.

- `def __init__(self, settings: Settings, repository: Repository, documents: DocumentService, provider: ExtractionProvider)` — Sem descrição específica no código.
- `def start(self, process: str, new_upload: bool=False) -> ExtractionStatus` — Retentativa explícita compartilha trabalho ativo; novo upload cria revisão nova.
- `def run(self, status: ExtractionStatus, documents: list[DocumentMetadata]) -> None` — Executa OCR antes de qualquer prompt e mantém cada estágio consultável.
- `def _sum_optional(values: list[int | None]) -> int | None` — Soma somente quando todas as chamadas realmente forneceram a métrica.
- `def _summarize_usage(cls, usages: list[AiUsage]) -> AiUsageSummary` — Não estima tokens ou custo quando o contrato corporativo não os retorna.
- `def consolidate(self, result: ExtractionResult, documents: list[DocumentMetadata], ocr_documents: list[OcrDocument] | None=None) -> ExtractionResult` — Valida evidências contra OCR, resolve cronologia inequívoca e mantém conflitos.
- `def close(self) -> None` — Desliga a fila sem perder o status persistido dos trabalhos pendentes.

## `backend/services/extraction_wire.py`

Contrato externo simples; limites financeiros continuam no contrato interno.

### `class WireEvidence(FieldEvidence)`

Mantém o schema externo simples e torna papel/efeito explicitamente obrigatórios.


### `class WireInstallment(Contract)`

Dinheiro como texto evita regex Decimal e conversão por ponto flutuante.


### `class WireFinancialEvent(Contract)`

Todos os campos são obrigatórios no transporte, sem defaults no schema.


### `class WireExtractionFragment(Contract)`

Somente tipos básicos e enums são enviados ao gerador estruturado.


## `backend/services/imports.py`

Importadores rejeitam linhas inválidas em vez de alterar o lote silenciosamente.

### `def read_table(content: bytes, filename: str) -> list[dict[str, str]]`

Somente formatos documentados; CSV exige UTF-8 e preserva identificadores.

### `def normalize_date(value: object) -> str`

Datas ISO têm prioridade; o formato brasileiro é aceito explicitamente.

### `def normalize_money(value: object) -> str`

A vírgula identifica formato brasileiro; decimal canônico usa ponto.

### `def installment_from_row(row: dict[str, str], damage_type: str) -> Installment`

Normalização de arquivo fica centralizada e usa o mesmo contrato da API.

### `class ImportService`

A prévia nunca calcula nem confirma revisão humana.

- `def installments(self, content: bytes, filename: str, damage_type: str) -> list[Installment]` — Importa todas as linhas ou informa erro, sem omitir valores inválidos.
- `def batch(self, content: bytes, filename: str) -> BatchImport` — JSON carrega o contrato completo; planilhas agrupam parcelas por processo.

## `backend/services/indices.py`

Gestão das séries delega ao atualizador existente, com exclusão mútua.

### `def display_name(key: str, raw_name: str) -> str`

Normaliza nomes da lista para o padrão esperado na interface.

### `def display_label(key: str, raw_name: str) -> str`

Acrescenta o intervalo de disponibilidade quando conhecido.

### `def _public_update_failure(result) -> str`

Converte a falha técnica do atualizador em orientação segura para a interface.

### `class IndexService`

Uma atualização por vez, estado verificável e backup fornecido pelo motor.

- `def __init__(self, settings: Settings, repository: Repository, facade: EngineFacade)` — Recebe dependências explicitamente para manter configuração e testes isolados.
- `def options(self) -> list[IndexOption]` — Lista índices selecionáveis, inclusive séries históricas extintas conhecidas.
- `def status(self) -> IndexStatus` — Checksum relata o arquivo real; não implica atualidade da série.
- `def save(self, state: str, message: str) -> IndexStatus` — Persiste o estado de atualização para consultas e recuperação.
- `def start(self) -> IndexStatus` — A trava do processo evita que dois cliques enfileirem atualizações iguais.
- `def run(self) -> None` — Atualiza as séries sob a mesma trava usada pelo cálculo.
- `def close(self) -> None` — Encerra recursos próprios sem interferir em outras instâncias.

## `backend/services/operational_policy.py`

Aplica critérios operacionais rastreáveis antes da revisão humana do cálculo.

### `def current_competence(today: date | None=None) -> CalculationDefaults`

Retorna mês e ano da data de referência no calendário da aplicação.

### `def fee_installments(rows: list[Installment], percentage: Decimal) -> list[Installment]`

Compõe parcelas nominais de honorários; não calcula juros ou correção.

### `def validate_prepared_request(payload: CalculationRequest) -> None`

Não permite duplicar encargos nem calcular sobre uma composição desatualizada.

### `class OperationalPolicy`

Aplica os padrões após conferir evidências, separando-os dos fatos extraídos.

- `def __init__(self, configuration: OperationalSettings | None=None)` — Configuração central permite alterar seleção sem editar o motor.
- `def apply(self, extracted: ExtractionResult, today: date | None=None) -> ExtractionResult` — Aplica padrões somente quando a evidência do caso concreto não informa o campo.

## `backend/services/prompt_context.py`

Monta contexto enxuto e específico por tarefa para reduzir tokens repetidos.

### `class PromptContext`

Prefixo comum estável e contexto processual reutilizados no mesmo processo.

- `def for_task(self, task_path: Path) -> str` — Inclui somente o subcontrato necessário à tarefa para reduzir payload textual.

### `class PromptContextBuilder`

Pré-calcula dados estáveis e evita repetir o schema integral em todas as chamadas.

- `def __init__(self, base_path: Path | None=None)` — Sem descrição específica no código.
- `def build(self, process: str, documents: list[DocumentMetadata]) -> PromptContext` — Materializa apenas cronologia e catálogo; o subcontrato entra por tarefa.

## `backend/services/revision_audit.py`

Persistência e enriquecimento da trilha de revisão humana dos parâmetros.

### `class RevisionAuditService`

Registra eventos imutáveis sem depender do estado visual do Angular.

- `def __init__(self, repository: Repository)` — Recebe o repositório que persiste os eventos imutáveis de revisão.
- `def record(self, change: ParameterChangeInput, actor: str) -> ParameterChangeRecord` — Enriquece o evento com o valor/origem extraídos que o servidor conhece.
- `def list_for_process(self, process: str) -> list[ParameterChangeRecord]` — Retorna toda a trilha persistida do processo.
- `def list_for_draft(self, draft: str) -> list[ParameterChangeRecord]` — Retorna a trilha do rascunho manual atual.

## `scripts/evaluate_extraction.py`

Compara predições de extração com um conjunto de referência revisado.

### `def _case_map(payload: dict[str, Any], field_name: str) -> dict[str, dict[str, Any]]`

Indexa casos por identificador e valida a presença do objeto de campos.

### `def evaluate(gold: dict[str, Any], predictions: dict[str, Any]) -> dict[str, Any]`

Calcula acerto exato por campo e lista divergências sem ocultá-las em média.

### `def main() -> int`

Lê arquivos informados em CLI e imprime relatório JSON reproduzível.

## `scripts/generate_contracts.py`

Gera interfaces TypeScript do OpenAPI; a API é a fonte única dos contratos.

### `def type_name(schema: dict) -> str`

Converte somente estruturas publicadas pelo Pydantic/OpenAPI.

### `def main() -> None`

Salva contrato e interfaces com ordenação estável para comparação em testes.

## `scripts/generate_engine_manifest.py`

Gera o manifesto SHA-256 dos arquivos Python do motor determinístico.

### `def engine_manifest() -> dict[str, str]`

Retorna hashes ordenados dos fontes Python que compõem o pacote do motor.

### `def main() -> int`

Persiste o manifesto em JSON estável para validação de integridade.

## `scripts/generate_parameter_catalog.py`

Gera o catálogo TypeScript a partir da política central versionada.

### `def ts(value: object) -> str`

Serializa JSON válido também como literal TypeScript.

### `def main() -> None`

Valida chaves básicas e grava o artefato consumido pela interface.

## `scripts/generate_parameter_docs.py`

Gera a documentação do catálogo de parâmetros a partir da política central.

### `def _display(value: object) -> str`

Converte valores da política para texto curto e estável em Markdown.

### `def main() -> None`

Grava padrões, obrigatoriedade, opções e grupos sem duplicação manual.

## `scripts/validate_architecture.py`

Valida fronteiras arquiteturais, dependências proibidas e versões fixadas do frontend.

### `def architecture_errors(root: Path) -> list[str]`

Imports são analisados por AST, evitando falsos positivos em palavras como interest.

## `src/judicial_calc/__init__.py`

Sem descrição específica no código.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/calculator.py`

Sem descrição específica no código.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/cli.py`

Interface de linha de comando do projeto.

### `def _decimal_para_texto(obj: Any) -> Any`

Serializa ``Decimal`` para JSON.

### `def main() -> None`

Executa o cálculo a partir de um arquivo JSON.

## `src/judicial_calc/core/__init__.py`

Sem descrição específica no código.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/core/constants.py`

Sem descrição específica no código.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/core/dates.py`

Funções utilitárias para datas e competências mensais.

### `def _int_flex(valor: str | int, nome: str) -> int`

Converte inteiros que podem chegar como 2026.0/"2026.0".

### `def parse_mes_ano(mes: str | int, ano: str | int) -> str`

Converte mês e ano em competência ``AAAA-MM``.

### `def parse_data(valor: str | date | datetime) -> date`

Converte uma entrada de data para ``datetime.date``.

### `def competencia_data(d: date) -> str`

Extrai a competência mensal de uma data.

### `def data_primeiro_dia(comp: str) -> date`

Retorna o primeiro dia de uma competência.

### `def ultimo_dia_mes(comp: str) -> date`

Retorna o último dia de uma competência.

### `def somar_meses(comp: str, meses: int) -> str`

Soma ou subtrai meses de uma competência.

### `def iter_competencias(inicio: str, fim: str) -> Iterable[str]`

Itera competências mensais em intervalo fechado.

### `def competencias_entre(inicio: str, fim: str) -> int`

Conta a diferença em meses entre duas competências.

## `src/judicial_calc/core/errors.py`

Exceções estruturadas usadas na fronteira do motor de cálculo.

### `class CalculationValidationError(ValueError)`

Representa uma combinação inválida de parâmetros do motor.

- `def __init__(self, code: str, fields: Iterable[str]=(), message: str='Parâmetros de cálculo incompatíveis.') -> None` — Inicializa código estável, campos relacionados e mensagem pública sanitizada.

## `src/judicial_calc/core/models.py`

Modelos Pydantic versionados para entrada/auditoria do cálculo judicial.

### `class StrictBaseModel(BaseModel)`

Base comum que aceita campos extras para compatibilidade evolutiva.


### `class EvidenceSource(StrictBaseModel)`

Fonte/evidência usada para justificar um campo extraído.

- `def is_usable_for_calculation(self) -> bool` — Indica se a evidência pode alimentar o cálculo final.

### `class ParcelaInput(StrictBaseModel)`

Parcela individual calculável.


### `class VerbaJudicial(StrictBaseModel)`

Verba consolidada por natureza jurídica.


### `class EventoFinanceiro(StrictBaseModel)`

Evento financeiro cronológico que pode abater ou documentar valores.

- `def validate_data_for_abating_event(self) -> 'EventoFinanceiro'` — Eventos que afetam cálculo precisam de data.

### `class PrescricaoParams(StrictBaseModel)`

Agrupa os parâmetros estruturados de prescrição usados no contrato interno.


### `class CompensacaoParams(StrictBaseModel)`

Agrupa os parâmetros estruturados de compensação usados no contrato interno.


### `class DuploIndiceParams(StrictBaseModel)`

Agrupa os parâmetros das duas faixas de correção do modo de duplo índice.


### `class CalculoJudicialInput(StrictBaseModel)`

Payload versionado completo para cálculo judicial auditável.

- `def params_must_be_dict(cls, value: dict[str, Any]) -> dict[str, Any]` — Garante que o bloco de parâmetros seja recebido como dicionário antes das demais validações.
- `def calculation_params(self) -> dict[str, Any]` — Retorna ``params`` enriquecido com eventos financeiros para o motor.

## `src/judicial_calc/core/numbers.py`

Funções utilitárias para conversão e arredondamento numérico.

### `def D(valor: Any) -> Decimal`

Converte valores comuns para ``Decimal`` de forma segura.

### `def moeda(valor: Any) -> Decimal`

Arredonda um valor para centavos com regra comercial.

### `def percentual_taxa_legal(valor_decimal: Decimal) -> Decimal`

Arredonda percentuais equivalentes da Taxa Legal.

### `def arredondar_abnt(valor: Decimal, casas: int) -> Decimal`

Arredonda usando o critério ABNT/meio par.

## `src/judicial_calc/core/tables.py`

Normalização de tabelas de índices.

### `def normalizar_tabela_mensal(tabela: pd.DataFrame | list[dict[str, Any]], coluna_valor: str='indice') -> pd.DataFrame`

Normaliza tabela mensal para o formato usado nos cálculos.

## `src/judicial_calc/core/types.py`

Tipos públicos retornados pela biblioteca.

### `class ResultadoCalculo`

Resultado completo do cálculo judicial.


## `src/judicial_calc/data/__init__.py`

Sem descrição específica no código.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/data_sources/__init__.py`

Sem descrição específica no código.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/data_sources/drcalc_updater.py`

Atualização diária das planilhas locais de índices a partir do DrCalc.

### `class DrCalcRecord`

Uma observação extraída de uma série do DrCalc.


### `class DrCalcSeries`

Série histórica extraída de uma página do DrCalc.


### `class DrCalcUpdateResult`

Resultado auditável da tentativa de atualização.

- `def to_dict(self) -> dict[str, Any]` — Serializa o resultado da atualização do DrCalc para um dicionário simples e auditável.

### `class DrCalcUpdateError(RuntimeError)`

Falha controlada da atualização das planilhas locais.


### `def _today_str() -> str`

Retorna a data corrente em formato ISO para gravação do estado do atualizador.

### `def _data_dir(path: str | Path | None=None) -> Path`

Resolve a pasta que contém as planilhas locais de índices.

### `def _state_path(data_dir: Path) -> Path`

Resolve o arquivo JSON usado para persistir o estado do atualizador.

### `def _lock_path(data_dir: Path) -> Path`

Resolve o arquivo de lock que impede duas atualizações simultâneas.

### `def _load_state(data_dir: Path) -> dict[str, Any]`

Lê o estado persistido do atualizador e retorna uma estrutura vazia quando não existe estado válido.

### `def _write_state(data_dir: Path, result: DrCalcUpdateResult) -> None`

Persiste o estado da atualização preservando o último sucesso.

### `def _already_updated_today(data_dir: Path) -> bool`

Verifica se já existe atualização bem-sucedida registrada para a data corrente.

### `def _normalize_text(value: Any) -> str`

Normaliza texto HTML para comparação de títulos e cabeçalhos de séries.

### `def _decimal_from_ptbr(value: Any) -> Decimal | None`

Converte números em formatos PT-BR/EN para Decimal.

### `def _parse_date_like(value: Any) -> date | str | None`

Normaliza datas/competências extraídas do HTML.

### `def _periodicity(records: Iterable[DrCalcRecord]) -> str`

Infere a periodicidade de uma série a partir dos períodos observados.

### `def _competencia_from_period(periodo: date | str) -> str`

Converte um período mensal para a competência canônica AAAA-MM.

### `def _build_category_url(category_id: int) -> str`

Monta a URL inicial de uma categoria do DrCalc.

### `class DrCalcClient`

Cliente simples para descobrir e baixar séries do DrCalc.

- `def __init__(self, session: requests.Session | None=None, timeout: int=30) -> None` — Inicializa a instância com as dependências e configurações necessárias ao componente.
- `def get(self, url: str) -> str` — Executa uma requisição HTTP com timeout e tratamento de falhas do cliente.
- `def _request_form(self, *, method: str, url: str, payload: dict[str, str]) -> tuple[str, str]` — Submete o formulário histórico do DrCalc preservando o método informado pela página.
- `def discover_series_urls(self) -> list[tuple[str, str, str]]` — Retorna tuplas ``(categoria, nome, url)`` encontradas nas categorias alvo.
- `def fetch_historical_series(self) -> list[DrCalcSeries]` — Baixa as séries pela consulta histórica oficial do DrCalc.
- `def _select_signature(select: Any) -> str` — Produz uma assinatura textual estável para classificar campos do formulário.
- `def _numeric_option_values(select: Any) -> list[int]` — Retorna valores inteiros das opções quando o campo é predominantemente numérico.
- `def _select_role(self, select: Any) -> str` — Classifica ``select`` como categoria, mês, ano, série ou outro.
- `def _field_boundary(signature: str) -> str | None` — Infere se o campo representa o início ou o fim do intervalo pesquisado.
- `def _option_value_for_number(select: Any, number: int, *, nearest: str) -> str | None` — Escolhe a opção numérica desejada respeitando os valores efetivamente publicados.
- `def _selected_or_first_value(select: Any) -> str | None` — Lê a opção selecionada do formulário ou usa a primeira opção com valor.
- `def _find_history_form(self, soup: BeautifulSoup) -> tuple[Any, Any, list[Any], list[Any]] | None` — Localiza o formulário de consulta e seus campos de série, mês e ano.
- `def _split_interval_selects(self, selects: list[Any]) -> tuple[Any, Any]` — Separa os dois campos equivalentes em início/fim usando nome e ordem do DOM.
- `def _base_form_payload(self, form: Any) -> dict[str, str]` — Copia campos ocultos e defaults necessários para reproduzir a submissão do formulário.
- `def _fetch_category_form_series(self, *, category_name: str, category_id: int, category_url: str, html: str) -> list[DrCalcSeries]` — Submete o formulário histórico para todos os indexadores de uma categoria.
- `def _infer_metric_from_columns(columns: Iterable[str]) -> str` — Infere a natureza da métrica pela semântica dos cabeçalhos.
- `def _discover_category_ids(self) -> list[tuple[str, int]]` — Descobre os IDs das três categorias relevantes sem depender de posição fixa.
- `def _is_series_select(select: Any) -> bool` — Identifica o ``select`` de indexadores e ignora mês, ano e categoria.
- `def _extract_links_from_category(self, html: str, base_url: str) -> list[tuple[str, str]]` — Extrai somente links plausíveis de séries da categoria informada.
- `def fetch_series(self, category: str, name: str, url: str) -> DrCalcSeries | None` — Baixa e interpreta uma série do DrCalc em registros estruturados.
- `def _series_title(self, soup: BeautifulSoup, fallback: str) -> str` — Obtém um título estável para identificar a série baixada.
- `def _extract_records_from_html(self, html: str, soup: BeautifulSoup, preferred_metric: str | None=None) -> tuple[list[DrCalcRecord], list[str]]` — Extrai registros temporais do HTML da série.
- `def _records_from_table(self, df: pd.DataFrame, preferred_metric: str | None=None) -> list[DrCalcRecord]` — Converte uma tabela HTML em registros de período e valor.
- `def _records_from_matrix_table(self, df: pd.DataFrame) -> list[DrCalcRecord]` — Interpreta tabelas históricas no formato ano x meses ou mês x anos.

### `def _series_score(series_name: str, target_label: str, extra_aliases: Iterable[str]=()) -> int`

Calcula uma pontuação heurística para escolher a série mais compatível com um destino.

### `def _looks_like_rate_percent(series: DrCalcSeries) -> bool`

Avalia de forma conservadora se uma série sem unidade parece percentual.

### `def _best_series_for_monthly_column(column: str, series_list: list[DrCalcSeries]) -> DrCalcSeries | None`

Seleciona a melhor série mensal para alimentar uma coluna da planilha local.

### `def _best_daily_series(kind: str, series_list: list[DrCalcSeries]) -> DrCalcSeries | None`

Seleciona a melhor série diária entre as séries descobertas.

### `def _convert_monthly_value(column: str, valor: Decimal, *, source_metric: str='unknown') -> Decimal`

Converte o valor mensal da fonte para a unidade esperada pela planilha local.

### `def _convert_daily_value(valor: Decimal, *, source_metric: str='unknown') -> Decimal`

Converte o valor diário da fonte para a unidade esperada pela planilha local.

### `def _monthly_dataframe_from_workbook(path: Path) -> pd.DataFrame`

Lê a planilha mensal existente e normaliza seu conteúdo em DataFrame.

### `def _daily_dataframe_from_workbook(path: Path) -> pd.DataFrame`

Lê a planilha diária existente e normaliza seu conteúdo em DataFrame.

### `def _write_monthly_workbook(df: pd.DataFrame, path: Path) -> None`

Grava a tabela mensal normalizada no arquivo Excel de destino.

### `def _write_daily_workbook(df: pd.DataFrame, path: Path) -> None`

Grava a tabela diária normalizada no arquivo Excel de destino.

### `def _merge_monthly(existing_path: Path, series_list: list[DrCalcSeries]) -> tuple[pd.DataFrame, list[str], list[str]]`

Combina séries mensais baixadas com a estrutura da planilha local.

### `def _merge_daily(existing_path: Path, series: DrCalcSeries | None, label: str) -> tuple[pd.DataFrame, list[str]]`

Combina a série diária baixada com a estrutura da planilha local.

### `def _validate_outputs(monthly: pd.DataFrame, daily_selic_ipcae: pd.DataFrame, daily_12_6: pd.DataFrame) -> None`

Valida se as planilhas produzidas possuem estrutura e conteúdo mínimos esperados.

### `def _backup_planilhas(data_dir: Path) -> Path`

Cria cópia de segurança das planilhas antes de substituí-las.

### `def _atomic_replace(src: Path, dst: Path) -> None`

Substitui um arquivo de destino de forma atômica após gravação temporária.

### `def _df_row_count(path: Path, *, daily: bool=False) -> int`

Conta linhas úteis de uma planilha local de índices.

### `def _df_date_range(df: pd.DataFrame, date_col: str='data') -> tuple[str, str]`

Retorna intervalo textual mínimo/máximo de datas/competências.

### `def _build_diff_row(filename: str, before_rows: int, after_df: pd.DataFrame) -> dict[str, Any]`

Resume diferença de linhas e intervalo de datas de uma planilha.

### `def _consistency_checks(monthly: pd.DataFrame, daily_selic_ipcae: pd.DataFrame, daily_12_6: pd.DataFrame) -> list[dict[str, Any]]`

Gera checagens legíveis para a tela administrativa de índices.

### `def list_drcalc_backups(data_dir: str | Path | None=None) -> list[dict[str, Any]]`

Lista backups locais das planilhas de índices.

### `def restaurar_backup_drcalc(backup_id_or_path: str, *, data_dir: str | Path | None=None) -> DrCalcUpdateResult`

Restaura as planilhas a partir de um backup criado pelo atualizador.

### `def _clear_local_caches() -> None`

Limpa caches de leitura de índices para que os próximos cálculos usem os arquivos atuais.

### `def _acquire_lock(data_dir: Path, wait_seconds: int=20) -> bool`

Adquire o lock de atualização e retorna o recurso usado para liberação posterior.

### `def _release_lock(data_dir: Path) -> None`

Libera o lock de atualização adquirido pelo processo.

### `def baixar_series_drcalc(timeout: int=30) -> list[DrCalcSeries]`

Baixa as séries disponíveis nas três categorias alvo do DrCalc.

### `def atualizar_planilhas_drcalc(*, data_dir: str | Path | None=None, timeout: int=30, series_list: list[DrCalcSeries] | None=None) -> DrCalcUpdateResult`

Força atualização das três planilhas locais a partir do DrCalc.

### `def atualizar_planilhas_drcalc_se_necessario(*, data_dir: str | Path | None=None, force: bool=False, timeout: int=30, strict: bool=False) -> DrCalcUpdateResult`

Atualiza as planilhas apenas uma vez por dia.

## `src/judicial_calc/data_sources/http_client.py`

Sem descrição específica no código.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/data_sources/local_excel.py`

Leitura das planilhas locais usadas nos cálculos judiciais.

### `class LocalIndexSpec`

Metadados de uma coluna de índice na tabela mensal local.


### `class MissingLocalIndexSpec`

Metadados de índice conhecido, mas sem coluna na planilha local.


### `def _resource_path(filename: str) -> Path`

Resolve o caminho de uma planilha empacotada no projeto.

### `def normalize_key(text: str) -> str`

Normaliza nomes e rótulos de índices para chaves seguras de API.

### `def _spec(key: str, column: str, mode: IndexMode, *aliases: str) -> LocalIndexSpec`

Cria a especificação de uma coluna mensal com aliases normalizados.

### `def local_index_specs() -> tuple[LocalIndexSpec, ...]`

Lista os índices efetivamente disponíveis na planilha mensal.

### `def local_missing_index_specs() -> tuple[MissingLocalIndexSpec, ...]`

Lista índices conhecidos, mas sem dados na planilha mensal.

### `def resolve_index_key(key_or_label: str) -> str`

Resolve aliases para a chave técnica do índice.

### `def get_index_spec(key_or_label: str) -> LocalIndexSpec`

Obtém metadados de um índice local.

### `def _decimal_or_none(value: Any) -> Decimal | None`

Converte célula de planilha para ``Decimal`` ou ``None``.

### `def _month_from_cell(value: Any) -> str | None`

Converte célula de competência mensal para ``AAAA-MM``.

### `def _date_from_cell(value: Any) -> date`

Converte célula diária da planilha para ``datetime.date``.

### `def load_monthly_indices(path: str | None=None) -> pd.DataFrame`

Carrega a tabela mensal local em formato largo.

### `def load_index_series(key_or_label: str, path: str | None=None) -> pd.DataFrame`

Retorna a série mensal de uma chave local.

### `def load_taxa_legal_mensal_percentual(path: str | None=None) -> pd.DataFrame`

Carrega a coluna mensal da Taxa Legal em percentual ao mês.

### `def load_daily_rate_table(kind: str, path: str | None=None) -> pd.DataFrame`

Carrega uma tabela diária local de taxas em decimal ao dia.

### `def available_indices() -> pd.DataFrame`

Retorna uma tabela de índices locais disponíveis.

### `def missing_indices() -> pd.DataFrame`

Retorna índices conhecidos que não possuem coluna na planilha.

## `src/judicial_calc/extraction/__init__.py`

Sem descrição específica no código.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/extraction/base.py`

Contratos simples para extratores de tabelas mensais.

### `class MonthlyTableExtractor(ABC)`

Interface para fontes que entregam séries mensais.

- `def extract(self, inicio: str, fim: str) -> pd.DataFrame` — Extrai uma janela mensal fechada.

### `class InMemoryMonthlyTableExtractor(MonthlyTableExtractor)`

Extrator para tabelas já carregadas em memória.

- `def __init__(self, tabela: pd.DataFrame | list[dict[str, Any]], value_column: str='indice') -> None` — Armazena a tabela que será filtrada posteriormente.
- `def extract(self, inicio: str, fim: str) -> pd.DataFrame` — Filtra a tabela de memória no intervalo mensal.

## `src/judicial_calc/extraction/sgs.py`

Download de séries mensais e diárias do SGS/Bacen.

### `def _baixar_sgs_curto(codigo: int, nome: str, inicio: str, fim: str) -> pd.DataFrame`

Baixa um bloco mensal curto do SGS e consolida por competência.

### `def baixar_sgs(codigo: int, nome: str, inicio: str, fim: str) -> pd.DataFrame`

Baixa série mensal do SGS/Bacen em blocos seguros.

### `def _baixar_sgs_diario_curto(codigo: int, nome: str, data_inicio: date, data_fim: date) -> pd.DataFrame`

Baixa um bloco diário curto do SGS/Bacen.

### `def baixar_sgs_diario(codigo: int, nome: str, data_inicio: date, data_fim: date) -> pd.DataFrame`

Baixa uma série diária do SGS preservando cada data observada.

### `class SGSMonthlyExtractor(MonthlyTableExtractor)`

Extrator mensal para uma série SGS/Bacen.

- `def __init__(self, codigo: int, nome: str) -> None` — Armazena metadados da série SGS.
- `def extract(self, inicio: str, fim: str) -> pd.DataFrame` — Baixa a janela mensal configurada no extrator.

## `src/judicial_calc/indices/__init__.py`

Sem descrição específica no código.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/indices/base.py`

Estratégias base para correção monetária.

### `class CorrectionIndexStrategy(ABC)`

Contrato para qualquer índice de correção monetária.

- `def final_competence(self, competencia_atualizacao: str) -> str` — Retorna a competência final usada no cálculo do índice.
- `def factor(self, *, data_parcela: date, competencia_atualizacao: str, tabela_indices: pd.DataFrame | list[dict[str, Any]] | None, deflacionar_valor_nominal: bool) -> Decimal` — Calcula o fator de correção da parcela.
- `def _apply_floor(self, fator: Decimal, deflacionar_valor_nominal: bool) -> Decimal` — Aplica piso de fator mínimo igual a um quando não há deflação.

### `class NoCorrectionIndex(CorrectionIndexStrategy)`

Estratégia que não aplica correção monetária.

- `def final_competence(self, competencia_atualizacao: str) -> str` — Retorna o mês anterior por consistência com índices mensais.
- `def factor(self, *, data_parcela: date, competencia_atualizacao: str, tabela_indices: pd.DataFrame | list[dict[str, Any]] | None, deflacionar_valor_nominal: bool) -> Decimal` — Retorna fator neutro para qualquer parcela.

### `class ValueTableCorrectionIndex(CorrectionIndexStrategy)`

Correção por tabela customizada de número-índice mensal.

- `def __init__(self, key: str='custom_value_table', final_uses_update_month: bool=False) -> None` — Inicializa a estratégia de tabela customizada.
- `def final_competence(self, competencia_atualizacao: str) -> str` — Retorna a competência final da tabela customizada.
- `def factor(self, *, data_parcela: date, competencia_atualizacao: str, tabela_indices: pd.DataFrame | list[dict[str, Any]] | None, deflacionar_valor_nominal: bool) -> Decimal` — Calcula fator pela tabela customizada do usuário.

### `def fator_tabela_valor_mensal(tabela: pd.DataFrame | list[dict[str, Any]], inicio: str, fim: str) -> Decimal`

Calcula fator por tabela de número-índice mensal.

## `src/judicial_calc/indices/local_excel.py`

Estratégias de correção monetária baseadas na planilha mensal local.

### `def _series_map(tabela: Tabela) -> dict[str, Decimal]`

Normaliza uma tabela mensal em dicionário de acesso rápido.

### `def _default_series_map(key: str) -> dict[str, Decimal]`

Carrega e cacheia a série mensal local de uma chave de índice.

### `def _fator_por_taxa_decimal_map(mapa: dict[str, Decimal], inicio: str, fim: str) -> Decimal`

Acumula variações mensais em decimal usando um mapa já normalizado.

### `def _fator_por_numero_indice_map(mapa: dict[str, Decimal], inicio: str, fim: str) -> Decimal`

Calcula fator por razão entre número-índice final e inicial.

### `def fator_por_taxa_decimal(tabela: Tabela, inicio: str, fim: str) -> Decimal`

Acumula uma tabela mensal de taxas decimais.

### `def fator_por_numero_indice(tabela: Tabela, inicio: str, fim: str) -> Decimal`

Calcula fator de correção por número-índice mensal.

### `class LocalExcelCorrectionIndex(CorrectionIndexStrategy)`

Estratégia de correção por uma coluna do arquivo ``taxas_mensais.xlsx``.

- `def __init__(self, spec: LocalIndexSpec) -> None` — Inicializa a estratégia e seus aliases públicos.
- `def final_competence(self, competencia_atualizacao: str) -> str` — Retorna a competência final usada no índice.
- `def factor(self, *, data_parcela: date, competencia_atualizacao: str, tabela_indices: pd.DataFrame | list[dict[str, Any]] | None, deflacionar_valor_nominal: bool) -> Decimal` — Calcula o fator de correção monetária de uma parcela.

### `def create_local_excel_index_strategies() -> list[LocalExcelCorrectionIndex]`

Cria as estratégias para todas as colunas cadastradas na planilha.

### `def is_local_excel_index(key_or_label: str) -> bool`

Verifica se uma chave ou rótulo existe na planilha local.

## `src/judicial_calc/indices/registry.py`

Registro central das estratégias de correção monetária.

### `class IndexRegistry`

Mapa de chaves de índices para suas estratégias de cálculo.

- `def __init__(self) -> None` — Cria um registro vazio de estratégias.
- `def register(self, strategy: CorrectionIndexStrategy, *aliases: str, overwrite: bool=True) -> None` — Registra uma estratégia por chave principal e aliases.
- `def get(self, key: str) -> CorrectionIndexStrategy | None` — Busca uma estratégia pelo nome do índice.
- `def names(self) -> list[str]` — Lista as chaves registradas em ordem alfabética.

### `def create_default_index_registry() -> IndexRegistry`

Monta e cacheia o registro padrão de índices.

### `def resolve_index_strategy(indice: str, tabela_indices_informada: bool=False) -> CorrectionIndexStrategy`

Resolve a estratégia de correção monetária a partir da chave informada.

## `src/judicial_calc/indices/sgs_percentage.py`

Índices de correção obtidos de séries percentuais mensais SGS/Bacen.

### `def fator_percentual_mensal_por_tabela(tabela: pd.DataFrame | list[dict[str, Any]], competencia_inicio: str, competencia_fim: str, coluna_preferida: str) -> Decimal`

Acumula uma tabela mensal de percentuais.

### `def fator_percentual_mensal(indice: str, competencia_inicio: str, competencia_fim: str) -> Decimal`

Baixa e acumula um índice percentual mensal do SGS.

### `class SGSPercentageCorrectionIndex(CorrectionIndexStrategy)`

Estratégia de correção por série percentual mensal SGS.

- `def __init__(self, key: str, codigo: int, value_column: str) -> None` — Inicializa os metadados da série SGS.
- `def final_competence(self, competencia_atualizacao: str) -> str` — Usa a competência anterior ao mês de atualização.
- `def factor(self, *, data_parcela: date, competencia_atualizacao: str, tabela_indices: pd.DataFrame | list[dict[str, Any]] | None, deflacionar_valor_nominal: bool) -> Decimal` — Calcula o fator de correção pela série SGS.

## `src/judicial_calc/interest/__init__.py`

Sem descrição específica no código.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/interest/daily_rates.py`

Juros moratórios por tabelas diárias locais.

### `def _normalizar_tabela_diaria(tabela: Tabela, kind: str) -> pd.DataFrame`

Normaliza uma tabela diária para cálculo de juros.

### `def _data_fim_periodo(competencia_atualizacao: str, competencia_final_taxa_legal: str | None) -> date`

Define o último dia do período diário a acumular.

### `def soma_taxas_diarias(*, data_inicio: date, data_fim: date, tabela_diaria: Tabela, kind: str) -> tuple[Decimal, Decimal]`

Soma taxas diárias em decimal dentro de um intervalo fechado.

### `def _taxa_legal_decimal_competencia(competencia: str) -> Decimal`

Obtém a Taxa Legal mensal local em decimal para uma competência.

### `def _percentual_selic_ipcae_diario(*, data_inicio: date, data_fim: date, tabela_diaria: Tabela, competencia_atualizacao: str, aplicar_extensao_pos_tabela: bool) -> tuple[Decimal, Decimal]`

Soma a tabela diária SELIC-IPCAE e eventual extensão mensal.

### `def calcular_juros_moratorios_diario(*, valor_base: Decimal, data_inicio: date, competencia_atualizacao: str, tabela_diaria: Tabela, competencia_final_taxa_legal: str | None, kind: str, aplicar_extensao_pos_tabela: bool=False) -> tuple[Decimal, Decimal, Decimal]`

Calcula juros moratórios pela soma de taxas diárias.

## `src/judicial_calc/interest/fixed.py`

Cálculo de juros fixos simples ou compostos.

### `def meses_juros_simples(data_inicio: date, competencia_atualizacao: str, pro_rata: bool=False) -> Decimal`

Conta meses de juros simples até a competência de atualização.

### `def _periodos_compostos(data_inicio: date, competencia_atualizacao: str, periodicidade: str) -> Decimal`

Conta períodos inteiros usados na capitalização composta.

### `def calcular_juros_fixo(valor_base: Decimal, data_inicio: date, competencia_atualizacao: str, taxa: str | Decimal | int | float, periodicidade: str='mensal', pro_rata: bool=False, tipo: str='capitalizacao_simples') -> tuple[Decimal, Decimal, Decimal]`

Calcula juros fixos simples ou compostos.

## `src/judicial_calc/interest/service.py`

Sem descrição específica no código.

### `def calcular_juros(*, valor_base: Decimal, valor_nominal: Decimal, data_parcela: date, competencia_atualizacao: str, taxa: Any, periodicidade: str, pro_rata: bool, tipo: str, data_inicio: str | date | None, tabela_taxa_legal: pd.DataFrame | list[dict[str, Any]] | None, tabela_selic: pd.DataFrame | list[dict[str, Any]] | None, tabela_selic_diaria: pd.DataFrame | list[dict[str, Any]] | None, tabela_ipca_deducao: pd.DataFrame | list[dict[str, Any]] | None, tabela_taxa_legal_diaria_selic_ipcae: pd.DataFrame | list[dict[str, Any]] | None=None, tabela_taxa_legal_diaria_12_6: pd.DataFrame | list[dict[str, Any]] | None=None, competencia_final_taxa_legal: str | None=None, deduzir_correcao_pre_lei: bool=True, aplicar_taxa_legal_pos_lei: bool=True, data_fim_selic_stj1368: date | None=None, competencia_final_taxa_legal_stj1368: str | None=None, usar_selic_mensal_sem_deducao: bool=False, valor_referencia_percentual_stj1368: Decimal | None=None, valor_incidencia_stj1368: Decimal | None=None) -> tuple[Decimal, Decimal, Decimal]`

Seleciona e executa a regra de juros aplicável.

## `src/judicial_calc/interest/taxa_legal.py`

Juros legais especiais usados para replicar opções do critério de referência.

### `def _normalizar_percentual_mensal(tabela: pd.DataFrame | list[dict[str, Any]], coluna: str) -> pd.DataFrame`

Normaliza uma tabela mensal percentual.

### `def _normalizar_selic_diaria(tabela: pd.DataFrame | list[dict[str, Any]]) -> pd.DataFrame`

Normaliza tabela diária da Selic.

### `def _mapa_mensal(tabela: pd.DataFrame, coluna: str) -> dict[str, Decimal]`

Converte tabela mensal normalizada em dicionário ``{AAAA-MM: Decimal}``.

### `def _acumular_percentuais_mensais(comps: Iterable[str], mapa: dict[str, Decimal], nome: str) -> Decimal`

Acumula percentuais mensais em fator composto.

### `def baixar_tabela_taxa_legal_oficial(inicio: str, fim: str) -> pd.DataFrame`

Baixa a Taxa Legal oficial do Bacen/SGS 29543.

### `def gerar_tabela_taxa_legal(inicio: str, fim: str) -> pd.DataFrame`

Gera tabela mensal da Taxa Legal usando exclusivamente SGS 29543.

### `def baixar_tabela_selic_mensal(inicio: str, fim: str) -> pd.DataFrame`

Baixa Selic mensal acumulada no mês, SGS 4390.

### `def baixar_tabela_selic_diaria(data_inicio: date, data_fim: date) -> pd.DataFrame`

Baixa Selic diária, SGS 11, preservando todas as datas da série.

### `def baixar_tabela_ipca_deducao(inicio: str, fim: str, codigo_sgs: int=SGS_IPCA_15) -> pd.DataFrame`

Baixa a inflação usada como dedução no modo STJ 1368.

### `def resolver_competencia_final_taxa_legal(competencia_atualizacao: str, competencia_final_taxa_legal: str | None) -> str`

Resolve a última competência usada em juros/Taxa Legal.

### `def _tabela_taxa_legal(inicio: str, fim: str, tabela_taxa_legal: Tabela) -> pd.DataFrame`

Obtém tabela mensal da Taxa Legal para o intervalo solicitado.

### `def _somar_taxa_legal_percentual(inicio: str, fim: str, tabela_taxa_legal: Tabela) -> Decimal`

Soma percentuais mensais da Taxa Legal em regime simples.

### `def soma_taxa_legal(*, valor_base: Decimal, data_inicio: date, competencia_atualizacao: str, tabela_taxa_legal: Tabela, competencia_final_taxa_legal: str | None) -> tuple[Decimal, Decimal]`

Calcula juros usando somente a Taxa Legal oficial.

### `def fator_selic_mensal(inicio: str, fim: str, tabela_selic: Tabela) -> Decimal`

Acumula a Selic mensal SGS 4390 entre duas competências.

### `def fator_selic_mensal_local_sem_deducao(inicio: str, fim: str, tabela_selic: Tabela) -> Decimal`

Acumula Selic mensal no padrão observado para IGP-M no critério de referência.

### `def fator_selic_diaria(data_inicio: date, data_fim: date, tabela_selic_diaria: Tabela) -> Decimal`

Acumula Selic diária SGS 11 entre duas datas, inclusive.

### `def fator_ipca_deducao(inicio: str, fim: str, tabela_ipca_deducao: Tabela) -> Decimal`

Acumula a inflação mensal deduzida no modo SELIC - correção.

### `def _fator_selic_pre_lei(*, data_inicio: date, data_fim_selic: date, tabela_selic: Tabela, tabela_selic_diaria: Tabela, usar_selic_mensal_sem_deducao: bool) -> Decimal`

Escolhe a série Selic correta para o trecho pré-Lei.

### `def _juros_pre_lei_stj1368(*, valor_nominal: Decimal, data_inicio: date, data_fim_selic: date, fim_deducao_correcao: str, tabela_selic: Tabela, tabela_selic_diaria: Tabela, tabela_ipca_deducao: Tabela, deduzir_correcao_pre_lei: bool, usar_selic_mensal_sem_deducao: bool) -> Decimal`

Calcula o trecho pré-Lei como diferença de montantes.

### `def calcular_juros_stj1368_selic_menos_correcao(*, valor_nominal: Decimal, valor_corrigido: Decimal, data_inicio: date, competencia_atualizacao: str, tabela_selic: Tabela, tabela_selic_diaria: Tabela, tabela_ipca_deducao: Tabela, tabela_taxa_legal: Tabela, competencia_final_taxa_legal: str | None, deduzir_correcao_pre_lei: bool=True, aplicar_taxa_legal_pos_lei: bool=True, data_fim_selic_stj1368: date | None=None, competencia_final_taxa_legal_stj1368: str | None=None, usar_selic_mensal_sem_deducao: bool=False, valor_referencia_percentual: Decimal | None=None, valor_incidencia: Decimal | None=None) -> tuple[Decimal, Decimal, Decimal]`

Replica o seletor critério de referência "Taxa Legal + STJ Tema 1368".

### `def _percentual_juros_fixos_legais(data_inicio: date, competencia_atualizacao: str) -> tuple[Decimal, Decimal]`

Calcula o trecho fixo histórico anterior à Taxa Legal.

### `def soma_juros_moratorios_ctn_lei_14905(*, valor_base: Decimal, data_inicio: date, competencia_atualizacao: str, tabela_taxa_legal: Tabela, competencia_final_taxa_legal: str | None) -> tuple[Decimal, Decimal, Decimal]`

Calcula a opção histórica 6%/12% a.a. + Taxa Legal.

### `def soma_juros_moratorios_stj1368_lei_14905(**kwargs: Any) -> tuple[Decimal, Decimal, Decimal]`

Atalho para o cálculo STJ 1368 com SELIC menos correção.

## `src/judicial_calc/io/__init__.py`

Sem descrição específica no código.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/io/excel.py`

Sem descrição específica no código.

### `def _safe_df(value: Any) -> pd.DataFrame`

Converte listas/dicts/escalares para DataFrame sem quebrar exportação.

### `def _write_if_not_empty(writer: pd.ExcelWriter, sheet_name: str, value: Any) -> None`

Escreve uma aba somente quando há conteúdo.

### `def salvar_resultado_excel(resultado: ResultadoCalculo, caminho: str | Path) -> None`

Salva a memória, resumo e trilha auditável do cálculo em Excel.

## `src/judicial_calc/io/pdf.py`

Exportação da memória de cálculo em PDF no estilo de planilha judicial.

### `def _resumo_dict(resultado: ResultadoCalculo) -> dict[str, Any]`

Converte o DataFrame de resumo em dicionário campo -> valor.

### `def _as_decimal(value: Any, default: str='0') -> Decimal`

Converte valores de pandas/strings/float para Decimal de forma tolerante.

### `def _format_decimal_br(value: Any) -> str`

Formata número com separador brasileiro, sem símbolo monetário.

### `def _format_currency_br(value: Any) -> str`

Formata número em reais para o bloco de subtotais.

### `def _format_percent(value: Any) -> str`

Formata percentual com vírgula decimal.

### `def _format_date_br(value: Any) -> str`

Formata datas em DD/MM/AAAA.

### `def _competencia_label(resumo: dict[str, Any], parametros: dict[str, Any]) -> str`

Retorna competência de atualização em português.

### `def _indice_label(indice: Any) -> str`

Tenta converter a chave interna do índice para o rótulo legível.

### `def _indice_header(resumo: dict[str, Any], parametros: dict[str, Any]) -> str`

Monta o rótulo do indexador, incluindo duplo índice quando houver.

### `def _juros_header(parametros: dict[str, Any], prefixo: str) -> str`

Monta descrição de juros para o cabeçalho.

### `def _truthy(value: Any) -> bool`

Interpreta valores comuns de configuração booleana.

### `def _nonzero(value: Any) -> bool`

Retorna True quando o valor numérico é diferente de zero.

### `def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph`

Cria Paragraph com HTML mínimo escapado e quebra de linha controlada.

### `def _build_styles() -> dict[str, ParagraphStyle]`

Cria os estilos tipográficos e de tabela utilizados na memória PDF.

### `def _table_columns(memoria: pd.DataFrame, parametros: dict[str, Any]) -> list[tuple[str, str, str, int]]`

Define colunas compactas da tabela no padrão DrCalc.

### `def _col_widths(columns: list[tuple[str, str, str, int]], available_width: float) -> list[float]`

Calcula larguras de colunas adequadas à tabela principal do PDF.

### `def _build_memory_table(memoria: pd.DataFrame, parametros: dict[str, Any], styles: dict[str, ParagraphStyle], available_width: float) -> Table`

Cria a tabela principal da memória de cálculo.

### `def _summary_rows(resumo: dict[str, Any], parametros: dict[str, Any]) -> list[tuple[str, str]]`

Monta o bloco de subtotais no rodapé da planilha.

### `def _build_summary_table(resumo: dict[str, Any], parametros: dict[str, Any], styles: dict[str, ParagraphStyle], available_width: float) -> Table`

Cria a tabela alinhada à direita com subtotais e total geral.

### `def _build_header_lines(resultado: ResultadoCalculo) -> list[str]`

Monta o cabeçalho textual do PDF.

### `def _draw_footer(canvas, doc) -> None`

Desenha numeração de páginas discreta.

### `def _records_table(title: str, records: list[dict[str, Any]], styles: dict[str, ParagraphStyle], available_width: float, *, max_rows: int=80) -> list[Any]`

Cria uma seção auditável em tabela simples.

### `def _flatten_evidence_map(evidence_map: Any) -> list[dict[str, Any]]`

Transforma evidence_map em linhas para PDF auditável.

### `def salvar_resultado_pdf_auditavel(resultado: ResultadoCalculo, caminho: str | Path) -> None`

Salva PDF auditável com memória sintética + evidências e alertas.

### `def salvar_resultado_pdf(resultado: ResultadoCalculo, caminho: str | Path) -> None`

Salva a memória de cálculo em PDF no padrão de planilha judicial.

## `src/judicial_calc/services/__init__.py`

Sem descrição específica no código.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/services/calculation_adjustments.py`

Compensação e abatimentos de eventos financeiros aplicados ao resultado.

### `def _calcular_valor_compensacao(cfg: CalculoParams, total_geral_bruto: Decimal) -> Decimal`

Calcula o valor a descontar por compensação sobre o total final bruto.

### `def _aplicar_compensacao_na_memoria(memoria: pd.DataFrame, valor_compensacao: Decimal) -> pd.DataFrame`

Rateia a compensação final entre parcelas para manter memória auditável.

### `def _total_eventos_financeiros(eventos_df: pd.DataFrame) -> Decimal`

Soma eventos financeiros que impactam o total.

### `def _aplicar_eventos_financeiros_na_memoria(memoria: pd.DataFrame, total_eventos: Decimal) -> pd.DataFrame`

Rateia abatimentos cronológicos finais na memória.

### `def _ajustar_resumo_por_eventos(resumo: pd.DataFrame, eventos_df: pd.DataFrame) -> pd.DataFrame`

Inclui abatimentos por eventos financeiros no resumo final.

## `src/judicial_calc/services/calculation_parameters.py`

Normalização e validação dos parâmetros públicos do motor de cálculo.

### `def _subtrair_anos_data(data_base: date, anos: int) -> date`

Subtrai anos preservando mês/dia sempre que possível.

### `def _normalizar_inteiro_flexivel(valor: Any, nome: str, *, permitir_vazio: bool=False, default: int=0) -> int`

Converte entradas comuns de UI/IA para inteiro.

### `def _normalizar_flag_binaria(valor: Any, nome: str, true_aliases: set[str], false_aliases: set[str]) -> int`

Normaliza flags 0/1 aceitando aliases textuais e numéricos flexíveis.

### `def _normalizar_flag_prescricao(valor: Any) -> int`

Normaliza a flag de prescrição para 0 ou 1.

### `def _normalizar_tipo_data_referencia_prescricao(valor: Any) -> str`

Valida o tipo da data de referência usada para a prescrição.

### `def _param_prescricao(params: dict[str, Any], nome: str, default: Any=None) -> Any`

Lê parâmetros de prescrição aceitando aliases de integração.

### `def _resolver_prescricao(params: dict[str, Any]) -> tuple[int, int | None, str | None, date | None, date | None]`

Resolve os parâmetros de prescrição e calcula a data inicial do cálculo.

### `def _normalizar_flag_compensacao(valor: Any) -> int`

Normaliza a flag de compensação para 0 ou 1.

### `def _normalizar_tipo_compensacao(valor: Any) -> str`

Valida o tipo do cálculo da compensação.

### `def _param_compensacao(params: dict[str, Any], nome: str, default: Any=None) -> Any`

Lê parâmetros de compensação aceitando aliases de integração.

### `def _resolver_compensacao(params: dict[str, Any]) -> tuple[int, str, Decimal]`

Resolve os parâmetros de compensação aplicados no final do cálculo.

### `def _normalizar_flag_duplo_indice(valor: Any) -> int`

Normaliza a flag de duplo índice para 0 ou 1.

### `def _param_duplo_indice(params: dict[str, Any], nome: str, default: Any=None) -> Any`

Lê parâmetros de duplo índice aceitando aliases de integração.

### `def _validar_faixa_duplo_indice(prefixo: str, data_inicio: date, data_fim: date) -> None`

Valida uma faixa fechada de datas para duplo índice.

### `def _resolver_valor_parcela_duplo_indice(valor_raw: Any, nome: str) -> Decimal | None`

Normaliza o valor opcional de parcela informado para uma faixa.

### `class FaixaDuploIndice`

Configuração de uma faixa fechada de datas corrigida por índice próprio.

- `def contem(self, data_parcela: date) -> bool` — Retorna True quando a data da parcela está no intervalo fechado.

### `def _resolver_duplo_indice(params: dict[str, Any], indice_padrao: str) -> tuple[int, FaixaDuploIndice | None, FaixaDuploIndice | None]`

Resolve parâmetros de duplo índice e cria as duas faixas fechadas.

### `def _moeda_art_523(valor: Decimal) -> Decimal`

Arredondamento usado pelo critério de referência no bloco do art. 523.

### `def normalizar_art_523(valor: Any) -> str`

Normaliza o seletor do art. 523 do CPC para os nomes internos.

### `class CalculoParams`

Parâmetros normalizados usados internamente pelo serviço.

- `def from_raw(cls, params: dict[str, Any]) -> 'CalculoParams'` — Cria parâmetros normalizados a partir do dicionário público.
- `def tipos_juros(self) -> set[str]` — Retorna os tipos de juros usados no cálculo.
- `def usa_stj1368(self) -> bool` — Indica se o cálculo precisa de séries do modo STJ 1368.
- `def usa_taxa_legal(self) -> bool` — Indica se a Taxa Legal mensal será necessária.
- `def stj1368_deduz_correcao(self) -> bool` — Indica se o modo STJ 1368 deduz inflação da Selic.
- `def tem_prescricao(self) -> bool` — Indica se o cálculo deve aplicar corte por prescrição.
- `def tem_compensacao(self) -> bool` — Indica se o cálculo deve descontar compensação no total final.
- `def tem_duplo_indice(self) -> bool` — Indica se a correção monetária deve variar por faixa de datas.
- `def indices_correcao_usados(self) -> set[str]` — Lista os índices de correção que podem ser usados no cálculo.
- `def faixa_duplo_indice_para_data(self, data_parcela: date) -> FaixaDuploIndice | None` — Retorna a faixa de duplo índice aplicável à data da parcela.

## `src/judicial_calc/services/calculation_penalties.py`

Multas, rateios monetários e art. 523 do CPC usados pelo motor.

### `class MultaLinha`

Detalhamento da multa percentual informada pelo usuário.


### `def _parcela_a_vencer(data_parcela, competencia_atualizacao: str) -> bool`

Indica se a parcela vence depois da competência de atualização.

### `def _multa_pode_incidir(data_parcela, cfg: CalculoParams) -> bool`

Aplica a opção 'incidir multa sobre parcelas a vencer'.

### `def _base_multa_manual(*, valor_atualizado: Decimal, juros_comp: Decimal, juros_mora: Decimal, params: dict[str, Any]) -> Decimal`

Calcula a base da multa percentual informada pelo usuário.

### `def _calcular_multa_linha(*, data_parcela, valor_atualizado: Decimal, juros_comp: Decimal, juros_mora: Decimal, cfg: CalculoParams, params: dict[str, Any]) -> MultaLinha`

Calcula somente a multa percentual comum de uma parcela.

### `def _rateio_monetario(total: Decimal, pesos: list[Decimal]) -> list[Decimal]`

Distribui um valor monetário entre linhas preservando a soma exata.

### `def _total_art_523(cfg: CalculoParams, base_art_523: Decimal) -> tuple[Decimal, Decimal]`

Calcula multa e honorários legais do art. 523 sobre a base final.

### `def _aplicar_art_523_na_memoria(*, memoria: pd.DataFrame, cfg: CalculoParams, honorarios_informados: Decimal) -> pd.DataFrame`

Inclui na memória de cálculo os campos do art. 523.

## `src/judicial_calc/services/calculation_prescription.py`

Filtro de parcelas alcançadas pela configuração de prescrição.

### `def _aplicar_prescricao(df: pd.DataFrame, cfg: CalculoParams) -> pd.DataFrame`

Filtra as parcelas prescritas e mantém apenas valores a partir do corte.

## `src/judicial_calc/services/calculation_service.py`

Orquestração do cálculo de atualização de débitos judiciais.

### `class TabelasCalculo`

Conjunto de tabelas pré-carregadas para evitar chamadas repetidas.


### `def competencia_final_correcao(indice: str, competencia_atualizacao: str) -> str`

Retorna a competência final usada pelo índice de correção.

### `def obter_fator_correcao(*, indice: str, data_parcela, competencia_atualizacao: str, tabela_indices: Tabela, deflacionar_valor_nominal: bool)`

Obtém o fator de correção monetária de uma parcela.

### `def _tabela_indices_para(indice: str, tabelas: TabelasCalculo) -> Tabela`

Retorna a tabela de índices pré-carregada para uma chave específica.

### `def _indice_correcao_linha(data_parcela: date, cfg: CalculoParams) -> tuple[str, Decimal | None, FaixaDuploIndice | None]`

Resolve o índice e eventual valor base específico de uma linha.

### `def _data_inicio_com_prescricao(data_inicio: date, cfg: CalculoParams) -> date`

Aplica a data de corte prescricional ao termo inicial de juros.

### `def _data_inicio_juros_efetiva(params: dict[str, Any], cfg: CalculoParams, prefixo: str, data_parcela: date) -> date`

Calcula a data inicial efetivamente usada nos juros de uma linha.

### `def _datas_inicio_juros(df: pd.DataFrame, cfg: CalculoParams, tipos: set[str]) -> list`

Obtém as datas iniciais dos juros que usam determinado conjunto de tipos.

### `def _precarregar_indices(df: pd.DataFrame, cfg: CalculoParams, tabelas: TabelasCalculo) -> None`

Pré-carrega somente os índices que ainda dependem de SGS.

### `def _precarregar_taxa_legal(df: pd.DataFrame, cfg: CalculoParams, tabelas: TabelasCalculo) -> None`

Carrega a Taxa Legal mensal a partir da planilha critério de referência anexada.

### `def _precarregar_selic(df: pd.DataFrame, cfg: CalculoParams, tabelas: TabelasCalculo) -> None`

Baixa Selic mensal ou diária para o modo STJ 1368.

### `def _precarregar_ipca_deducao(df: pd.DataFrame, cfg: CalculoParams, tabelas: TabelasCalculo) -> None`

Baixa a série de correção deduzida no modo STJ 1368.

### `def _precarregar_tabelas(df: pd.DataFrame, cfg: CalculoParams, params: dict[str, Any]) -> TabelasCalculo`

Centraliza a pré-carga das fontes externas.

### `def _parametros_stj1368(cfg: CalculoParams) -> dict[str, Any]`

Monta os ajustes de transição do modo critério de referência/STJ 1368.

### `def _calcular_juros_da_linha(*, params: dict[str, Any], cfg: CalculoParams, tabelas: TabelasCalculo, valor_base: Decimal, valor_nominal: Decimal, data_parcela, prefixo: str, valor_referencia_percentual_stj1368: Decimal | None=None, valor_incidencia_stj1368: Decimal | None=None) -> tuple[Decimal, Decimal, Decimal]`

Calcula juros compensatórios ou moratórios de uma linha.

### `def _eventos_financeiros_param(params: dict[str, Any]) -> list[dict[str, Any]]`

Lê eventos financeiros do payload/parâmetros aceitando aliases.

### `def _montar_eventos_financeiros(params: dict[str, Any], cfg: CalculoParams, tabelas: TabelasCalculo) -> pd.DataFrame`

Atualiza e ordena eventos financeiros cronológicos para abatimento.

### `def _linha_memoria(row: dict[str, Any], cfg: CalculoParams, params: dict[str, Any], tabelas: TabelasCalculo) -> dict[str, Any]`

Calcula uma parcela e devolve uma linha da memória de cálculo.

### `def _bool_param(valor: Any, default: bool=False) -> bool`

Normaliza parâmetros booleanos vindos de UI/JSON/ambiente.

### `def _executar_atualizacao_indices_se_necessario(params: dict[str, Any]) -> dict[str, Any]`

Executa a atualização diária das planilhas antes do cálculo.

### `def calcular_debitos(parcelas: pd.DataFrame | list[dict[str, Any]], **params: Any) -> ResultadoCalculo`

Calcula a atualização completa de um conjunto de parcelas.

## `src/judicial_calc/services/calculation_summary.py`

Composição do resumo final e dos honorários do cálculo.

### `class HonorariosResumo`

Detalhamento dos honorários e acréscimos finais.

- `def total_honorarios(self) -> Decimal` — Honorários totais: informados + legais do art. 523.
- `def total_art_523(self) -> Decimal` — Acréscimo total do art. 523: multa + honorários legais.

### `def _calcular_honorarios_informados(*, total_atualizado: Decimal, total_comp: Decimal, total_mora: Decimal, total_multa: Decimal, params: dict[str, Any]) -> tuple[Decimal, Decimal]`

Calcula apenas os honorários informados pelo usuário.

### `def _calcular_honorarios_resumo(*, total_atualizado: Decimal, total_comp: Decimal, total_mora: Decimal, total_multa: Decimal, memoria: pd.DataFrame, params: dict[str, Any]) -> HonorariosResumo`

Consolida honorários informados e acréscimos do art. 523.

### `def _total_multa_resumo(memoria: pd.DataFrame, params: dict[str, Any]) -> Decimal`

Calcula o total de multa como o critério de referência exibe na linha de totais.

### `def _montar_resumo(memoria: pd.DataFrame, params: dict[str, Any], cfg: CalculoParams) -> pd.DataFrame`

Agrega os totais finais no mesmo encadeamento visual do critério de referência.

# Angular / TypeScript

## `frontend/src/app/app.component.ts`

Shell Angular único com navegação entre aplicações e módulos operacionais.

Símbolos exportados: `AppComponent`.

## `frontend/src/app/app.routes.ts`

Cada aplicação fica agrupada para permitir expansão futura do sistema.

Símbolos exportados: `routes`.

## `frontend/src/app/batches/batch-page.component.ts`

Lotes mostram a prévia completa antes de solicitar confirmação e executar.

Símbolos exportados: `BatchPageComponent`.

## `frontend/src/app/calculation/calculation-page.component.ts`

Página compõe componentes coesos e concentra apenas a organização visual.

Símbolos exportados: `CalculationPageComponent`.

## `frontend/src/app/calculation/events-editor.component.ts`

Eventos são enviados ao motor somente com valores e critérios revisados.

Símbolos exportados: `EventsEditorComponent`.

## `frontend/src/app/calculation/evidence-panel.component.ts`

Evidências são texto escapado pelo Angular, com navegação para a página da fonte.

Símbolos exportados: `EvidencePanelComponent`.

## `frontend/src/app/calculation/extraction-log.component.ts`

Log visual reúne a origem automática e a trilha imutável de revisão humana.

Símbolos exportados: `ExtractionLogComponent`.

## `frontend/src/app/calculation/installment-batch.component.ts`

Criação de linhas recorrentes organiza datas; não implementa cálculo jurídico.

Símbolos exportados: `InstallmentBatchComponent`.

## `frontend/src/app/calculation/installment-dates.ts`

Meses/anos mantêm o dia original, limitado ao último dia válido de cada mês.

Símbolos exportados: `recurringDate`.

## `frontend/src/app/calculation/installment-editor.component.ts`

Edição direta de parcelas com rolagem própria, sem apagar outros tipos de verba.

Símbolos exportados: `InstallmentEditorComponent`.

## `frontend/src/app/calculation/parameter-fields.ts`

Gerado de config/calculation_policy.json. Não editar manualmente.

Símbolos exportados: `ParameterKey`, `DamageType`, `SelectOption`, `ParamField`, `PARAM_FIELDS`, `REQUIRED_PARAMETER_KEYS`, `MANUAL_DEFAULT_PARAMETERS`, `PROCESS_DEFAULT_PARAMETERS`, `monthOptions`, `interestTypeOptions`, `periodicityOptions`, `feeTypeOptions`, `prescricaoReferenceOptions`, `compensationTypeOptions`.

## `frontend/src/app/calculation/parameter-panel.component.ts`

Catálogo, agrupamento e visibilidade são decisões de apresentação.

Símbolos exportados: `ParameterPanelComponent`.

## `frontend/src/app/calculation/pdf-viewer.component.ts`

O visualizador consome somente Blob da API, com cancelamento e descarte de URLs.

Símbolos exportados: `PdfViewerComponent`.

## `frontend/src/app/calculation/process-selector.component.ts`

A seleção é vazia no início e mantém a busca sob controle do usuário.

Símbolos exportados: `ProcessSelectorComponent`.

## `frontend/src/app/calculation/result-panel.component.ts`

Resultado e memória exibem apenas valores calculados pelo backend.

Símbolos exportados: `ResultPanelComponent`.

## `frontend/src/app/core/api-errors.ts`

Mensagens comuns distinguem o servidor da aplicação do provedor de extração.

Símbolos exportados: `connectionMessage`.

## `frontend/src/app/core/batch-api.service.ts`

Importação e execução são ações distintas e explicitamente tipadas.

Símbolos exportados: `BatchApiService`.

## `frontend/src/app/core/calculation-api.service.ts`

A interface envia parâmetros; nenhuma matemática jurídica é executada aqui.

Símbolos exportados: `CalculationApiService`.

## `frontend/src/app/core/calculation-mapper.ts`

Único adaptador de formulário camelCase para os contratos snake_case.

Símbolos exportados: `CalculationOrigin`, `ParameterForm`, `InstallmentForm`, `WorkspaceDraft`, `blankDraft`, `decimalText`, `missingFields`, `toCalculationRequest`, `applyExtraction`.

## `frontend/src/app/core/config.ts`

Configuração lida antes de iniciar Angular, sem recompilar por ambiente.

Símbolos exportados: `ApiConfiguration`.

## `frontend/src/app/core/connection-api.service.ts`

Disponibilidade é consultada antes do upload, sem enviar a chave ao navegador.

Símbolos exportados: `ConnectionApiService`.

## `frontend/src/app/core/contracts.ts`

Gerado de docs/openapi.json. Atualize por scripts/generate_contracts.py.

Símbolos exportados: `AiUsage`, `AiUsageSummary`, `BatchImport`, `BatchItem`, `BatchRequest`, `BatchResponse`, `Body_import_batch_api_lotes_importar_post`, `Body_import_installments_api_documentos_parcelas_importar_post`, `Body_upload_api_documentos_upload_post`, `CalculationDefaults`, `CalculationDraft`, `CalculationMetadata`, `CalculationParameters_Input`, `CalculationParameters_Output`, `CalculationPolicyView`, `CalculationRequest`, `CalculationResponse`, `ChronologyDecision`, `DataTable`, `DocumentMetadata`, `ExtractionConfiguration`, `ExtractionRequest`, `ExtractionResult`, `ExtractionStatus`, `FeePreparation`, `FieldEvidence`, `FinancialEvent_Input`, `FinancialEvent_Output`, `HTTPValidationError`, `Health`, `IndexOption`, `IndexStatus`, `Installment_Input`, `Installment_Output`, `OperationalAdjustment`, `ParameterCatalogItem`, `ParameterChangeInput`, `ParameterChangeRecord`, `ParameterOption`, `ProcessSummary`, `SummaryEntry`, `UploadResponse`, `ValidationError`.

## `frontend/src/app/core/document-api.service.ts`

Serviço HTTP do domínio documental.

Símbolos exportados: `DocumentApiService`.

## `frontend/src/app/core/extraction-api.service.ts`

Extrações continuam no servidor mesmo quando o usuário troca de processo.

Símbolos exportados: `ExtractionApiService`.

## `frontend/src/app/core/index-api.service.ts`

Catálogo único é consultado na API.

Símbolos exportados: `IndexApiService`.

## `frontend/src/app/core/notifications.ts`

Notificações podem ser fechadas e não carregam HTML do backend.

Símbolos exportados: `Notifications`, `saveBlob`.

## `frontend/src/app/core/result-presentation.ts`

Rótulos de apresentação: os valores são sempre os retornados pelo motor.

Símbolos exportados: `summaryRows`, `finalTotal`.

## `frontend/src/app/core/revision-audit-api.service.ts`

Trilha de revisão humana; nenhum cálculo é executado neste serviço.

Símbolos exportados: `RevisionAuditApiService`.

## `frontend/src/app/core/workspace.store.ts`

Estado visual e rascunhos vivem no Angular; SQLite recebe somente estado de negócio.

Símbolos exportados: `WorkspaceStore`.

## `frontend/src/app/indices/indices-page.component.ts`

Estado de atualização é consultado no servidor; não há sucesso presumido.

Símbolos exportados: `IndicesPageComponent`.

## `frontend/src/app/shared/notifications.component.ts`

Região acessível de avisos com fechamento individual.

Símbolos exportados: `NotificationsComponent`.

## `frontend/src/app/templates/application-template-page.component.ts`

Página template reutilizável para aplicações futuras do sistema.

Símbolos exportados: `ApplicationTemplatePageComponent`.

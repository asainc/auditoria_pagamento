# Referência do código

> Arquivo gerado automaticamente por `scripts/generate_code_reference.py`.
> As descrições vêm das docstrings/comentários do source; não edite este arquivo manualmente.

## Como ler esta referência

Use esta referência para localizar responsabilidades. Para entender a sequência de execução, consulte `FLUXO_CALCULO.md`; para contratos e valores padrão, consulte `PARAMETROS.md`.

# Python

## `backend/__init__.py`

Inicialização mínima do pacote backend para execução corporativa sem virtualenv.

Este módulo não expõe classes ou funções de nível superior.

## `backend/access.py`

Publicação protegida por gateway autenticado; local usa apenas loopback.

### `def require_access(request: Request) -> None`

Cabeçalho é inserido pelo gateway, nunca enviado ao navegador como segredo.

**Entrada:** `request: Request`.

**Saída:** `None`.

### `def technical_actor(request: Request) -> str`

Deriva identificador técnico estável sem persistir a identidade pessoal em claro.

**Entrada:** `request: Request`.

**Saída:** `str`.

## `backend/calculation_identity.py`

Normalização determinística das identidades usadas no histórico de cálculos.

### `def normalize_process_number(value: str) -> str`

Retorna somente os dígitos para comparar processos sem depender de pontuação.

**Entrada:** `value: str`.

**Saída:** `str`.

### `def display_process_number(value: str) -> str`

Aplica a máscara CNJ quando houver exatamente vinte dígitos.

**Entrada:** `value: str`.

**Saída:** `str`.

### `def normalize_manual_identifier(value: str) -> str`

Normaliza o identificador manual para comparação sem alterar o rótulo exibido.

**Entrada:** `value: str`.

**Saída:** `str`.

## `backend/calculation_policy.py`

Catálogo e padrões centrais do cálculo.

### `class CalculationPolicyConfigurationError(RuntimeError)`

Indica erro estrutural na política versionada da aplicação.


### `def load_calculation_policy() -> dict[str, Any]`

Carrega e valida a estrutura mínima da política de cálculo.

**Entrada:** nenhuma entrada explícita.

**Saída:** `dict[str, Any]`.

### `def parameter_catalog() -> list[dict[str, Any]]`

Retorna cópia rasa do catálogo central de parâmetros.

**Entrada:** nenhuma entrada explícita.

**Saída:** `list[dict[str, Any]]`.

### `def parameter_keys() -> tuple[str, ...]`

Retorna as chaves na ordem usada pela interface e pela documentação.

**Entrada:** nenhuma entrada explícita.

**Saída:** `tuple[str, ...]`.

### `def required_parameter_keys() -> tuple[str, ...]`

Retorna os campos mínimos necessários para disparar o motor.

**Entrada:** nenhuma entrada explícita.

**Saída:** `tuple[str, ...]`.

### `def parameter_label(key: str) -> str`

Converte uma chave técnica no rótulo oficial da aplicação.

**Entrada:** `key: str`.

**Saída:** `str`.

### `def defaults_for_origin(origin: CalculationOrigin) -> dict[str, Any]`

Retorna os valores padrão efetivos para a origem informada.

**Entrada:** `origin: CalculationOrigin`.

**Saída:** `dict[str, Any]`.

### `def apply_missing_defaults(parameters: dict[str, Any], origin: CalculationOrigin) -> dict[str, Any]`

Completa somente campos ausentes; valores explícitos nunca são sobrescritos.

**Entrada:** `parameters: dict[str, Any]`, `origin: CalculationOrigin`.

**Saída:** `dict[str, Any]`.

### `def policy_hash() -> str`

Retorna SHA-256 canônico da política efetivamente carregada.

**Entrada:** nenhuma entrada explícita.

**Saída:** `str`.

## `backend/config.py`

Configuração validada; erros não são substituídos silenciosamente por padrões.

### `class OperationalSettings(Contract)`

Visão tipada dos padrões documentais definidos no catálogo central.

**Atributos declarados:** `default_index: str`, `default_moratory_type: InterestType`, `default_art_523: Literal['nao_aplicar', 'aplicar_multa', 'aplicar_multa_honorarios']`.


### `class Settings(Contract)`

Parâmetros operacionais centralizados; segredos vêm do ambiente.

**Atributos declarados:** `environment: str`, `operational: OperationalSettings`, `data_dir: Path`, `cors_origins: list[str]`, `max_upload_bytes: int`, `max_upload_files: int`, `extraction_workers: int`, `bradesco_environment: Literal['dev', 'homol', 'prod']`, `bradesco_identificador: SecretStr`, `bradesco_senha: SecretStr`, `bradesco_authorization_token: SecretStr`, `bradesco_ca_bundle: Path | None`, `bradesco_text_url: str`, `bradesco_identity_url: str`, `bradesco_timeout_seconds: int`, `bradesco_text_model: str`, `bradesco_text_temperature: float`, `bradesco_text_max_tokens: int`, `bradesco_prompt_max_chars: int`, `extraction_max_pages_per_task: int`, `extraction_fallback_pages_per_document: int`, `extraction_max_attempts: int`, `extraction_retry_delay_seconds: int`, `extraction_lease_seconds: int`, `ai_finops_cache_enabled: bool`, `ai_finops_cache_ttl_days: int`, `ai_finops_max_calls_per_job: int`, `ai_finops_max_input_chars_per_job: int`, `ai_finops_input_usd_per_million_tokens: Decimal | None`, `ai_finops_output_usd_per_million_tokens: Decimal | None`, `ai_finops_cached_input_usd_per_million_tokens: Decimal | None`, `ai_finops_monthly_budget_usd: Decimal | None`, `ai_finops_budget_warning_ratio: Decimal`, `ai_finops_enforce_monthly_budget: bool`, `learning_examples_enabled: bool`, `learning_max_examples_per_task: int`, `learning_max_chars_per_task: int`, `gateway_token: SecretStr`, `index_timeout_seconds: int`.

**Métodos:**

- `def validate_origins(cls, values: list[str]) -> list[str]` — Uma origem explícita evita conceder acesso CORS a sites arbitrários.
  - Entrada: `values: list[str]`.
  - Saída: `list[str]`.
- `def require_gateway(self) -> Settings` — Publicação depende do gateway autenticado; não há login paralelo na UI.
  - Entrada: nenhuma entrada explícita.
  - Saída: `Settings`.

### `def load_settings() -> Settings`

Prioridade: ambiente > .env > JSON > padrões; segredos corporativos não são persistidos.

**Entrada:** nenhuma entrada explícita.

**Saída:** `Settings`.

## `backend/container.py`

Monta os objetos compartilhados pela API e controla o ciclo de vida deles.

### `class Services`

Agrupa serviços e repositórios que pertencem à mesma execução da API.

**Métodos:**

- `def __init__(self, settings: Settings, provider: ExtractionProvider | None=None) -> None` — Cria banco, repositórios e serviços em uma ordem explícita.
  - Entrada: `settings: Settings`, `provider: ExtractionProvider | None`.
  - Saída: `None`.
- `def close(self) -> None` — Encerra recursos que mantêm threads abertas.
  - Entrada: nenhuma entrada explícita.
  - Saída: `None`.

### `def services(request: Request) -> Services`

Obtém a composição de serviços pertencente à aplicação FastAPI atual.

**Entrada:** `request: Request`.

**Saída:** `Services`.

## `backend/contracts/__init__.py`

Exportações explícitas dos contratos por domínio.

Este módulo não expõe classes ou funções de nível superior.

## `backend/contracts/audit.py`

Contratos da trilha de revisão humana.

### `class ParameterChangeInput(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `origem_calculo: CalculationOrigin`, `numero_processo: ProcessId | None`, `rascunho_id: str`, `campo: str`, `valor_anterior: Scalar`, `valor_novo: Scalar`, `extracao_id: str | None`.

**Métodos:**

- `def validate_change(self) -> 'ParameterChangeInput'` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `'ParameterChangeInput'`.

### `class ParameterChangeRecord(ParameterChangeInput)`

Sem descrição específica no código.

**Atributos declarados:** `identificador: int`, `registrado_em: str`, `ator_tecnico: str`, `valor_extraido: Scalar`, `origem_extraida: str | None`.


## `backend/contracts/base.py`

Tipos e contrato-base compartilhados entre os domínios da API.

### `class Contract(BaseModel)`

Base fechada para impedir campos desconhecidos e coerções silenciosas.

**Atributos declarados:** `model_config: tipo inferido em execução`.


## `backend/contracts/batch.py`

Contratos de execução e importação em lote.

### `class BatchRequest(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `processos: list[CalculationRequest]`.


### `class BatchItem(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `numero_processo: str | None`, `resultado: VersionedCalculationResponse | None`, `erro: str | None`.


### `class BatchResponse(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `resultados: list[BatchItem]`.


### `class BatchImport(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `processos: list[CalculationDraft]`, `erros: list[str]`.


## `backend/contracts/calculation.py`

Exportações centrais dos contratos relacionados ao domínio de cálculo.

Este módulo não expõe classes ou funções de nível superior.

## `backend/contracts/calculation_history.py`

Contratos de versionamento, execução, artefatos e histórico.

### `class CalculationVersionRef(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `calculo_id: str`, `versao: int`, `versao_base: int | None`, `criado_em: str`, `criada: bool`.


### `class CalculationExecutionRef(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `execucao_id: str`, `calculo_id: str`, `versao: int`, `executada_em: str`, `nova_versao: bool`.


### `class VersionedCalculationResponse(CalculationResponse)`

Sem descrição específica no código.

**Atributos declarados:** `registro: CalculationVersionRef | None`, `execucao: CalculationExecutionRef | None`.


### `class CalculationFieldDiff(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `caminho: str`, `valor_anterior: Scalar`, `valor_novo: Scalar`.


### `class InstallmentDiff(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `posicao: int`, `acao: Literal['adicionada', 'removida', 'alterada']`, `campos_alterados: list[str]`, `antes: Installment | None`, `depois: Installment | None`.


### `class CalculationDiff(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `campos: list[CalculationFieldDiff]`, `parcelas: list[InstallmentDiff]`.


### `class CalculationExecutionSummary(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `execucao_id: str`, `versao: int`, `executada_em: str`, `executada_por: str`, `entrada_sha256: str`, `politica_sha256: str`, `motor_sha256: str`, `indices_sha256: str`, `duracao_ms: float`.


### `class CalculationExecutionsPage(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `calculo_id: str`, `versao: int`, `itens: list[CalculationExecutionSummary]`, `pagina: int`, `tamanho_pagina: int`, `total_itens: int`, `total_paginas: int`.


### `class CalculationVersionSummary(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `versao: int`, `versao_base: int | None`, `criado_em: str`, `criado_por: str`, `total_geral: str | None`, `indice: str`, `competencia_atualizacao: str`, `entrada_sha256: str`, `indices_sha256: str`, `campos_alterados: list[str]`, `diff: CalculationDiff`, `quantidade_execucoes: int`, `ultima_execucao_em: str | None`.


### `class CalculationHistoryItem(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `calculo_id: str`, `origem_calculo: CalculationOrigin`, `identificador_calculo: str`, `numero_processo: str | None`, `numero_processo_normalizado: str | None`, `estado: CalculationState`, `criado_em: str`, `criado_por: str`, `atualizado_em: str`, `quantidade_versoes: int`, `quantidade_execucoes: int`, `versao_atual: int`, `total_atual: str | None`, `indice_atual: str`, `competencia_atualizacao_atual: str`.


### `class CalculationHistoryPage(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `itens: list[CalculationHistoryItem]`, `pagina: int`, `tamanho_pagina: int`, `total_itens: int`, `total_paginas: int`.


### `class CalculationVersionsPage(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `calculo_id: str`, `itens: list[CalculationVersionSummary]`, `pagina: int`, `tamanho_pagina: int`, `total_itens: int`, `total_paginas: int`.


### `class CalculationVersionDetail(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `calculo_id: str`, `origem_calculo: CalculationOrigin`, `identificador_calculo: str`, `numero_processo: str | None`, `estado_calculo: CalculationState`, `versao: int`, `versao_atual: int`, `versao_base: int | None`, `criado_em: str`, `criado_por: str`, `campos_alterados: list[str]`, `diff: CalculationDiff`, `quantidade_execucoes: int`, `requisicao: CalculationRequest`, `resultado: CalculationResponse`.


### `class CalculationComparison(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `calculo_id: str`, `versao_origem: int`, `versao_destino: int`, `total_origem: str | None`, `total_destino: str | None`, `diferenca_total: str | None`, `diff: CalculationDiff`.


### `class CalculationStateChange(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `estado: CalculationState`.


### `class CalculationStateResult(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `calculo_id: str`, `estado: CalculationState`, `atualizado_em: str`.


## `backend/contracts/calculation_input.py`

Contratos de entrada de cálculo e preparação de parcelas.

### `class Installment(Contract)`

Parcela revisada e congelada dentro de uma versão.

**Atributos declarados:** `data: date`, `valor_singelo: Money`, `descricao: str`, `verba_tipo: DamageType`, `multiplicador: Literal[1, 2] | None`, `origem: Literal['informada', 'honorarios_dano_moral']`.


### `class CalculationDraft(Contract)`

Entrada completa antes da confirmação humana definitiva.

**Atributos declarados:** `origem_calculo: CalculationOrigin`, `numero_processo: ProcessId | None`, `identificador_calculo: CalculationIdentifier | None`, `parcelas: list[Installment]`, `parametros: CalculationParameters`, `parametros_por_dano: DamageParameters | None`, `revisao_humana_confirmada: bool`, `honorarios_sobre_danos_morais: bool`, `competencia_automatica: bool`.

**Métodos:**

- `def apply_origin_defaults(cls, raw: object) -> object` — Normaliza identidade e aplica padrões oficiais antes da validação.
  - Entrada: `raw: object`.
  - Saída: `object`.
- `def validate_origin_identity(self) -> 'CalculationDraft'` — Garante uma única identidade de negócio por origem.
  - Entrada: nenhuma entrada explícita.
  - Saída: `'CalculationDraft'`.

### `class CalculationRequest(CalculationDraft)`

Sem descrição específica no código.

**Atributos declarados:** `revisao_humana_confirmada: Literal[True]`.


### `class FeePreparation(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `parcelas: list[Installment]`, `percentual: Rate`.


## `backend/contracts/calculation_output.py`

Contratos de saída do motor e recomendações operacionais.

### `class DataTable(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `colunas: list[str]`, `linhas: list[list[Scalar]]`.


### `class SummaryEntry(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `campo: str`, `valor: str`.


### `class CalculationMetadata(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `entrada_sha256: str`, `politica_sha256: str`, `motor_sha256: str`, `indices_sha256: str`, `duracao_ms: float`, `revisao_humana_confirmada: bool`.


### `class CalculationResponse(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `origem_calculo: CalculationOrigin`, `numero_processo: str | None`, `identificador_calculo: str`, `memoria: DataTable`, `resumo: list[SummaryEntry]`, `parametros: CalculationParameters`, `parametros_por_dano: DamageParameters`, `metadata: CalculationMetadata`.


### `class CalculationDefaults(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `mes: Month`, `ano: int`, `competencia_recomendada: str | None`, `ajustada_por_disponibilidade: bool`, `mensagem: str | None`.


## `backend/contracts/calculation_parameters.py`

Contratos dos parâmetros de cálculo, separados do transporte HTTP.

### `class MonetaryUpdateParameters(Contract)`

Atualização monetária e competência de cálculo.

**Atributos declarados:** `mes_atualizacao: Month`, `ano_atualizacao: int`, `indice: str`, `deflacionar_valor_nominal: bool | None`, `competencia_final_taxa_legal: str | None`.


### `class MoratoryInterestParameters(Contract)`

Juros moratórios.

**Atributos declarados:** `juros_moratorios_tipo: InterestType`, `juros_moratorios_taxa: Rate | None`, `juros_moratorios_periodicidade: Periodicity | None`, `juros_moratorios_pro_rata: bool | None`, `juros_moratorios_data_inicio: date | None`.


### `class DamageFinancialCriteria(MonetaryUpdateParameters, MoratoryInterestParameters)`

Critérios financeiros próprios de uma natureza de dano.


### `class DamageParameters(Contract)`

Critérios independentes para dano material e dano moral.

**Atributos declarados:** `dano_material: DamageFinancialCriteria`, `dano_moral: DamageFinancialCriteria`.


### `class PenaltyAndFeeParameters(Contract)`

Multa, honorários e art. 523 com modalidade explicitamente tipada.

**Atributos declarados:** `incidir_multa_sobre_juros_moratorios: bool | None`, `incidir_multa_sobre_parcelas_a_vencer: bool | None`, `incidir_honorarios_sobre_multa: bool | None`, `multa_valor: FlexibleAmount | None`, `multa_tipo: Literal['percentual', 'fixo'] | None`, `honorarios: FlexibleAmount | None`, `honorarios_tipo: Literal['percentual', 'fixo'] | None`, `art_523: Literal['nao_aplicar', 'aplicar_multa', 'aplicar_multa_honorarios'] | None`.


### `class PrescriptionParameters(Contract)`

Prescrição e referência temporal.

**Atributos declarados:** `prescricao_flag: bool | None`, `prescricao_anos: int | None`, `prescricao_data_referencia_tipo: Literal['data_ajuizamento', 'data_decisao', 'data_ultima_parcela'] | None`, `prescricao_data_referencia: date | None`.


### `class CompensationParameters(Contract)`

Compensação percentual ou fixa.

**Atributos declarados:** `compensacao_flag: bool | None`, `compensacao_tipo_calculo: Literal['percentual', 'fixo'] | None`, `compensacao_valor: FlexibleAmount | None`.


### `class DualIndexParameters(Contract)`

Dois intervalos de correção monetária.

**Atributos declarados:** `duplo_indice_flag: bool | None`, `duplo_indice_primeiro_indice: str | None`, `duplo_indice_primeiro_data_inicio: date | None`, `duplo_indice_primeiro_data_fim: date | None`, `duplo_indice_primeiro_valor_parcela: Money | None`, `duplo_indice_segundo_indice: str | None`, `duplo_indice_segundo_data_inicio: date | None`, `duplo_indice_segundo_data_fim: date | None`, `duplo_indice_segundo_valor_parcela: Money | None`.


### `class CalculationParameters(MonetaryUpdateParameters, MoratoryInterestParameters, PenaltyAndFeeParameters, PrescriptionParameters, CompensationParameters, DualIndexParameters)`

Contrato externo composto; o domínio interno usa uma representação aninhada.

**Atributos declarados:** `valor_dobrado_flag: bool | None`.

**Métodos:**

- `def require_active_fields(self) -> 'CalculationParameters'` — Valida apenas dependências estruturais dos grupos habilitados.
  - Entrada: nenhuma entrada explícita.
  - Saída: `'CalculationParameters'`.

## `backend/contracts/document.py`

Contratos do domínio documental.

### `class DocumentMetadata(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `identificador: str`, `numero_processo: str`, `nome: str`, `sha256: str`, `tamanho_bytes: int`, `paginas: int`, `classificacao: str`.


### `class ProcessSummary(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `numero_processo: str`, `quantidade_documentos: int`.


## `backend/contracts/extraction.py`

Contratos de extração, evidência e política de parâmetros.

### `class AiUsage(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `etapa: str`, `modelo: str`, `tokens_entrada: int | None`, `tokens_entrada_cache: int | None`, `tokens_saida: int | None`, `tokens_total: int | None`, `tokens_estimados_entrada: int | None`, `tokens_estimados_saida: int | None`, `origem_tokens: Literal['gateway', 'estimativa_local', 'cache', 'indisponivel']`, `custo_estimado_usd: Decimal | None`, `duracao_ms: float`, `paginas_contexto: int | None`, `caracteres_entrada: int | None`, `caracteres_saida: int | None`, `cache_hit: bool`, `request_sha256: str | None`, `correcao_estrutural: bool`.


### `class AiUsageSummary(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `chamadas: int`, `chamadas_api: int`, `acertos_cache: int`, `tokens_entrada: int | None`, `tokens_entrada_cache: int | None`, `tokens_saida: int | None`, `tokens_total: int | None`, `tokens_estimados_total: int | None`, `custo_estimado_usd: Decimal | None`, `duracao_total_ms: float`, `detalhamento: list[AiUsage]`.


### `class ExtractionRequest(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `numero_processo: ProcessId`.


### `class ExtractionStatus(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `numero_processo: str`, `identificador: str`, `estado: Literal['aguardando', 'executando', 'pronto', 'falha', 'bloqueada', 'interrompida']`, `etapa: str`, `mensagem: str`, `atualizado_em: str`, `codigo_erro: str | None`, `uso_ia: AiUsageSummary | None`.


### `class ExtractionConfiguration(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `provedor: Literal['bradesco_iagen']`, `configurada: bool`, `modelo: str`, `mensagem: str`, `leitura_documental: str`, `tokens_disponiveis: bool`, `custo_disponivel: bool`.


### `class UploadResponse(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `documentos: list[DocumentMetadata]`, `extracoes: list[ExtractionStatus]`.


### `class FieldEvidence(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `campo: str`, `valor: Scalar`, `documento: str`, `pagina: int`, `trecho: str`, `escopo: Literal['caso_concreto', 'jurisprudencia_citada', 'indeterminado']`, `natureza: EvidenceNature`, `efeito: EvidenceEffect`.


### `class OperationalAdjustment(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `campo: str`, `valor: Scalar`, `motivo: str`.


### `class ChronologyDecision(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `campo: str`, `valor: Scalar`, `documento: str`, `pagina: int`, `sequencia: int`, `natureza: EvidenceNature`, `efeito: EvidenceEffect`, `motivo: str`.


### `class ExtractionResult(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `numero_processo: str`, `campos: list[FieldEvidence]`, `parcelas: list[Installment]`, `alertas: list[str]`, `versao_prompts: str`, `parametros_consolidados: dict[str, Scalar]`, `decisoes_cronologicas: list[ChronologyDecision]`, `ajustes_operacionais: list[OperationalAdjustment]`, `honorarios_sobre_danos_morais: bool`, `competencia_automatica: bool`, `uso_ia: AiUsageSummary | None`.


### `class ParameterOption(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `value: Scalar`, `label: str`, `hidden: bool`.


### `class ParameterCatalogItem(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `key: str`, `label: str`, `type: Literal['text', 'number', 'date', 'select', 'checkbox']`, `section: str`, `options: list[ParameterOption] | None`, `help: str | None`, `damageTypes: list[DamageType] | None`.


### `class CalculationPolicyView(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `origem_calculo: CalculationOrigin`, `parametros_padrao: dict[str, Scalar]`, `campos_obrigatorios: list[str]`, `catalogo: list[ParameterCatalogItem]`.


## `backend/contracts/index.py`

Contratos do catálogo e atualização de índices.

### `class IndexOption(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `chave: str`, `nome: str`, `nome_base: str`, `disponivel: bool`, `modo: Literal['rate_decimal', 'value_index', 'sem_correcao', 'indisponivel']`, `competencia_inicial: str | None`, `competencia_final: str | None`, `competencia_maxima_atualizacao: str | None`.


### `class IndexStatus(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `estado: Literal['nao_verificado', 'atualizado', 'sem_novidade', 'falha', 'executando']`, `mensagem: str`, `atualizado_em: str | None`, `arquivos_sha256: dict[str, str]`.


## `backend/contracts/quality.py`

Contratos de aprendizado supervisionado e qualidade da extração.

### `class ReviewSnapshotInput(Contract)`

Snapshot do estado revisado usado para comparar IA × humano no servidor.

**Atributos declarados:** `origem_calculo: CalculationOrigin`, `numero_processo: ProcessId | None`, `rascunho_id: str`, `extracao_id: str | None`, `parametros: dict[str, Scalar]`, `parametros_por_dano: dict[str, dict[str, Scalar]]`, `parcelas: list[Installment]`.


### `class FeedbackEventRecord(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `identificador: str`, `numero_processo: str | None`, `rascunho_id: str`, `extracao_id: str | None`, `campo: str`, `acao: FeedbackAction`, `motivo_codigo: FeedbackReasonCode`, `comentario: str | None`, `valor_modelo: Scalar`, `valor_humano: Scalar`, `documento: str | None`, `pagina: int | None`, `evidencia_modelo: str | None`, `tipo_documento: str | None`, `versao_prompts: str | None`, `modelo: str | None`, `pipeline_version: str`, `revisor_pseudonimo: str`, `criado_em: str`, `status_curadoria: CurationStatus`.


### `class ReviewCaptureResult(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `eventos_criados: int`, `confirmados: int`, `corrigidos: int`, `pendentes_curadoria: int`.


### `class FeedbackCurationInput(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `status: Literal['approved', 'rejected']`, `motivo_codigo: FeedbackReasonCode | None`, `comentario: str | None`.


### `class FeedbackFieldMetric(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `campo: str`, `total: int`, `confirmados: int`, `corrigidos: int`, `removidos: int`, `adicionados: int`, `taxa_intervencao: Decimal`.


### `class FeedbackReasonMetric(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `motivo_codigo: str`, `quantidade: int`.


### `class QualitySummary(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `total_eventos: int`, `confirmados: int`, `corrigidos: int`, `removidos: int`, `adicionados: int`, `pendentes_curadoria: int`, `taxa_intervencao: Decimal`, `por_campo: list[FeedbackFieldMetric]`, `motivos: list[FeedbackReasonMetric]`.


### `class FeedbackPage(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `itens: list[FeedbackEventRecord]`, `pagina: int`, `tamanho_pagina: int`, `total_itens: int`, `total_paginas: int`.


### `class DatasetSnapshot(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `identificador: str`, `criado_em: str`, `criado_por: str`, `sha256: str`, `quantidade_exemplos: int`.


### `class LearningExample(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `campo: str`, `tarefa: str`, `evidencia: str | None`, `valor_modelo: Scalar`, `valor_esperado: Scalar`, `motivo_codigo: str`.


### `class FinOpsStageMetric(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `etapa: str`, `chamadas_api: int`, `falhas_api: int`, `acertos_cache: int`, `caracteres_entrada: int`, `caracteres_saida: int`, `tokens_reais: int | None`, `tokens_estimados: int`, `custo_estimado_usd: Decimal | None`.


### `class FinOpsSummary(Contract)`

Sem descrição específica no código.

**Atributos declarados:** `periodo_dias: int`, `chamadas_api: int`, `falhas_api: int`, `acertos_cache: int`, `taxa_cache: Decimal`, `caracteres_entrada: int`, `caracteres_saida: int`, `tokens_reais: int | None`, `tokens_estimados: int`, `custo_estimado_usd: Decimal | None`, `origem_tokens: Literal['gateway', 'estimativa_local', 'mista', 'cache', 'indisponivel']`, `economia_chamadas_cache: int`, `orcamento_mensal_usd: Decimal | None`, `consumo_mes_estimado_usd: Decimal | None`, `percentual_orcamento: Decimal | None`, `status_orcamento: Literal['not_configured', 'unavailable', 'ok', 'warning', 'exceeded']`, `por_etapa: list[FinOpsStageMetric]`.


## `backend/domain/__init__.py`

Modelos de domínio independentes dos contratos HTTP.

Este módulo não expõe classes ou funções de nível superior.

## `backend/domain/calculation_parameters.py`

Modelo de domínio dos parâmetros jurídico-financeiros.

### `class AmountRule`

Valor percentual ou monetário com semântica explícita e mutuamente exclusiva.

**Atributos declarados:** `tipo: Literal['percentual', 'fixo']`, `percentual: Decimal | None`, `valor_fixo: Decimal | None`.

**Métodos:**

- `def build(cls, tipo: str | None, valor: Decimal | None) -> 'AmountRule | None'` — Converte o par tipo/valor sem misturar taxa percentual e dinheiro no domínio.
  - Entrada: `tipo: str | None`, `valor: Decimal | None`.
  - Saída: `'AmountRule | None'`.

### `class MonetaryUpdateRule`

Critério e competência de atualização monetária.

**Atributos declarados:** `mes: str`, `ano: int`, `indice: str`, `deflacionar: bool | None`, `competencia_final_taxa_legal: str | None`.


### `class InterestRule`

Regra de juros com todos os atributos que pertencem ao mesmo conceito.

**Atributos declarados:** `tipo: str`, `taxa: Decimal | None`, `periodicidade: str | None`, `pro_rata: bool | None`, `data_inicio: date | None`.


### `class PrescriptionRule`

Configuração da prescrição; campos inativos permanecem nulos.

**Atributos declarados:** `ativa: bool`, `anos: int | None`, `referencia_tipo: str | None`, `referencia: date | None`.


### `class DualIndexSegment`

Um intervalo fechado de uma regra de duplo índice.

**Atributos declarados:** `indice: str | None`, `inicio: date | None`, `fim: date | None`, `valor_parcela: Decimal | None`.


### `class DualIndexRule`

Regra completa de dois índices com dois segmentos explícitos.

**Atributos declarados:** `ativo: bool`, `primeiro: DualIndexSegment`, `segundo: DualIndexSegment`.


### `class NormalizedCalculationParameters`

Visão interna orientada ao domínio; não é serializada diretamente na API.

**Atributos declarados:** `atualizacao: MonetaryUpdateRule`, `juros_moratorios: InterestRule`, `multa: AmountRule | None`, `honorarios: AmountRule | None`, `compensacao: AmountRule | None`, `prescricao: PrescriptionRule`, `duplo_indice: DualIndexRule`, `art_523: str | None`, `valor_dobrado: bool`, `contrato_flat: dict[str, object]`.


### `def _decimal(value: object | None) -> Decimal | None`

Normaliza numerais Pydantic para Decimal sem introduzir float.

**Entrada:** `value: object | None`.

**Saída:** `Decimal | None`.

### `def normalize_parameters(parameters: CalculationParameters) -> NormalizedCalculationParameters`

Converte o contrato plano em grupos coesos sem alterar a entrada do motor.

**Entrada:** `parameters: CalculationParameters`.

**Saída:** `NormalizedCalculationParameters`.

## `backend/errors.py`

Erros públicos estruturados, estáveis e sem conteúdo sensível.

### `class ErrorField`

Erro associado a um campo sem repetir o valor recebido.

**Atributos declarados:** `field: str`, `message: str`, `type: str | None`.


### `class ServiceError(Exception)`

Falha esperada com código de máquina e mensagem segura para a interface.

**Métodos:**

- `def __init__(self, message: str, status_code: int=422, *, code: str='DOMAIN_ERROR', fields: Iterable[ErrorField] | None=None, retryable: bool=False) -> None` — Sem descrição específica no código.
  - Entrada: `message: str`, `status_code: int`, `code: str`, `fields: Iterable[ErrorField] | None`, `retryable: bool`.
  - Saída: `None`.
- `def payload(self, request_id: str | None=None) -> dict[str, object]` — Serializa somente metadados públicos previamente controlados.
  - Entrada: `request_id: str | None`.
  - Saída: `dict[str, object]`.

## `backend/models.py`

Ponto central de importação dos contratos usados pelo backend e pelos testes.

Este módulo não expõe classes ou funções de nível superior.

## `backend/persistence/__init__.py`

Infraestrutura de banco local: conexão SQLite e criação/migração do esquema.

Este módulo não expõe classes ou funções de nível superior.

## `backend/persistence/schema.py`

Schema e migrações idempotentes do banco de negócio.

### `def timestamp() -> str`

UTC torna eventos comparáveis entre instalações.

**Entrada:** nenhuma entrada explícita.

**Saída:** `str`.

### `def _business_state(payload: dict) -> dict`

Sem descrição específica no código.

**Entrada:** `payload: dict`.

**Saída:** `dict`.

### `def business_hash(payload: dict) -> str`

Hash canônico exclusivo do estado funcional do cálculo.

**Entrada:** `payload: dict`.

**Saída:** `str`.

### `def full_diff(previous: dict | None, current: dict) -> CalculationDiff`

Diff completo entre parâmetros e parcelas de duas versões.

**Entrada:** `previous: dict | None`, `current: dict`.

**Saída:** `CalculationDiff`.

### `def _changed_fields(diff: CalculationDiff) -> list[str]`

Sem descrição específica no código.

**Entrada:** `diff: CalculationDiff`.

**Saída:** `list[str]`.

### `def _table_exists(connection: sqlite3.Connection, name: str) -> bool`

Sem descrição específica no código.

**Entrada:** `connection: sqlite3.Connection`, `name: str`.

**Saída:** `bool`.

### `def _columns(connection: sqlite3.Connection, table: str) -> set[str]`

Sem descrição específica no código.

**Entrada:** `connection: sqlite3.Connection`, `table: str`.

**Saída:** `set[str]`.

### `def _base_schema(connection: sqlite3.Connection) -> None`

Sem descrição específica no código.

**Entrada:** `connection: sqlite3.Connection`.

**Saída:** `None`.

### `def _parameter_changes_ddl(table: str='parameter_changes') -> str`

Sem descrição específica no código.

**Entrada:** `table: str`.

**Saída:** `str`.

### `def _ensure_parameter_changes(connection: sqlite3.Connection) -> None`

Sem descrição específica no código.

**Entrada:** `connection: sqlite3.Connection`.

**Saída:** `None`.

### `def _ensure_calculation_records(connection: sqlite3.Connection) -> None`

Sem descrição específica no código.

**Entrada:** `connection: sqlite3.Connection`.

**Saída:** `None`.

### `def _create_normalized_calculation_tables(connection: sqlite3.Connection) -> None`

Sem descrição específica no código.

**Entrada:** `connection: sqlite3.Connection`.

**Saída:** `None`.

### `def _insert_artifact(connection: sqlite3.Connection, execution_id: str, kind: str, content: bytes, created_at: str) -> None`

Sem descrição específica no código.

**Entrada:** `connection: sqlite3.Connection`, `execution_id: str`, `kind: str`, `content: bytes`, `created_at: str`.

**Saída:** `None`.

### `def _normalize_calculation_storage(connection: sqlite3.Connection) -> None`

Migra versões/execuções com BLOBs duplicados para execução + artefato.

**Entrada:** `connection: sqlite3.Connection`.

**Saída:** `None`.

### `def _ensure_learning_and_finops(connection: sqlite3.Connection) -> None`

Cria estruturas imutáveis de feedback supervisionado e FinOps da IA.

**Entrada:** `connection: sqlite3.Connection`.

**Saída:** `None`.

### `def _indexes(connection: sqlite3.Connection) -> None`

Sem descrição específica no código.

**Entrada:** `connection: sqlite3.Connection`.

**Saída:** `None`.

### `def migrate(database: SQLiteDatabase) -> None`

Aplica migrações antes de os serviços iniciarem.

**Entrada:** `database: SQLiteDatabase`.

**Saída:** `None`.

## `backend/persistence/sqlite.py`

Infraestrutura SQLite compartilhada pelos repositórios especializados.

### `class SQLiteDatabase`

Cria conexões curtas; nenhuma conexão é compartilhada entre threads.

**Métodos:**

- `def __init__(self, data_dir: Path) -> None` — Sem descrição específica no código.
  - Entrada: `data_dir: Path`.
  - Saída: `None`.
- `def connect(self, *, isolation_level: str | None='DEFERRED', foreign_keys: bool=True) -> sqlite3.Connection` — Sem descrição específica no código.
  - Entrada: `isolation_level: str | None`, `foreign_keys: bool`.
  - Saída: `sqlite3.Connection`.
- `def connection(self) -> Iterator[sqlite3.Connection]` — Commit ou rollback integral da operação corrente.
  - Entrada: nenhuma entrada explícita.
  - Saída: `Iterator[sqlite3.Connection]`.
- `def immediate(self) -> Iterator[sqlite3.Connection]` — Serializa decisões concorrentes que dependem do estado mais recente.
  - Entrada: nenhuma entrada explícita.
  - Saída: `Iterator[sqlite3.Connection]`.

## `backend/principal.py`

Única inicialização FastAPI; não hospeda o frontend da aplicação.

### `class Health(Contract)`

Identifica disponibilidade da API e sua versão de contrato.

**Atributos declarados:** `status: str`, `versao_api: str`.


### `class AuditFormatter(logging.Formatter)`

Logs estruturados contêm apenas metadados técnicos selecionados.

**Métodos:**

- `def format(self, record: logging.LogRecord) -> str` — Seleciona metadados de auditoria sem serializar conteúdo de requisições.
  - Entrada: `record: logging.LogRecord`.
  - Saída: `str`.

### `def create_app(settings: Settings | None=None, provider: ExtractionProvider | None=None) -> FastAPI`

Cria uma instância FastAPI com configuração e dependências explicitamente injetáveis.

**Entrada:** `settings: Settings | None`, `provider: ExtractionProvider | None`.

**Saída:** `FastAPI`.

## `backend/repositories/__init__.py`

Repositórios que leem e gravam cada grupo de dados persistidos pela aplicação.

Este módulo não expõe classes ou funções de nível superior.

## `backend/repositories/ai_operations_repository.py`

Persistência de telemetria FinOps e cache determinístico de respostas estruturadas.

### `class AiOperationsRepository`

Sem descrição específica no código.

**Métodos:**

- `def __init__(self, database: SQLiteDatabase) -> None` — Sem descrição específica no código.
  - Entrada: `database: SQLiteDatabase`.
  - Saída: `None`.
- `def cached_response(self, request_sha256: str, model: str, *, ttl_days: int=30) -> str | None` — Sem descrição específica no código.
  - Entrada: `request_sha256: str`, `model: str`, `ttl_days: int`.
  - Saída: `str | None`.
- `def cache_response(self, request_sha256: str, model: str, stage: str, response_json: str) -> None` — Sem descrição específica no código.
  - Entrada: `request_sha256: str`, `model: str`, `stage: str`, `response_json: str`.
  - Saída: `None`.
- `def record_usage(self, payload: dict) -> None` — Sem descrição específica no código.
  - Entrada: `payload: dict`.
  - Saída: `None`.
- `def job_api_consumption(self, job: str) -> tuple[int, int]` — Sem descrição específica no código.
  - Entrada: `job: str`.
  - Saída: `tuple[int, int]`.
- `def current_month_cost(self) -> Decimal | None` — Retorna custo mensal apenas quando TODAS as chamadas têm estimativa disponível.
  - Entrada: nenhuma entrada explícita.
  - Saída: `Decimal | None`.
- `def summary(self, days: int, *, monthly_budget_usd: Decimal | None=None, budget_warning_ratio: Decimal=Decimal('0.80')) -> FinOpsSummary` — Sem descrição específica no código.
  - Entrada: `days: int`, `monthly_budget_usd: Decimal | None`, `budget_warning_ratio: Decimal`.
  - Saída: `FinOpsSummary`.

## `backend/repositories/audit_repository.py`

Persistência de auditoria técnica e revisão humana.

### `class AuditRepository`

Eventos imutáveis sem conteúdo documental bruto.

**Métodos:**

- `def __init__(self, database: SQLiteDatabase) -> None` — Sem descrição específica no código.
  - Entrada: `database: SQLiteDatabase`.
  - Saída: `None`.
- `def append(self, event: str, payload: dict[str, str | int | float | bool]) -> None` — Sem descrição específica no código.
  - Entrada: `event: str`, `payload: dict[str, str | int | float | bool]`.
  - Saída: `None`.
- `def add_parameter_change(self, change: ParameterChangeInput, *, actor: str, extracted_value: object=None, extracted_source: str | None=None) -> ParameterChangeRecord` — Sem descrição específica no código.
  - Entrada: `change: ParameterChangeInput`, `actor: str`, `extracted_value: object`, `extracted_source: str | None`.
  - Saída: `ParameterChangeRecord`.
- `def parameter_changes(self, *, process: str | None=None, draft: str | None=None) -> list[ParameterChangeRecord]` — Sem descrição específica no código.
  - Entrada: `process: str | None`, `draft: str | None`.
  - Saída: `list[ParameterChangeRecord]`.

## `backend/repositories/calculation_repository.py`

Persistência do agregado Cálculo → Versão → Execução → Artefato.

### `def _changed_fields(diff: CalculationDiff) -> list[str]`

Sem descrição específica no código.

**Entrada:** `diff: CalculationDiff`.

**Saída:** `list[str]`.

### `def _record_identity(origin: str, identifier: str, process: str | None) -> tuple[str, str, str]`

Sem descrição específica no código.

**Entrada:** `origin: str`, `identifier: str`, `process: str | None`.

**Saída:** `tuple[str, str, str]`.

### `def _total_difference(before: str | None, after: str | None) -> str | None`

Sem descrição específica no código.

**Entrada:** `before: str | None`, `after: str | None`.

**Saída:** `str | None`.

### `def _artifact_hash(content: bytes) -> str`

Sem descrição específica no código.

**Entrada:** `content: bytes`.

**Saída:** `str`.

### `class CalculationRepository`

Repositório transacional do ciclo de vida de cálculos versionados.

**Métodos:**

- `def __init__(self, database: SQLiteDatabase) -> None` — Sem descrição específica no código.
  - Entrada: `database: SQLiteDatabase`.
  - Saída: `None`.
- `def append_version(self, *, request: CalculationRequest, response: CalculationResponse, actor: str, pdf: bytes | None=None, pdf_factory: Callable[[str, int], bytes] | None=None, calculation_id: str | None=None, base_version: int | None=None, expected_current_version: int | None=None) -> tuple[CalculationVersionRef, CalculationExecutionRef]` — Cria versão somente para novo estado funcional e sempre registra execução.
  - Entrada: `request: CalculationRequest`, `response: CalculationResponse`, `actor: str`, `pdf: bytes | None`, `pdf_factory: Callable[[str, int], bytes] | None`, `calculation_id: str | None`, `base_version: int | None`, `expected_current_version: int | None`.
  - Saída: `tuple[CalculationVersionRef, CalculationExecutionRef]`.
- `def history(self, *, page: int=1, page_size: int=20, search: str | None=None, origin: str | None=None, state: CalculationState | None=None, index_name: str | None=None, created_by: str | None=None, updated_from: date | None=None, updated_to: date | None=None, sort: str='processo') -> CalculationHistoryPage` — Sem descrição específica no código.
  - Entrada: `page: int`, `page_size: int`, `search: str | None`, `origin: str | None`, `state: CalculationState | None`, `index_name: str | None`, `created_by: str | None`, `updated_from: date | None`, `updated_to: date | None`, `sort: str`.
  - Saída: `CalculationHistoryPage`.
- `def versions(self, calculation_id: str, *, page: int=1, page_size: int=50) -> CalculationVersionsPage | None` — Sem descrição específica no código.
  - Entrada: `calculation_id: str`, `page: int`, `page_size: int`.
  - Saída: `CalculationVersionsPage | None`.
- `def version(self, calculation_id: str, version: int) -> CalculationVersionDetail | None` — Sem descrição específica no código.
  - Entrada: `calculation_id: str`, `version: int`.
  - Saída: `CalculationVersionDetail | None`.
- `def compare(self, calculation_id: str, version_from: int, version_to: int) -> CalculationComparison | None` — Sem descrição específica no código.
  - Entrada: `calculation_id: str`, `version_from: int`, `version_to: int`.
  - Saída: `CalculationComparison | None`.
- `def change_state(self, calculation_id: str, state: CalculationState, *, actor: str) -> CalculationStateResult | None` — Sem descrição específica no código.
  - Entrada: `calculation_id: str`, `state: CalculationState`, `actor: str`.
  - Saída: `CalculationStateResult | None`.
- `def executions(self, calculation_id: str, version: int, *, page: int=1, page_size: int=20) -> CalculationExecutionsPage | None` — Sem descrição específica no código.
  - Entrada: `calculation_id: str`, `version: int`, `page: int`, `page_size: int`.
  - Saída: `CalculationExecutionsPage | None`.
- `def version_pdf(self, calculation_id: str, version: int) -> bytes | None` — Lê a memória de cálculo congelada quando a versão foi executada.
  - Entrada: `calculation_id: str`, `version: int`.
  - Saída: `bytes | None`.
- `def execution_pdf(self, calculation_id: str, execution_id: str) -> bytes | None` — Lê a memória de cálculo produzida por uma execução específica.
  - Entrada: `calculation_id: str`, `execution_id: str`.
  - Saída: `bytes | None`.

## `backend/repositories/document_repository.py`

Persistência exclusiva de documentos e processos.

### `def _process_sort_key(value: str) -> tuple[int, str, str]`

Sem descrição específica no código.

**Entrada:** `value: str`.

**Saída:** `tuple[int, str, str]`.

### `class DocumentRepository`

CRUD documental sem conhecer extração, cálculo ou auditoria.

**Métodos:**

- `def __init__(self, database: SQLiteDatabase) -> None` — Sem descrição específica no código.
  - Entrada: `database: SQLiteDatabase`.
  - Saída: `None`.
- `def add(self, document: DocumentMetadata) -> DocumentMetadata` — Sem descrição específica no código.
  - Entrada: `document: DocumentMetadata`.
  - Saída: `DocumentMetadata`.
- `def list_for_process(self, process: str) -> list[DocumentMetadata]` — Sem descrição específica no código.
  - Entrada: `process: str`.
  - Saída: `list[DocumentMetadata]`.
- `def get(self, identifier: str) -> DocumentMetadata | None` — Sem descrição específica no código.
  - Entrada: `identifier: str`.
  - Saída: `DocumentMetadata | None`.
- `def classify(self, identifier: str, classification: str) -> None` — Sem descrição específica no código.
  - Entrada: `identifier: str`, `classification: str`.
  - Saída: `None`.
- `def processes(self) -> list[ProcessSummary]` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `list[ProcessSummary]`.

## `backend/repositories/extraction_repository.py`

Persistência exclusiva do fluxo e fila de extração.

### `class ExtractionRepository`

Estado da extração e lease da fila durável.

**Métodos:**

- `def __init__(self, database: SQLiteDatabase, documents: DocumentRepository) -> None` — Sem descrição específica no código.
  - Entrada: `database: SQLiteDatabase`, `documents: DocumentRepository`.
  - Saída: `None`.
- `def start_job(self, status: ExtractionStatus, *, max_attempts: int=3) -> None` — Sem descrição específica no código.
  - Entrada: `status: ExtractionStatus`, `max_attempts: int`.
  - Saída: `None`.
- `def claim_job(self, lease_seconds: int) -> tuple[str, str, int, int] | None` — Sem descrição específica no código.
  - Entrada: `lease_seconds: int`.
  - Saída: `tuple[str, str, int, int] | None`.
- `def retry_job(self, job: str, delay_seconds: float) -> None` — Sem descrição específica no código.
  - Entrada: `job: str`, `delay_seconds: float`.
  - Saída: `None`.
- `def finish_job(self, job: str, *, success: bool) -> None` — Sem descrição específica no código.
  - Entrada: `job: str`, `success: bool`.
  - Saída: `None`.
- `def update_job(self, status: ExtractionStatus, result: ExtractionResult | None=None) -> None` — Sem descrição específica no código.
  - Entrada: `status: ExtractionStatus`, `result: ExtractionResult | None`.
  - Saída: `None`.
- `def status(self, process: str) -> ExtractionStatus | None` — Sem descrição específica no código.
  - Entrada: `process: str`.
  - Saída: `ExtractionStatus | None`.
- `def result(self, process: str) -> ExtractionResult | None` — Sem descrição específica no código.
  - Entrada: `process: str`.
  - Saída: `ExtractionResult | None`.
- `def recover_jobs(self) -> None` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `None`.

## `backend/repositories/index_repository.py`

Persistência mínima do estado do atualizador de índices.

### `class IndexRepository`

Sem descrição específica no código.

**Métodos:**

- `def __init__(self, database: SQLiteDatabase) -> None` — Sem descrição específica no código.
  - Entrada: `database: SQLiteDatabase`.
  - Saída: `None`.
- `def status(self) -> IndexStatus | None` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `IndexStatus | None`.
- `def save(self, status: IndexStatus) -> None` — Sem descrição específica no código.
  - Entrada: `status: IndexStatus`.
  - Saída: `None`.
- `def start_if_idle(self, status: IndexStatus) -> IndexStatus` — Sem descrição específica no código.
  - Entrada: `status: IndexStatus`.
  - Saída: `IndexStatus`.

## `backend/repositories/quality_repository.py`

Persistência da supervisão humana, curadoria e datasets versionados.

### `def stage_for_field(field: str) -> str`

Sem descrição específica no código.

**Entrada:** `field: str`.

**Saída:** `str`.

### `def _decode_scalar(value: str | None)`

Sem descrição específica no código.

**Entrada:** `value: str | None`.

**Saída:** tipo de saída não declarado.

### `class QualityRepository`

Repositório analítico separado do banco operacional de extração.

**Métodos:**

- `def __init__(self, database: SQLiteDatabase) -> None` — Sem descrição específica no código.
  - Entrada: `database: SQLiteDatabase`.
  - Saída: `None`.
- `def add_feedback(self, payload: dict) -> tuple[FeedbackEventRecord, bool]` — Insere evento imutável e deduplica reenvios pelo fingerprint.
  - Entrada: `payload: dict`.
  - Saída: `tuple[FeedbackEventRecord, bool]`.
- `def _feedback_record(row) -> FeedbackEventRecord` — Sem descrição específica no código.
  - Entrada: `row: tipo não declarado`.
  - Saída: `FeedbackEventRecord`.
- `def page(self, *, page: int, page_size: int, status: str | None=None, field: str | None=None) -> FeedbackPage` — Sem descrição específica no código.
  - Entrada: `page: int`, `page_size: int`, `status: str | None`, `field: str | None`.
  - Saída: `FeedbackPage`.
- `def curate(self, feedback_id: str, payload: FeedbackCurationInput, curator_hash: str) -> FeedbackEventRecord | None` — Sem descrição específica no código.
  - Entrada: `feedback_id: str`, `payload: FeedbackCurationInput`, `curator_hash: str`.
  - Saída: `FeedbackEventRecord | None`.
- `def summary(self) -> QualitySummary` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `QualitySummary`.
- `def create_dataset_snapshot(self, actor_hash: str) -> DatasetSnapshot` — Sem descrição específica no código.
  - Entrada: `actor_hash: str`.
  - Saída: `DatasetSnapshot`.
- `def _tokens(value: str) -> set[str]` — Sem descrição específica no código.
  - Entrada: `value: str`.
  - Saída: `set[str]`.
- `def retrieve_examples(self, stage: str, context: str, limit: int) -> list[LearningExample]` — Recuperação lexical local: zero chamadas extras de IA e somente exemplos aprovados.
  - Entrada: `stage: str`, `context: str`, `limit: int`.
  - Saída: `list[LearningExample]`.

## `backend/routers/__init__.py`

Rotas apenas recebem, validam e delegam aos serviços.

Este módulo não expõe classes ou funções de nível superior.

## `backend/routers/audit.py`

Endpoints de auditoria da revisão humana de parâmetros.

### `def record_parameter_change(payload: ParameterChangeInput, request: Request, service: Dependency)`

Registra uma alteração de parâmetro como evento imutável.

**Entrada:** `payload: ParameterChangeInput`, `request: Request`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def list_parameter_changes(service: Dependency, numero_processo: str | None=Query(default=None), rascunho_id: str | None=Query(default=None))`

Consulta por processo real ou por rascunho manual; exige exatamente um filtro.

**Entrada:** `service: Dependency`, `numero_processo: str | None`, `rascunho_id: str | None`.

**Saída:** tipo de saída não declarado.

## `backend/routers/batches.py`

Lotes reutilizam o mesmo serviço de cálculo e a confirmação humana.

### `async def import_batch(service: Dependency, file: UploadFile=File(...))`

Importar apenas prepara a prévia; não executa nem confirma o lote.

**Entrada:** `service: Dependency`, `file: UploadFile`.

**Saída:** tipo de saída não declarado.

### `def run(payload: BatchRequest, request: Request, service: Dependency)`

Falhas são explícitas por processo; sucessos não são descartados.

**Entrada:** `payload: BatchRequest`, `request: Request`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

## `backend/routers/calculations.py`

Cálculo, histórico versionado, execuções e exportações compartilham contratos validados.

### `def defaults(indice: str | None=None)`

Recomenda competência sem ultrapassar a cobertura do índice selecionado.

**Entrada:** `indice: str | None`.

**Saída:** tipo de saída não declarado.

### `def calculation_policy(origem_calculo: CalculationOrigin)`

Expõe padrões e metadados oficiais sem duplicá-los no frontend.

**Entrada:** `origem_calculo: CalculationOrigin`.

**Saída:** tipo de saída não declarado.

### `def prepare_fees(payload: FeePreparation)`

Mostra os valores nominais para revisão antes da chamada ao motor.

**Entrada:** `payload: FeePreparation`.

**Saída:** tipo de saída não declarado.

### `def history(service: Dependency, pagina: int=Query(default=1, ge=1), tamanho_pagina: int=Query(default=20, ge=1, le=100), busca: str | None=Query(default=None, max_length=120), origem: CalculationOrigin | None=None, estado: CalculationState | None=None, indice: str | None=Query(default=None, max_length=120), criado_por: str | None=Query(default=None, max_length=120), atualizado_de: date | None=None, atualizado_ate: date | None=None, ordenacao: Literal['processo', 'atualizado_desc', 'atualizado_asc', 'criado_desc', 'criado_asc']='processo')`

Lista cálculos paginados; as versões são carregadas somente após expansão.

**Entrada:** `service: Dependency`, `pagina: int`, `tamanho_pagina: int`, `busca: str | None`, `origem: CalculationOrigin | None`, `estado: CalculationState | None`, `indice: str | None`, `criado_por: str | None`, `atualizado_de: date | None`, `atualizado_ate: date | None`, `ordenacao: Literal['processo', 'atualizado_desc', 'atualizado_asc', 'criado_desc', 'criado_asc']`.

**Saída:** tipo de saída não declarado.

### `def versions(calculo_id: str, service: Dependency, pagina: int=Query(default=1, ge=1), tamanho_pagina: int=Query(default=50, ge=1, le=100))`

Lazy loading das versões de um cálculo já localizado no histórico.

**Entrada:** `calculo_id: str`, `service: Dependency`, `pagina: int`, `tamanho_pagina: int`.

**Saída:** tipo de saída não declarado.

### `def compare_versions(calculo_id: str, service: Dependency, versao_origem: int=Query(ge=1), versao_destino: int=Query(ge=1))`

Compara parâmetros, parcelas e impacto no total entre duas versões.

**Entrada:** `calculo_id: str`, `service: Dependency`, `versao_origem: int`, `versao_destino: int`.

**Saída:** tipo de saída não declarado.

### `def change_state(calculo_id: str, payload: CalculationStateChange, request: Request, service: Dependency)`

Arquiva, cancela ou reativa o cálculo sem excluir histórico.

**Entrada:** `calculo_id: str`, `payload: CalculationStateChange`, `request: Request`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def executions(calculo_id: str, versao: int, service: Dependency, pagina: int=Query(default=1, ge=1), tamanho_pagina: int=Query(default=20, ge=1, le=100))`

Pagina execuções técnicas sem carregar indefinidamente uma versão muito reexecutada.

**Entrada:** `calculo_id: str`, `versao: int`, `service: Dependency`, `pagina: int`, `tamanho_pagina: int`.

**Saída:** tipo de saída não declarado.

### `def version_detail(calculo_id: str, versao: int, service: Dependency)`

Reabre o snapshot exato de uma versão sem executar o motor novamente.

**Entrada:** `calculo_id: str`, `versao: int`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def version_pdf(calculo_id: str, versao: int, service: Dependency)`

Baixa a memória congelada quando aquela versão de negócio foi criada.

**Entrada:** `calculo_id: str`, `versao: int`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def execution_pdf(calculo_id: str, execucao_id: str, service: Dependency)`

Baixa a memória da execução atual, mesmo quando a versão foi reutilizada.

**Entrada:** `calculo_id: str`, `execucao_id: str`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def calculate(payload: CalculationRequest, request: Request, service: Dependency, calculo_id: str | None=Query(default=None), versao_base: int | None=Query(default=None, ge=1), versao_atual_esperada: int | None=Query(default=None, ge=1))`

Calcula e versiona com controle otimista, inclusive a partir de versões históricas.

**Entrada:** `payload: CalculationRequest`, `request: Request`, `service: Dependency`, `calculo_id: str | None`, `versao_base: int | None`, `versao_atual_esperada: int | None`.

**Saída:** tipo de saída não declarado.

### `def memory_pdf(payload: CalculationRequest, service: Dependency, indices_sha256: str | None=None)`

Exporta o request atual sem criar estado funcional ou execução persistida.

**Entrada:** `payload: CalculationRequest`, `service: Dependency`, `indices_sha256: str | None`.

**Saída:** tipo de saída não declarado.

## `backend/routers/documents.py`

Documentos chegam por multipart e são obtidos por identificador opaco.

### `async def upload(service: Dependency, files: list[UploadFile]=File(...))`

A extração é iniciada no servidor imediatamente após a persistência.

**Entrada:** `service: Dependency`, `files: list[UploadFile]`.

**Saída:** tipo de saída não declarado.

### `def processes(service: Dependency)`

Lista processos armazenados sem selecionar automaticamente nenhum na UI.

**Entrada:** `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def process_documents(numero_processo: str, service: Dependency)`

A seleção filtra no backend e evita misturar documentos de processos.

**Entrada:** `numero_processo: str`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def file(identificador_documento: str, service: Dependency)`

A autorização global da API também protege o conteúdo PDF.

**Entrada:** `identificador_documento: str`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `async def import_installments(service: Dependency, verba_tipo: DamageType, file: UploadFile=File(...))`

O limite também se aplica a planilhas antes de sua leitura pelo importador.

**Entrada:** `service: Dependency`, `verba_tipo: DamageType`, `file: UploadFile`.

**Saída:** tipo de saída não declarado.

## `backend/routers/extractions.py`

Consulta e repetição da extração não dependem de estado do navegador.

### `def configuration(service: Dependency)`

Expõe somente disponibilidade operacional da leitura local + geração corporativa.

**Entrada:** `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def start(payload: ExtractionRequest, service: Dependency)`

Retentativa manual é útil após configurar o deployment ou reiniciar o serviço.

**Entrada:** `payload: ExtractionRequest`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def status(numero_processo: str, service: Dependency)`

Ausência de trabalho é 404; falha do provedor é estado explícito.

**Entrada:** `numero_processo: str`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def result(numero_processo: str, service: Dependency)`

Somente extração consolidada é devolvida para revisão humana.

**Entrada:** `numero_processo: str`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

## `backend/routers/indices.py`

Catálogo e atualização de índices passam exclusivamente pela API.

### `def options(service: Dependency)`

Devolve somente chaves registradas no motor.

**Entrada:** `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def status(service: Dependency)`

Informa estado real, sem afirmar atualização não verificada.

**Entrada:** `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def update(service: Dependency)`

Atualização segue assíncrona e pode ser acompanhada por polling.

**Entrada:** `service: Dependency`.

**Saída:** tipo de saída não declarado.

## `backend/routers/quality.py`

Endpoints de qualidade supervisionada e FinOps da extração.

### `def capture_review(payload: ReviewSnapshotInput, request: Request, service: Dependency)`

Registra IA × humano sem sobrescrever a predição original.

**Entrada:** `payload: ReviewSnapshotInput`, `request: Request`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def quality_summary(service: Dependency)`

Sem descrição específica no código.

**Entrada:** `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def feedback_page(service: Dependency, pagina: int=Query(default=1, ge=1), tamanho: int=Query(default=25, ge=1, le=100), status: str | None=Query(default='pending'), campo: str | None=Query(default=None))`

Sem descrição específica no código.

**Entrada:** `service: Dependency`, `pagina: int`, `tamanho: int`, `status: str | None`, `campo: str | None`.

**Saída:** tipo de saída não declarado.

### `def curate_feedback(feedback_id: str, payload: FeedbackCurationInput, request: Request, service: Dependency)`

Sem descrição específica no código.

**Entrada:** `feedback_id: str`, `payload: FeedbackCurationInput`, `request: Request`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def snapshot_dataset(request: Request, service: Dependency)`

Congela IDs/hashes dos exemplos aprovados; não duplica conteúdo documental.

**Entrada:** `request: Request`, `service: Dependency`.

**Saída:** tipo de saída não declarado.

### `def finops(service: Dependency, dias: int=Query(default=30, ge=1, le=365))`

Sem descrição específica no código.

**Entrada:** `service: Dependency`, `dias: int`.

**Saída:** tipo de saída não declarado.

## `backend/services/__init__.py`

Serviços de aplicação independentes dos componentes Angular.

Este módulo não expõe classes ou funções de nível superior.

## `backend/services/ai_usage.py`

Telemetria FinOps: separa métricas reais, estimativas locais e custo configurado.

### `class UsageMeter`

Mede somente o que é observável e rotula explicitamente qualquer estimativa.

**Métodos:**

- `def __init__(self, settings: Settings | None=None) -> None` — Sem descrição específica no código.
  - Entrada: `settings: Settings | None`.
  - Saída: `None`.
- `def estimate_tokens(characters: int) -> int` — Heurística local para planejamento; não representa faturamento do gateway.
  - Entrada: `characters: int`.
  - Saída: `int`.
- `def _estimated_cost(settings: Settings | None, *, input_tokens: int, cached_input_tokens: int, output_tokens: int) -> Decimal | None` — Sem descrição específica no código.
  - Entrada: `settings: Settings | None`, `input_tokens: int`, `cached_input_tokens: int`, `output_tokens: int`.
  - Saída: `Decimal | None`.
- `def from_call(*, model: str, stage: str, duration_ms: float, input_chars: int=0, output_chars: int=0, input_tokens_actual: int | None=None, cached_input_tokens_actual: int | None=None, output_tokens_actual: int | None=None, cache_hit: bool=False, request_sha256: str | None=None, settings: Settings | None=None) -> AiUsage` — Sem descrição específica no código.
  - Entrada: `model: str`, `stage: str`, `duration_ms: float`, `input_chars: int`, `output_chars: int`, `input_tokens_actual: int | None`, `cached_input_tokens_actual: int | None`, `output_tokens_actual: int | None`, `cache_hit: bool`, `request_sha256: str | None`, `settings: Settings | None`.
  - Saída: `AiUsage`.

### `class RequestTimer`

Cronômetro monotônico para medir somente latência técnica.

**Métodos:**

- `def __init__(self) -> None` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `None`.
- `def elapsed_ms(self) -> float` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `float`.

## `backend/services/batches.py`

Orquestração de lotes reaproveita o cálculo unitário, sem duplicar o motor.

### `class BatchService`

Execução sequencial limita memória e mantém erros separados por processo.

**Métodos:**

- `def __init__(self, calculation: CalculationService)` — Recebe dependências explicitamente para manter configuração e testes isolados.
  - Entrada: `calculation: CalculationService`.
  - Saída: tipo de saída não declarado.
- `def execute(self, payload: BatchRequest, *, actor: str='system') -> BatchResponse` — Preserva os sucessos e informa explicitamente cada falha de domínio.
  - Entrada: `payload: BatchRequest`, `actor: str`.
  - Saída: `BatchResponse`.

## `backend/services/bradesco_bridge.py`

Integração mínima com ``gpt_bradesco.py`` para geração de texto.

### `class TextGenerationResult`

Texto e contadores reais quando o gateway os expõe explicitamente.

**Atributos declarados:** `text: str`, `input_tokens: int | None`, `cached_input_tokens: int | None`, `output_tokens: int | None`.


### `class BradescoBridgeError(ServiceError)`

Erro sanitizado da integração corporativa, sem conteúdo documental.

**Métodos:**

- `def __init__(self, code: str, message: str, status_code: int=502)` — Sem descrição específica no código.
  - Entrada: `code: str`, `message: str`, `status_code: int`.
  - Saída: tipo de saída não declarado.

### `class BradescoBridgeClient`

Facade restrita ao ``text_generator`` do módulo corporativo.

**Métodos:**

- `def __init__(self, settings: Settings)` — Sem descrição específica no código.
  - Entrada: `settings: Settings`.
  - Saída: tipo de saída não declarado.
- `def configured(self) -> bool` — A configuração local exige apenas um deployment de geração de texto.
  - Entrada: nenhuma entrada explícita.
  - Saída: `bool`.
- `def _load(self) -> Any` — Importa o módulo corporativo somente na primeira chamada de prompt.
  - Entrada: nenhuma entrada explícita.
  - Saída: `Any`.
- `def _safe_request_id(value: Any) -> str | None` — Aceita somente identificadores técnicos curtos em mensagens de erro.
  - Entrada: `value: Any`.
  - Saída: `str | None`.
- `def _safe_status_code(exc: Exception) -> int | None` — Recupera apenas o código HTTP sem propagar corpo de resposta ou documento.
  - Entrada: `exc: Exception`.
  - Saída: `int | None`.
- `def _classify_error(self, exc: Exception, operation: str) -> BradescoBridgeError` — Traduz falhas externas sem ecoar prompt, documento ou credencial.
  - Entrada: `exc: Exception`, `operation: str`.
  - Saída: `BradescoBridgeError`.
- `def _binds(function: Any, args: Sequence[Any]) -> bool` — Confere a assinatura antes da chamada para evitar tentativa por exceção.
  - Entrada: `function: Any`, `args: Sequence[Any]`.
  - Saída: `bool`.
- `def _invoke_callable(self, operation: str, function: Any, variants: Sequence[Sequence[Any]]) -> Any` — Executa a primeira assinatura conhecida compatível com a função.
  - Entrada: `operation: str`, `function: Any`, `variants: Sequence[Sequence[Any]]`.
  - Saída: `Any`.
- `def generate_text_with_metadata(self, payload: str, *, max_tokens: int) -> TextGenerationResult` — Executa geração e preserva contadores reais apenas quando expostos pelo gateway.
  - Entrada: `payload: str`, `max_tokens: int`.
  - Saída: `TextGenerationResult`.
- `def generate_text(self, payload: str, *, max_tokens: int) -> str` — Retorna somente o texto para consumidores que não precisam das métricas.
  - Entrada: `payload: str`, `max_tokens: int`.
  - Saída: `str`.

## `backend/services/calculation.py`

Orquestra cálculo, versionamento, exportação e auditoria fora das rotas HTTP.

### `class CalculationService`

Uma execução coerente usa a mesma versão de índices até o fim.

**Métodos:**

- `def __init__(self, repository: CalculationRepository, audit_repository: AuditRepository, facade: EngineFacade)` — Recebe dependências explicitamente para manter configuração e testes isolados.
  - Entrada: `repository: CalculationRepository`, `audit_repository: AuditRepository`, `facade: EngineFacade`.
  - Saída: tipo de saída não declarado.
- `def execute(self, payload: CalculationRequest, pdf: bool=False, expected_indices_hash: str | None=None, *, calculation_id: str | None=None, base_version: int | None=None, expected_current_version: int | None=None, actor: str='system', persist_version: bool=True) -> VersionedCalculationResponse | bytes` — Executa o motor e cadastra automaticamente a versão do cálculo.
  - Entrada: `payload: CalculationRequest`, `pdf: bool`, `expected_indices_hash: str | None`, `calculation_id: str | None`, `base_version: int | None`, `expected_current_version: int | None`, `actor: str`, `persist_version: bool`.
  - Saída: `VersionedCalculationResponse | bytes`.

## `backend/services/chronology.py`

Consolidação determinística da evolução documental de um processo.

### `def document_sequence(name: str) -> int`

Obtém a sequência cronológica do padrão ``processo_sequencia*.pdf``.

**Entrada:** `name: str`.

**Saída:** `int`.

### `def ordered_documents(documents: list[DocumentMetadata]) -> list[DocumentMetadata]`

Ordena anexos do mais antigo para o mais recente de forma determinística.

**Entrada:** `documents: list[DocumentMetadata]`.

**Saída:** `list[DocumentMetadata]`.

### `class ChronologyReducer`

Resolve valores efetivos sem apagar as evidências históricas que os originaram.

**Métodos:**

- `def reduce(self, evidences: Iterable[FieldEvidence]) -> tuple[dict[str, Scalar], list[ChronologyDecision], list[str]]` — Consolida apenas ``parametros.*`` e devolve valor, decisão e alertas.
  - Entrada: `evidences: Iterable[FieldEvidence]`.
  - Saída: `tuple[dict[str, Scalar], list[ChronologyDecision], list[str]]`.
- `def _resolve_commands(self, path: str, commands: list[FieldEvidence]) -> tuple[Scalar, FieldEvidence, str] | None` — Aplica os efeitos dos comandos em ordem cronológica.
  - Entrada: `path: str`, `commands: list[FieldEvidence]`.
  - Saída: `tuple[Scalar, FieldEvidence, str] | None`.
- `def _value_key(value: Scalar) -> str` — Compara escalares sem depender de hash de tipos heterogêneos.
  - Entrada: `value: Scalar`.
  - Saída: `str`.
- `def _sort_key(item: FieldEvidence) -> tuple[int, int, str]` — Ordenação estável para escolher a evidência mais recente entre concordantes.
  - Entrada: `item: FieldEvidence`.
  - Saída: `tuple[int, int, str]`.
- `def _decision(path: str, evidence: FieldEvidence, reason: str) -> ChronologyDecision` — Materializa a decisão de consolidação para auditoria e UI.
  - Entrada: `path: str`, `evidence: FieldEvidence`, `reason: str`.
  - Saída: `ChronologyDecision`.

## `backend/services/documents.py`

Upload validado, persistente e organizado exclusivamente no backend.

### `class DocumentService`

Identifica o processo pelo nome exigido; conteúdo não altera a associação.

**Métodos:**

- `def __init__(self, settings: Settings, repository: DocumentRepository, audit_repository: AuditRepository)` — Recebe dependências explicitamente para manter configuração e testes isolados.
  - Entrada: `settings: Settings`, `repository: DocumentRepository`, `audit_repository: AuditRepository`.
  - Saída: tipo de saída não declarado.
- `async def receive(self, files: list[UploadFile]) -> list[DocumentMetadata]` — Valida o lote completo antes de persistir; leitura limitada evita alocações ilimitadas.
  - Entrada: `files: list[UploadFile]`.
  - Saída: `list[DocumentMetadata]`.
- `def path(self, identifier: str) -> tuple[Path, DocumentMetadata]` — Somente documento registrado pode ser obtido pelo identificador opaco.
  - Entrada: `identifier: str`.
  - Saída: `tuple[Path, DocumentMetadata]`.

## `backend/services/engine.py`

Única fachada do cálculo: adapta tipos sem reproduzir fórmulas.

### `def file_hashes(directory: Path, pattern: str) -> dict[str, str]`

Hash de conteúdo identifica código e séries sem incluir dados nos logs.

**Entrada:** `directory: Path`, `pattern: str`.

**Saída:** `dict[str, str]`.

### `def digest(values: dict[str, str]) -> str`

Ordenação torna o identificador independente da ordem do filesystem.

**Entrada:** `values: dict[str, str]`.

**Saída:** `str`.

### `def scalar(value: object) -> Scalar`

Decimais viram texto para evitar arredondamento binário na serialização.

**Entrada:** `value: object`.

**Saída:** `Scalar`.

### `def dataframe_table(frame: pd.DataFrame) -> DataTable`

O formato tabular admite colunas adicionais produzidas pelo próprio motor.

**Entrada:** `frame: pd.DataFrame`.

**Saída:** `DataTable`.

### `class EngineFacade`

Isola o motor de cálculo dos contratos HTTP e das estruturas da interface.

**Métodos:**

- `def __init__(self, settings: Settings)` — Recebe dependências explicitamente para manter configuração e testes isolados.
  - Entrada: `settings: Settings`.
  - Saída: tipo de saída não declarado.
- `def calculate(self, payload: CalculationRequest) -> ResultadoCalculo` — Converte a requisição validada para o formato esperado pelo motor e executa o cálculo.
  - Entrada: `payload: CalculationRequest`.
  - Saída: `ResultadoCalculo`.
- `def pdf(self, result: ResultadoCalculo, *, identificador_calculo: str | None=None, versao_calculo: int | None=None) -> bytes` — Gera a única memória PDF com identidade de negócio e versão quando conhecidas.
  - Entrada: `result: ResultadoCalculo`, `identificador_calculo: str | None`, `versao_calculo: int | None`.
  - Saída: `bytes`.
- `def index_hash(self) -> str` — A versão das séries é capturada enquanto o cálculo detém o lock.
  - Entrada: nenhuma entrada explícita.
  - Saída: `str`.

## `backend/services/engine_guidance.py`

Transforma erros estruturados do motor em orientação operacional segura.

### `def _format_competence(value: object) -> str`

Formata ``AAAA-MM`` sem depender do locale do sistema operacional.

**Entrada:** `value: object`.

**Saída:** `str`.

### `def _labels(keys: tuple[str, ...]) -> str`

Formata os campos do erro usando a mesma nomenclatura exibida na interface.

**Entrada:** `keys: tuple[str, ...]`.

**Saída:** `str`.

### `def engine_error_guidance(error: Exception) -> str`

Retorna orientação para correção sem analisar nem devolver o texto da exceção.

**Entrada:** `error: Exception`.

**Saída:** `str`.

## `backend/services/evidence_validator.py`

Validação de evidências contra o texto local e consolidação cronológica.

### `class EvidenceValidator`

Mantém somente evidências rastreáveis e calcula métricas de aceitação.

**Métodos:**

- `def __init__(self, reducer: ChronologyReducer | None=None)` — Sem descrição específica no código.
  - Entrada: `reducer: ChronologyReducer | None`.
  - Saída: tipo de saída não declarado.
- `def consolidate(self, result: ExtractionResult, documents: list[DocumentMetadata], pdf_documents: list[PdfTextDocument] | None=None) -> tuple[ExtractionResult, int, int]` — Sem descrição específica no código.
  - Entrada: `result: ExtractionResult`, `documents: list[DocumentMetadata]`, `pdf_documents: list[PdfTextDocument] | None`.
  - Saída: `tuple[ExtractionResult, int, int]`.

## `backend/services/extraction.py`

Orquestração de extração documental com leitura local, seleção de páginas e fila durável.

### `class ExtractionProviderError(ServiceError)`

Erro público estável; nunca inclui corpo da resposta, prompt ou credencial.

**Métodos:**

- `def __init__(self, code: str, message: str, status_code: int=502, retryable: bool=False)` — Sem descrição específica no código.
  - Entrada: `code: str`, `message: str`, `status_code: int`, `retryable: bool`.
  - Saída: tipo de saída não declarado.

### `class ExtractionProvider`

Fachada testável para PyMuPDF, roteamento de páginas e text_generator.

**Métodos:**

- `def __init__(self, settings: Settings, bridge: BradescoBridgeClient | None=None, ai_repository: AiOperationsRepository | None=None, quality_repository: QualityRepository | None=None)` — Sem descrição específica no código.
  - Entrada: `settings: Settings`, `bridge: BradescoBridgeClient | None`, `ai_repository: AiOperationsRepository | None`, `quality_repository: QualityRepository | None`.
  - Saída: tipo de saída não declarado.
- `def configured(self) -> bool` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `bool`.
- `def read_documents(self, files: list[tuple[str, bytes, int]]) -> list[PdfTextDocument]` — Sem descrição específica no código.
  - Entrada: `files: list[tuple[str, bytes, int]]`.
  - Saída: `list[PdfTextDocument]`.
- `def extract_with_metrics(self, prompt: str, documents: list[PdfTextDocument], *, stage: str, max_output_tokens: int, job_id: str | None=None) -> tuple[ProviderResult, PromptExecutionMetrics]` — Executa a tarefa e devolve métricas sem quebrar provedores de teste com interface mínima.
  - Entrada: `prompt: str`, `documents: list[PdfTextDocument]`, `stage: str`, `max_output_tokens: int`, `job_id: str | None`.
  - Saída: `tuple[ProviderResult, PromptExecutionMetrics]`.
- `def extract(self, prompt: str, documents: list[PdfTextDocument], *, stage: str, max_output_tokens: int, job_id: str | None=None) -> ProviderResult` — Compatibilidade para testes e integrações que não consomem métricas detalhadas.
  - Entrada: `prompt: str`, `documents: list[PdfTextDocument]`, `stage: str`, `max_output_tokens: int`, `job_id: str | None`.
  - Saída: `ProviderResult`.

### `class ExtractionService`

Orquestra fila durável, prompts especializados, validação e persistência.

**Métodos:**

- `def __init__(self, settings: Settings, extraction_repository: ExtractionRepository, document_repository: DocumentRepository, audit_repository: AuditRepository, documents: DocumentService, provider: ExtractionProvider)` — Sem descrição específica no código.
  - Entrada: `settings: Settings`, `extraction_repository: ExtractionRepository`, `document_repository: DocumentRepository`, `audit_repository: AuditRepository`, `documents: DocumentService`, `provider: ExtractionProvider`.
  - Saída: tipo de saída não declarado.
- `def start(self, process: str, new_upload: bool=False) -> ExtractionStatus` — Cria uma revisão e a persiste na fila; trabalhos ativos são compartilhados.
  - Entrada: `process: str`, `new_upload: bool`.
  - Saída: `ExtractionStatus`.
- `def _handle_claimed_job(self, claimed: ClaimedExtractionJob) -> None` — Sem descrição específica no código.
  - Entrada: `claimed: ClaimedExtractionJob`.
  - Saída: `None`.
- `def _persist_failure(self, status: ExtractionStatus, code: str, message: str) -> None` — Sem descrição específica no código.
  - Entrada: `status: ExtractionStatus`, `code: str`, `message: str`.
  - Saída: `None`.
- `def _run_once(self, status: ExtractionStatus, documents: list[DocumentMetadata], attempt: int) -> None` — Sem descrição específica no código.
  - Entrada: `status: ExtractionStatus`, `documents: list[DocumentMetadata]`, `attempt: int`.
  - Saída: `None`.
- `def run(self, status: ExtractionStatus, documents: list[DocumentMetadata]) -> None` — Compatibilidade de teste: executa uma tentativa síncrona fora da fila.
  - Entrada: `status: ExtractionStatus`, `documents: list[DocumentMetadata]`.
  - Saída: `None`.
- `def _sum_optional(values: list[int | None]) -> int | None` — Sem descrição específica no código.
  - Entrada: `values: list[int | None]`.
  - Saída: `int | None`.
- `def _summarize_usage(cls, usages: list[AiUsage]) -> AiUsageSummary` — Sem descrição específica no código.
  - Entrada: `usages: list[AiUsage]`.
  - Saída: `AiUsageSummary`.
- `def consolidate(self, result: ExtractionResult, documents: list[DocumentMetadata], pdf_documents: list[PdfTextDocument] | None=None) -> ExtractionResult` — Compatibilidade pública para testes de consolidação.
  - Entrada: `result: ExtractionResult`, `documents: list[DocumentMetadata]`, `pdf_documents: list[PdfTextDocument] | None`.
  - Saída: `ExtractionResult`.
- `def close(self) -> None` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `None`.

## `backend/services/extraction_jobs.py`

Fila durável de extração baseada no repositório de negócio.

### `class ClaimedExtractionJob`

Sem descrição específica no código.

**Atributos declarados:** `job_id: str`, `process: str`, `attempt: int`, `max_attempts: int`.


### `class DurableExtractionWorkers`

Workers locais que consomem jobs persistidos e recuperáveis após reinício.

**Métodos:**

- `def __init__(self, repository: ExtractionRepository, worker_count: int, handler: Callable[[ClaimedExtractionJob], None], *, lease_seconds: int=900, poll_seconds: float=0.25)` — Sem descrição específica no código.
  - Entrada: `repository: ExtractionRepository`, `worker_count: int`, `handler: Callable[[ClaimedExtractionJob], None]`, `lease_seconds: int`, `poll_seconds: float`.
  - Saída: tipo de saída não declarado.
- `def _loop(self) -> None` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `None`.
- `def wake(self) -> None` — Sinal sem estado; reduz latência após enqueue.
  - Entrada: nenhuma entrada explícita.
  - Saída: `None`.
- `def close(self) -> None` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `None`.

## `backend/services/extraction_types.py`

Tipos internos da extração; separados da orquestração para evitar acoplamento.

### `class ExtractionFragment(Contract)`

Fragmento especializado já validado pelo contrato interno.

**Atributos declarados:** `campos: list[FieldEvidence]`, `parcelas: list[Installment]`, `alertas: list[str]`.


### `class ProviderResult(Contract)`

Fragmento estruturado e telemetria observável das chamadas corporativas.

**Atributos declarados:** `fragmento: ExtractionFragment`, `usos: list[AiUsage]`.


## `backend/services/extraction_wire.py`

Contrato externo tolerante a omissões seguras; limites permanecem no contrato interno.

### `class WireEvidence(FieldEvidence)`

Evidência recebida do gerador com defaults somente para metadados de classificação.

**Atributos declarados:** `pagina: int`, `natureza: EvidenceNature`, `efeito: EvidenceEffect`.


### `class WireInstallment(Contract)`

Parcela no transporte; multiplicador só é informado com suporte documental específico.

**Atributos declarados:** `data: str`, `valor_singelo: str`, `descricao: str`, `numero_contrato: str | None`, `verba_tipo: DamageType`, `multiplicador: Literal[1, 2] | None`.

**Métodos:**

- `def include_contract_in_description(self) -> 'WireInstallment'` — Acrescenta o contrato à descrição sem criar novo campo no motor.
  - Entrada: nenhuma entrada explícita.
  - Saída: `'WireInstallment'`.

### `class WireExtractionFragment(Contract)`

Estrutura mínima retornada por cada prompt especializado.

**Atributos declarados:** `campos: list[WireEvidence]`, `parcelas: list[WireInstallment]`, `alertas: list[str]`.


## `backend/services/imports.py`

Importadores rejeitam linhas inválidas em vez de alterar o lote silenciosamente.

### `def read_table(content: bytes, filename: str) -> list[dict[str, str]]`

Somente formatos documentados; CSV exige UTF-8 e preserva identificadores.

**Entrada:** `content: bytes`, `filename: str`.

**Saída:** `list[dict[str, str]]`.

### `def normalize_date(value: object) -> str`

Datas ISO têm prioridade; o formato brasileiro é aceito explicitamente.

**Entrada:** `value: object`.

**Saída:** `str`.

### `def normalize_money(value: object) -> str`

A vírgula identifica formato brasileiro; decimal canônico usa ponto.

**Entrada:** `value: object`.

**Saída:** `str`.

### `def installment_from_row(row: dict[str, str], damage_type: str) -> Installment`

Normalização de arquivo fica centralizada e usa o mesmo contrato da API.

**Entrada:** `row: dict[str, str]`, `damage_type: str`.

**Saída:** `Installment`.

### `class ImportService`

A prévia nunca calcula nem confirma revisão humana.

**Métodos:**

- `def installments(self, content: bytes, filename: str, damage_type: str) -> list[Installment]` — Importa todas as linhas ou informa erro, sem omitir valores inválidos.
  - Entrada: `content: bytes`, `filename: str`, `damage_type: str`.
  - Saída: `list[Installment]`.
- `def batch(self, content: bytes, filename: str) -> BatchImport` — JSON carrega o contrato completo; planilhas agrupam parcelas por processo.
  - Entrada: `content: bytes`, `filename: str`.
  - Saída: `BatchImport`.

## `backend/services/indices.py`

Gestão das séries delega ao atualizador existente, com exclusão mútua.

### `def display_name(key: str, raw_name: str) -> str`

Normaliza nomes da lista para o padrão esperado na interface.

**Entrada:** `key: str`, `raw_name: str`.

**Saída:** `str`.

### `def format_competence(comp: str | None) -> str`

Formata ``AAAA-MM`` como ``mmm/AAAA`` sem depender de locale.

**Entrada:** `comp: str | None`.

**Saída:** `str`.

### `def display_label(raw_name: str, first: str | None, last: str | None) -> str`

Monta rótulo apenas com o intervalo observado na planilha instalada.

**Entrada:** `raw_name: str`, `first: str | None`, `last: str | None`.

**Saída:** `str`.

### `def _public_update_failure(result) -> str`

Converte a falha técnica do atualizador em orientação segura para a interface.

**Entrada:** `result: tipo não declarado`.

**Saída:** `str`.

### `class IndexService`

Uma atualização por vez, estado verificável e backup fornecido pelo motor.

**Métodos:**

- `def __init__(self, settings: Settings, repository: IndexRepository, audit_repository: AuditRepository, facade: EngineFacade) -> None` — Recebe apenas as dependências realmente usadas pelo serviço.
  - Entrada: `settings: Settings`, `repository: IndexRepository`, `audit_repository: AuditRepository`, `facade: EngineFacade`.
  - Saída: `None`.
- `def options(self) -> list[IndexOption]` — Lista índices selecionáveis, inclusive séries históricas extintas conhecidas.
  - Entrada: nenhuma entrada explícita.
  - Saída: `list[IndexOption]`.
- `def status(self) -> IndexStatus` — Checksum relata o arquivo real; não implica atualidade da série.
  - Entrada: nenhuma entrada explícita.
  - Saída: `IndexStatus`.
- `def save(self, state: str, message: str) -> IndexStatus` — Persiste o estado de atualização para consultas e recuperação.
  - Entrada: `state: str`, `message: str`.
  - Saída: `IndexStatus`.
- `def start(self) -> IndexStatus` — A trava do processo evita que dois cliques enfileirem atualizações iguais.
  - Entrada: nenhuma entrada explícita.
  - Saída: `IndexStatus`.
- `def run(self) -> None` — Atualiza as séries sob a mesma trava usada pelo cálculo.
  - Entrada: nenhuma entrada explícita.
  - Saída: `None`.
- `def close(self) -> None` — Encerra recursos próprios sem interferir em outras instâncias.
  - Entrada: nenhuma entrada explícita.
  - Saída: `None`.

## `backend/services/operational_policy.py`

Aplica critérios operacionais rastreáveis antes da revisão humana do cálculo.

### `def current_competence(today: date | None=None, index_key: str | None=None) -> CalculationDefaults`

Retorna a competência recomendada, respeitando a cobertura do índice.

**Entrada:** `today: date | None`, `index_key: str | None`.

**Saída:** `CalculationDefaults`.

### `def fee_installments(rows: list[Installment], percentage: Decimal) -> list[Installment]`

Compõe parcelas nominais de honorários; não calcula juros ou correção.

**Entrada:** `rows: list[Installment]`, `percentage: Decimal`.

**Saída:** `list[Installment]`.

### `def validate_prepared_request(payload: CalculationRequest) -> None`

Não permite duplicar encargos nem calcular sobre uma composição desatualizada.

**Entrada:** `payload: CalculationRequest`.

**Saída:** `None`.

### `class OperationalPolicy`

Aplica os padrões após conferir evidências, separando-os dos fatos extraídos.

**Métodos:**

- `def __init__(self, configuration: OperationalSettings | None=None)` — Configuração central permite alterar seleção sem editar o motor.
  - Entrada: `configuration: OperationalSettings | None`.
  - Saída: tipo de saída não declarado.
- `def apply(self, extracted: ExtractionResult, today: date | None=None) -> ExtractionResult` — Aplica padrões somente quando a evidência do caso concreto não informa o campo.
  - Entrada: `extracted: ExtractionResult`, `today: date | None`.
  - Saída: `ExtractionResult`.

## `backend/services/pdf_text_extractor.py`

Leitura local de PDFs com score explícito de qualidade da camada textual.

### `class PdfPageQuality`

Métricas técnicas da camada textual; nunca contém o texto da página.

**Atributos declarados:** `caracteres: int`, `caracteres_imprimiveis: int`, `proporcao_imprimivel: float`, `proporcao_alfanumerica: float`, `caracteres_substituicao: int`, `score: float`, `status: str`.


### `class PdfTextPage`

Texto de uma página e sua qualidade observada localmente.

**Atributos declarados:** `numero: int`, `texto: str`, `qualidade: PdfPageQuality | None`.


### `class PdfTextDocument`

Texto paginado do PDF e alertas de qualidade da camada textual.

**Atributos declarados:** `nome: str`, `paginas: tuple[PdfTextPage, ...]`, `alertas: tuple[str, ...]`.

**Métodos:**

- `def paginas_utilizaveis(self) -> tuple[PdfTextPage, ...]` — Retorna somente páginas com texto suficientemente confiável para IA.
  - Entrada: nenhuma entrada explícita.
  - Saída: `tuple[PdfTextPage, ...]`.
- `def caracteres_utilizaveis(self) -> int` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `int`.
- `def requer_fonte_alternativa(self) -> bool` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `bool`.
- `def texto_prompt(self) -> str` — Converte páginas utilizáveis em string rastreável pelo prompt.
  - Entrada: nenhuma entrada explícita.
  - Saída: `str`.

### `class PdfTextExtractor`

Extrai texto localmente e bloqueia chamadas de IA sem conteúdo minimamente útil.

**Métodos:**

- `def __init__(self, settings: Settings)` — Sem descrição específica no código.
  - Entrada: `settings: Settings`.
  - Saída: tipo de saída não declarado.
- `def _quality(text: str) -> PdfPageQuality` — Sem descrição específica no código.
  - Entrada: `text: str`.
  - Saída: `PdfPageQuality`.
- `def read(self, files: list[tuple[str, bytes, int]]) -> list[PdfTextDocument]` — Lê PDFs com PyMuPDF e devolve texto paginado em memória.
  - Entrada: `files: list[tuple[str, bytes, int]]`.
  - Saída: `list[PdfTextDocument]`.
- `def assert_usable(documents: list[PdfTextDocument]) -> None` — Evita gastar chamadas corporativas quando nenhum PDF tem texto utilizável.
  - Entrada: `documents: list[PdfTextDocument]`.
  - Saída: `None`.

## `backend/services/prompt_context.py`

Monta contexto enxuto e específico por tarefa para reduzir tokens repetidos.

### `class PromptContext`

Prefixo comum estável e contexto processual reutilizados no mesmo processo.

**Atributos declarados:** `base: str`, `process_context: str`, `parameter_schema: dict`.

**Métodos:**

- `def for_task(self, task_path: Path) -> str` — Inclui somente o subcontrato necessário à tarefa para reduzir payload textual.
  - Entrada: `task_path: Path`.
  - Saída: `str`.

### `class PromptContextBuilder`

Pré-calcula dados estáveis e evita repetir o schema integral em todas as chamadas.

**Métodos:**

- `def __init__(self, base_path: Path | None=None)` — Sem descrição específica no código.
  - Entrada: `base_path: Path | None`.
  - Saída: tipo de saída não declarado.
- `def build(self, process: str, documents: list[DocumentMetadata]) -> PromptContext` — Materializa apenas cronologia e catálogo; o subcontrato entra por tarefa.
  - Entrada: `process: str`, `documents: list[DocumentMetadata]`.
  - Saída: `PromptContext`.

## `backend/services/prompt_executor.py`

Execução de prompts corporativos com roteamento, cache, aprendizado e FinOps.

### `class PromptExecutionError(RuntimeError)`

Erro sanitizado do provedor corporativo.

**Métodos:**

- `def __init__(self, code: str, message: str, status_code: int=502, retryable: bool=False)` — Sem descrição específica no código.
  - Entrada: `code: str`, `message: str`, `status_code: int`, `retryable: bool`.
  - Saída: tipo de saída não declarado.

### `class PromptExecutionMetrics`

Métricas observáveis de uma tarefa, sem conteúdo documental.

**Atributos declarados:** `paginas_contexto: int`, `caracteres_contexto: int`, `chunks: int`, `reparos_estruturais: int`, `estrategia_selecao: str`.


### `class PromptExecutor`

Seleciona páginas, limita payload, reaproveita respostas idênticas e mede custo.

**Métodos:**

- `def __init__(self, settings: Settings, bridge: BradescoBridgeClient, router: PromptPageRouter | None=None, ai_repository: AiOperationsRepository | None=None, quality_repository: QualityRepository | None=None)` — Sem descrição específica no código.
  - Entrada: `settings: Settings`, `bridge: BradescoBridgeClient`, `router: PromptPageRouter | None`, `ai_repository: AiOperationsRepository | None`, `quality_repository: QualityRepository | None`.
  - Saída: tipo de saída não declarado.
- `def _translate_error(exc: Exception) -> PromptExecutionError` — Sem descrição específica no código.
  - Entrada: `exc: Exception`.
  - Saída: `PromptExecutionError`.
- `def _split_large_block(header: str, text: str, max_chars: int) -> list[str]` — Sem descrição específica no código.
  - Entrada: `header: str`, `text: str`, `max_chars: int`.
  - Saída: `list[str]`.
- `def _pack_text(self, documents: tuple[PdfTextDocument, ...]) -> list[str]` — Sem descrição específica no código.
  - Entrada: `documents: tuple[PdfTextDocument, ...]`.
  - Saída: `list[str]`.
- `def _shift_evidence(field: FieldEvidence, parcel_offset: int) -> FieldEvidence` — Sem descrição específica no código.
  - Entrada: `field: FieldEvidence`, `parcel_offset: int`.
  - Saída: `FieldEvidence`.
- `def _deduplicate_fields(fields: list[FieldEvidence]) -> list[FieldEvidence]` — Sem descrição específica no código.
  - Entrada: `fields: list[FieldEvidence]`.
  - Saída: `list[FieldEvidence]`.
- `def _request_hash(self, request: str, max_output_tokens: int) -> str` — Sem descrição específica no código.
  - Entrada: `request: str`, `max_output_tokens: int`.
  - Saída: `str`.
- `def _examples_block(self, stage: str, context: str) -> str` — Sem descrição específica no código.
  - Entrada: `stage: str`, `context: str`.
  - Saída: `str`.
- `def _ensure_budget(self, job_id: str | None, proposed_input_chars: int) -> None` — Sem descrição específica no código.
  - Entrada: `job_id: str | None`, `proposed_input_chars: int`.
  - Saída: `None`.
- `def _record_usage(self, usage: AiUsage, *, job_id: str | None, pages: int | None, structural_repair: bool) -> None` — Sem descrição específica no código.
  - Entrada: `usage: AiUsage`, `job_id: str | None`, `pages: int | None`, `structural_repair: bool`.
  - Saída: `None`.
- `def _generate(self, request: str, *, stage: str, max_output_tokens: int, job_id: str | None, pages: int | None, allow_cache: bool, structural_repair: bool) -> tuple[str, AiUsage, str | None]` — Sem descrição específica no código.
  - Entrada: `request: str`, `stage: str`, `max_output_tokens: int`, `job_id: str | None`, `pages: int | None`, `allow_cache: bool`, `structural_repair: bool`.
  - Saída: `tuple[str, AiUsage, str | None]`.
- `def _parse_or_repair(self, response: str, *, stage: str, max_output_tokens: int, job_id: str | None, pages: int | None) -> tuple[WireExtractionFragment, AiUsage | None, bool]` — Normaliza deterministicamente; usa IA apenas se o contrato continuar inválido.
  - Entrada: `response: str`, `stage: str`, `max_output_tokens: int`, `job_id: str | None`, `pages: int | None`.
  - Saída: `tuple[WireExtractionFragment, AiUsage | None, bool]`.
- `def execute(self, prompt: str, documents: list[PdfTextDocument], *, stage: str, max_output_tokens: int, job_id: str | None=None) -> tuple[ProviderResult, PromptExecutionMetrics]` — Sem descrição específica no código.
  - Entrada: `prompt: str`, `documents: list[PdfTextDocument]`, `stage: str`, `max_output_tokens: int`, `job_id: str | None`.
  - Saída: `tuple[ProviderResult, PromptExecutionMetrics]`.

## `backend/services/prompt_router.py`

Seleção determinística de páginas para reduzir payload sem usar outro modelo.

### `class PromptSelection`

Contexto selecionado e métricas observáveis da decisão determinística.

**Atributos declarados:** `documentos: tuple[PdfTextDocument, ...]`, `paginas: int`, `caracteres: int`, `estrategia: str`.


### `class PromptPageRouter`

Roteia somente páginas candidatas a cada tarefa especializada.

**Atributos declarados:** `KEYWORDS: dict[str, tuple[str, ...]]`.

**Métodos:**

- `def __init__(self, max_pages_per_task: int=16, fallback_pages_per_document: int=4)` — Sem descrição específica no código.
  - Entrada: `max_pages_per_task: int`, `fallback_pages_per_document: int`.
  - Saída: tipo de saída não declarado.
- `def _score(text: str, keywords: tuple[str, ...]) -> int` — Sem descrição específica no código.
  - Entrada: `text: str`, `keywords: tuple[str, ...]`.
  - Saída: `int`.
- `def _representative(pages: tuple[PdfTextPage, ...], limit: int) -> list[PdfTextPage]` — Sem descrição específica no código.
  - Entrada: `pages: tuple[PdfTextPage, ...]`, `limit: int`.
  - Saída: `list[PdfTextPage]`.
- `def select(self, stage: str, documents: list[PdfTextDocument]) -> PromptSelection` — Seleciona páginas por palavras-chave e aplica fallback representativo.
  - Entrada: `stage: str`, `documents: list[PdfTextDocument]`.
  - Saída: `PromptSelection`.

## `backend/services/quality_learning.py`

Transforma revisão humana em supervisão estruturada, curada e versionável.

### `class QualityLearningService`

Mantém prediction e revisão separadas; nunca sobrescreve a saída original da IA.

**Métodos:**

- `def __init__(self, settings: Settings, repository: QualityRepository, extraction_repository: ExtractionRepository, document_repository: DocumentRepository) -> None` — Sem descrição específica no código.
  - Entrada: `settings: Settings`, `repository: QualityRepository`, `extraction_repository: ExtractionRepository`, `document_repository: DocumentRepository`.
  - Saída: `None`.
- `def _reviewer_hash(actor: str) -> str` — Sem descrição específica no código.
  - Entrada: `actor: str`.
  - Saída: `str`.
- `def _json_value(value: object) -> str | None` — Sem descrição específica no código.
  - Entrada: `value: object`.
  - Saída: `str | None`.
- `def _equivalent(left: object, right: object) -> bool` — Sem descrição específica no código.
  - Entrada: `left: object`, `right: object`.
  - Saída: `bool`.
- `def _action(model_value: object, human_value: object) -> tuple[str, str]` — Sem descrição específica no código.
  - Entrada: `model_value: object`, `human_value: object`.
  - Saída: `tuple[str, str]`.
- `def _evidence(result, path: str)` — Sem descrição específica no código.
  - Entrada: `result: tipo não declarado`, `path: str`.
  - Saída: tipo de saída não declarado.
- `def capture_review(self, snapshot: ReviewSnapshotInput, actor: str) -> ReviewCaptureResult` — Compara o snapshot humano com a predição persistida no backend.
  - Entrada: `snapshot: ReviewSnapshotInput`, `actor: str`.
  - Saída: `ReviewCaptureResult`.
- `def summary(self) -> QualitySummary` — Sem descrição específica no código.
  - Entrada: nenhuma entrada explícita.
  - Saída: `QualitySummary`.
- `def feedback_page(self, page: int, page_size: int, status: str | None, field: str | None) -> FeedbackPage` — Sem descrição específica no código.
  - Entrada: `page: int`, `page_size: int`, `status: str | None`, `field: str | None`.
  - Saída: `FeedbackPage`.
- `def curate(self, feedback_id: str, payload: FeedbackCurationInput, actor: str) -> FeedbackEventRecord` — Sem descrição específica no código.
  - Entrada: `feedback_id: str`, `payload: FeedbackCurationInput`, `actor: str`.
  - Saída: `FeedbackEventRecord`.
- `def snapshot_dataset(self, actor: str) -> DatasetSnapshot` — Sem descrição específica no código.
  - Entrada: `actor: str`.
  - Saída: `DatasetSnapshot`.

## `backend/services/revision_audit.py`

Persistência e enriquecimento da trilha de revisão humana dos parâmetros.

### `class RevisionAuditService`

Registra eventos imutáveis sem depender do estado visual do Angular.

**Métodos:**

- `def __init__(self, repository: AuditRepository, extraction_repository: ExtractionRepository)` — Recebe o repositório que persiste os eventos imutáveis de revisão.
  - Entrada: `repository: AuditRepository`, `extraction_repository: ExtractionRepository`.
  - Saída: tipo de saída não declarado.
- `def record(self, change: ParameterChangeInput, actor: str) -> ParameterChangeRecord` — Enriquece o evento com o valor/origem extraídos que o servidor conhece.
  - Entrada: `change: ParameterChangeInput`, `actor: str`.
  - Saída: `ParameterChangeRecord`.
- `def list_for_process(self, process: str) -> list[ParameterChangeRecord]` — Retorna toda a trilha persistida do processo.
  - Entrada: `process: str`.
  - Saída: `list[ParameterChangeRecord]`.
- `def list_for_draft(self, draft: str) -> list[ParameterChangeRecord]` — Retorna a trilha do rascunho manual atual.
  - Entrada: `draft: str`.
  - Saída: `list[ParameterChangeRecord]`.

## `backend/services/structured_output.py`

Normalização determinística da saída do text_generator antes de qualquer reparo por IA.

### `class StructuredOutputError(ValueError)`

Falha estrutural sem ecoar conteúdo documental.


### `class StructuredOutputParser`

Aceita variações estruturais seguras e valida o contrato canônico.

**Atributos declarados:** `WRAPPERS: tipo inferido em execução`, `TOP_ALIASES: tipo inferido em execução`, `FIELD_ALIASES: tipo inferido em execução`, `INSTALLMENT_ALIASES: tipo inferido em execução`.

**Métodos:**

- `def _decode(text: str) -> dict[str, Any]` — Sem descrição específica no código.
  - Entrada: `text: str`.
  - Saída: `dict[str, Any]`.
- `def _unwrap(cls, decoded: dict[str, Any]) -> dict[str, Any]` — Sem descrição específica no código.
  - Entrada: `decoded: dict[str, Any]`.
  - Saída: `dict[str, Any]`.
- `def _rename(source: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]` — Sem descrição específica no código.
  - Entrada: `source: dict[str, Any]`, `aliases: dict[str, str]`.
  - Saída: `dict[str, Any]`.
- `def normalize(cls, decoded: dict[str, Any]) -> dict[str, Any]` — Sem descrição específica no código.
  - Entrada: `decoded: dict[str, Any]`.
  - Saída: `dict[str, Any]`.
- `def parse(self, text: str) -> WireExtractionFragment` — Sem descrição específica no código.
  - Entrada: `text: str`.
  - Saída: `WireExtractionFragment`.
- `def validation_summary(exc: ValidationError) -> str` — Sem descrição específica no código.
  - Entrada: `exc: ValidationError`.
  - Saída: `str`.

## `backend/version.py`

Versões oficiais da aplicação e do contrato HTTP.

Este módulo não expõe classes ou funções de nível superior.

## `scripts/check-python-environment.py`

Valida o runtime Python antes de iniciar a API.

### `def locked_versions() -> dict[str, str]`

Lê somente pins exatos do lock para evitar inferências de versão.

**Entrada:** nenhuma entrada explícita.

**Saída:** `dict[str, str]`.

### `def installed_version(package: str) -> str | None`

Retorna a versão instalada sem importar o pacote alvo.

**Entrada:** `package: str`.

**Saída:** `str | None`.

### `def main() -> int`

Falha cedo quando o runtime diverge das dependências críticas homologadas.

**Entrada:** nenhuma entrada explícita.

**Saída:** `int`.

## `scripts/evaluate_extraction.py`

Compara predições de extração com um conjunto de referência revisado.

### `def _case_map(payload: dict[str, Any], field_name: str) -> dict[str, dict[str, Any]]`

Indexa casos por identificador e valida a presença do objeto de campos.

**Entrada:** `payload: dict[str, Any]`, `field_name: str`.

**Saída:** `dict[str, dict[str, Any]]`.

### `def evaluate(gold: dict[str, Any], predictions: dict[str, Any]) -> dict[str, Any]`

Calcula acerto exato por campo e lista divergências sem ocultá-las em média.

**Entrada:** `gold: dict[str, Any]`, `predictions: dict[str, Any]`.

**Saída:** `dict[str, Any]`.

### `def main() -> int`

Lê arquivos informados em CLI e imprime relatório JSON reproduzível.

**Entrada:** nenhuma entrada explícita.

**Saída:** `int`.

## `scripts/generate_contracts.py`

Gera interfaces TypeScript do OpenAPI; a API é a fonte única dos contratos.

### `def type_name(schema: dict) -> str`

Converte somente estruturas publicadas pelo Pydantic/OpenAPI.

**Entrada:** `schema: dict`.

**Saída:** `str`.

### `def main() -> None`

Salva contrato e interfaces com ordenação estável para comparação em testes.

**Entrada:** nenhuma entrada explícita.

**Saída:** `None`.

## `scripts/generate_engine_manifest.py`

Gera o manifesto SHA-256 dos arquivos Python do motor determinístico.

### `def engine_manifest() -> dict[str, str]`

Retorna hashes ordenados dos fontes Python que compõem o pacote do motor.

**Entrada:** nenhuma entrada explícita.

**Saída:** `dict[str, str]`.

### `def main() -> int`

Persiste o manifesto em JSON estável para validação de integridade.

**Entrada:** nenhuma entrada explícita.

**Saída:** `int`.

## `scripts/generate_module_guide.py`

Gera um guia simples com a responsabilidade de cada módulo do projeto.

### `def _clean(text: str | None) -> str`

Transforma um comentário longo em uma descrição curta de uma linha.

**Entrada:** `text: str | None`.

**Saída:** `str`.

### `def _python_description(path: Path) -> str`

Lê apenas a árvore sintática; o módulo não é importado nem executado.

**Entrada:** `path: Path`.

**Saída:** `str`.

### `def _typescript_description(path: Path) -> str`

Extrai o primeiro comentário de documentação do arquivo TypeScript.

**Entrada:** `path: Path`.

**Saída:** `str`.

### `def _role(relative: str) -> tuple[str, str, str]`

Retorna papel, entrada típica e saída típica de acordo com a pasta.

**Entrada:** `relative: str`.

**Saída:** `tuple[str, str, str]`.

### `def _rows(paths: list[Path], description_reader) -> list[str]`

Monta linhas de tabela para uma lista ordenada de arquivos.

**Entrada:** `paths: list[Path]`, `description_reader: tipo não declarado`.

**Saída:** `list[str]`.

### `def generate() -> str`

Produz o Markdown completo de forma determinística.

**Entrada:** nenhuma entrada explícita.

**Saída:** `str`.

### `def main() -> int`

Grava o guia na pasta de documentação e informa o caminho criado.

**Entrada:** nenhuma entrada explícita.

**Saída:** `int`.

## `scripts/generate_parameter_catalog.py`

Gera o catálogo TypeScript a partir da política central.

### `def ts(value: object) -> str`

Serializa JSON válido também como literal TypeScript.

**Entrada:** `value: object`.

**Saída:** `str`.

### `def main() -> None`

Valida chaves básicas e grava o artefato consumido pela interface.

**Entrada:** nenhuma entrada explícita.

**Saída:** `None`.

## `scripts/generate_parameter_docs.py`

Gera a documentação do catálogo de parâmetros a partir da política central.

### `def _display(value: object) -> str`

Converte valores da política para texto curto e estável em Markdown.

**Entrada:** `value: object`.

**Saída:** `str`.

### `def main() -> None`

Grava padrões, obrigatoriedade, opções e grupos sem duplicação manual.

**Entrada:** nenhuma entrada explícita.

**Saída:** `None`.

## `scripts/run_backend.py`

Inicializa o backend usando uma única configuração de execução.

### `class RuntimeSettings`

Valores necessários apenas para iniciar os servidores locais.

**Atributos declarados:** `backend_host: str`, `backend_port: int`, `backend_workers: int`, `backend_access_log: bool`, `frontend_host: str`, `frontend_port: int`, `reload_directories: tuple[Path, ...]`, `reload_include_patterns: tuple[str, ...]`, `reload_exclude_patterns: tuple[str, ...]`.


### `def _read_json(path: Path) -> dict[str, Any]`

Lê o arquivo de execução e garante que a raiz seja um objeto JSON.

**Entrada:** `path: Path`.

**Saída:** `dict[str, Any]`.

### `def _required_mapping(data: dict[str, Any], key: str) -> dict[str, Any]`

Obtém uma seção obrigatória do JSON sem aceitar tipos inesperados.

**Entrada:** `data: dict[str, Any]`, `key: str`.

**Saída:** `dict[str, Any]`.

### `def _environment_bool(name: str, default: bool) -> bool`

Converte uma variável de ambiente em booleano de forma explícita.

**Entrada:** `name: str`, `default: bool`.

**Saída:** `bool`.

### `def _environment_int(name: str, default: int, *, minimum: int, maximum: int) -> int`

Lê um inteiro do ambiente e valida o intervalo permitido.

**Entrada:** `name: str`, `default: int`, `minimum: int`, `maximum: int`.

**Saída:** `int`.

### `def _project_paths(values: Any, field_name: str) -> tuple[Path, ...]`

Transforma caminhos relativos do JSON em caminhos absolutos do projeto.

**Entrada:** `values: Any`, `field_name: str`.

**Saída:** `tuple[Path, ...]`.

### `def _string_patterns(values: Any, field_name: str) -> tuple[str, ...]`

Valida uma lista de padrões relativos usada pelo observador de arquivos.

**Entrada:** `values: Any`, `field_name: str`.

**Saída:** `tuple[str, ...]`.

### `def load_runtime_settings(path: Path | None=None) -> RuntimeSettings`

Carrega e valida toda a configuração usada pelos scripts de execução.

**Entrada:** `path: Path | None`.

**Saída:** `RuntimeSettings`.

### `def validate_python_environment() -> None`

Executa a checagem de dependências antes de importar toda a aplicação.

**Entrada:** nenhuma entrada explícita.

**Saída:** `None`.

### `def run_backend(*, reload_enabled: bool) -> None`

Inicia o Uvicorn com escopo de observação controlado.

**Entrada:** `reload_enabled: bool`.

**Saída:** `None`.

### `def parse_arguments() -> argparse.Namespace`

Converte os argumentos do terminal em opções tipadas para o iniciador.

**Entrada:** nenhuma entrada explícita.

**Saída:** `argparse.Namespace`.

### `def main() -> int`

Ponto único de entrada do backend usado por todos os sistemas operacionais.

**Entrada:** nenhuma entrada explícita.

**Saída:** `int`.

## `scripts/test_text_generator_connection.py`

Diagnóstico seguro da conexão com o gerador corporativo.

### `def main() -> int`

Valida configuração local e realiza uma chamada mínima ao text_generator.

**Entrada:** nenhuma entrada explícita.

**Saída:** `int`.

## `scripts/validate_architecture.py`

Valida fronteiras arquiteturais, dependências proibidas e versões fixadas do frontend.

### `def architecture_errors(root: Path) -> list[str]`

Imports são analisados por AST, evitando falsos positivos em palavras como interest.

**Entrada:** `root: Path`.

**Saída:** `list[str]`.

## `src/judicial_calc/__init__.py`

Interface pública do motor de cálculo judicial.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/cli.py`

Interface de linha de comando do projeto.

### `def _decimal_para_texto(obj: Any) -> Any`

Serializa ``Decimal`` para JSON.

**Entrada:** `obj: Any`.

**Saída:** `Any`.

### `def main() -> None`

Executa o cálculo a partir de um arquivo JSON.

**Entrada:** nenhuma entrada explícita.

**Saída:** `None`.

## `src/judicial_calc/core/__init__.py`

Tipos, validações e utilidades básicas usadas por todas as regras do motor.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/core/constants.py`

Constantes compartilhadas por regras de datas e consulta de séries oficiais.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/core/dates.py`

Funções utilitárias para datas e competências mensais.

### `def _int_flex(valor: str | int, nome: str) -> int`

Converte inteiros que podem chegar como 2026.0/"2026.0".

**Entrada:** `valor: str | int`, `nome: str`.

**Saída:** `int`.

### `def parse_mes_ano(mes: str | int, ano: str | int) -> str`

Converte mês e ano em competência ``AAAA-MM``.

**Entrada:** `mes: str | int`, `ano: str | int`.

**Saída:** `str`.

### `def parse_data(valor: str | date | datetime) -> date`

Converte uma entrada de data para ``datetime.date``.

**Entrada:** `valor: str | date | datetime`.

**Saída:** `date`.

### `def competencia_data(d: date) -> str`

Extrai a competência mensal de uma data.

**Entrada:** `d: date`.

**Saída:** `str`.

### `def data_primeiro_dia(comp: str) -> date`

Retorna o primeiro dia de uma competência.

**Entrada:** `comp: str`.

**Saída:** `date`.

### `def ultimo_dia_mes(comp: str) -> date`

Retorna o último dia de uma competência.

**Entrada:** `comp: str`.

**Saída:** `date`.

### `def somar_meses(comp: str, meses: int) -> str`

Soma ou subtrai meses de uma competência.

**Entrada:** `comp: str`, `meses: int`.

**Saída:** `str`.

### `def iter_competencias(inicio: str, fim: str) -> Iterable[str]`

Itera competências mensais em intervalo fechado.

**Entrada:** `inicio: str`, `fim: str`.

**Saída:** `Iterable[str]`.

### `def competencias_entre(inicio: str, fim: str) -> int`

Conta a diferença em meses entre duas competências.

**Entrada:** `inicio: str`, `fim: str`.

**Saída:** `int`.

## `src/judicial_calc/core/errors.py`

Exceções estruturadas usadas na fronteira do motor de cálculo.

### `class CalculationValidationError(ValueError)`

Representa uma combinação inválida de parâmetros do motor.

**Métodos:**

- `def __init__(self, code: str, fields: Iterable[str]=(), message: str='Parâmetros de cálculo incompatíveis.', metadata: Mapping[str, Any] | None=None) -> None` — Inicializa código estável, campos relacionados e metadados seguros.
  - Entrada: `code: str`, `fields: Iterable[str]`, `message: str`, `metadata: Mapping[str, Any] | None`.
  - Saída: `None`.

## `src/judicial_calc/core/models.py`

Modelos Pydantic versionados para entrada/auditoria do cálculo judicial.

### `class StrictBaseModel(BaseModel)`

Base comum que aceita campos extras para compatibilidade evolutiva.

**Atributos declarados:** `model_config: tipo inferido em execução`.


### `class EvidenceSource(StrictBaseModel)`

Fonte/evidência usada para justificar um campo extraído.

**Atributos declarados:** `field_path: str`, `extracted_value: str`, `source_file: str`, `source_page: int | None`, `confidence: float`, `evidence: str`, `status: StatusEvidencia`, `process_scope: TipoEscopo`, `source_section: str | None`, `document_type: str | None`.

**Métodos:**

- `def is_usable_for_calculation(self) -> bool` — Indica se a evidência pode alimentar o cálculo final.
  - Entrada: nenhuma entrada explícita.
  - Saída: `bool`.

### `class ParcelaInput(StrictBaseModel)`

Parcela individual calculável.

**Atributos declarados:** `item: int`, `descricao: str`, `data: date`, `valor_singelo: Decimal`, `verba_tipo: TipoVerba`, `source_file: str | None`, `source_page: int | None`, `confidence: float | None`.


### `class VerbaJudicial(StrictBaseModel)`

Verba consolidada por natureza jurídica.

**Atributos declarados:** `tipo: TipoVerba`, `descricao: str`, `valor_base: Decimal`, `data_base: date | None`, `source_file: str | None`, `source_page: int | None`, `evidence: str`, `confidence: float`.


### `class PrescricaoParams(StrictBaseModel)`

Agrupa os parâmetros estruturados de prescrição usados no contrato interno.

**Atributos declarados:** `flag: int`, `anos: int | None`, `data_referencia_tipo: Literal['data_ajuizamento', 'data_decisao', 'data_ultima_parcela'] | None`, `data_referencia: date | None`.


### `class CompensacaoParams(StrictBaseModel)`

Agrupa os parâmetros estruturados de compensação usados no contrato interno.

**Atributos declarados:** `flag: int`, `tipo_calculo: Literal['percentual', 'fixo']`, `valor: Decimal`.


### `class DuploIndiceParams(StrictBaseModel)`

Agrupa os parâmetros das duas faixas de correção do modo de duplo índice.

**Atributos declarados:** `flag: int`, `primeiro_indice: str`, `primeiro_data_inicio: date | None`, `primeiro_data_fim: date | None`, `primeiro_valor_parcela: Decimal | None`, `segundo_indice: str`, `segundo_data_inicio: date | None`, `segundo_data_fim: date | None`, `segundo_valor_parcela: Decimal | None`.


### `class CalculoJudicialInput(StrictBaseModel)`

Payload versionado completo para cálculo judicial rastreável.

**Atributos declarados:** `schema_version: str`, `processo_id: str | None`, `parcelas: list[ParcelaInput]`, `params: dict[str, Any]`, `verbas: list[VerbaJudicial]`, `evidence_map: dict[str, list[EvidenceSource]]`, `raw_extractions: list[dict[str, Any]]`, `validation_issues: list[dict[str, Any]]`, `human_review_checklist: list[dict[str, Any]]`.

**Métodos:**

- `def params_must_be_dict(cls, value: dict[str, Any]) -> dict[str, Any]` — Garante que o bloco de parâmetros seja recebido como dicionário antes das demais validações.
  - Entrada: `value: dict[str, Any]`.
  - Saída: `dict[str, Any]`.
- `def calculation_params(self) -> dict[str, Any]` — Retorna uma cópia isolada dos parâmetros destinados ao motor.
  - Entrada: nenhuma entrada explícita.
  - Saída: `dict[str, Any]`.

## `src/judicial_calc/core/numbers.py`

Funções utilitárias para conversão e arredondamento numérico.

### `def D(valor: Any) -> Decimal`

Converte valores comuns para ``Decimal`` de forma segura.

**Entrada:** `valor: Any`.

**Saída:** `Decimal`.

### `def moeda(valor: Any) -> Decimal`

Arredonda um valor para centavos com regra comercial.

**Entrada:** `valor: Any`.

**Saída:** `Decimal`.

### `def percentual_taxa_legal(valor_decimal: Decimal) -> Decimal`

Arredonda percentuais equivalentes da Taxa Legal.

**Entrada:** `valor_decimal: Decimal`.

**Saída:** `Decimal`.

### `def arredondar_abnt(valor: Decimal, casas: int) -> Decimal`

Arredonda usando o critério ABNT/meio par.

**Entrada:** `valor: Decimal`, `casas: int`.

**Saída:** `Decimal`.

## `src/judicial_calc/core/tables.py`

Normalização de tabelas de índices.

### `def normalizar_tabela_mensal(tabela: pd.DataFrame | list[dict[str, Any]], coluna_valor: str='indice') -> pd.DataFrame`

Normaliza tabela mensal para o formato usado nos cálculos.

**Entrada:** `tabela: pd.DataFrame | list[dict[str, Any]]`, `coluna_valor: str`.

**Saída:** `pd.DataFrame`.

## `src/judicial_calc/core/types.py`

Tipos públicos retornados pela biblioteca.

### `class ResultadoCalculo`

Resultado completo do cálculo judicial.

**Atributos declarados:** `memoria: pd.DataFrame`, `resumo: pd.DataFrame`, `parametros: dict[str, Any]`.


## `src/judicial_calc/data/__init__.py`

Pacote de recursos contendo as planilhas de índices distribuídas com o motor.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/data_sources/__init__.py`

Acesso controlado às fontes de índices e às planilhas locais do motor.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/data_sources/drcalc/__init__.py`

Interface pública do atualizador de índices obtidos do DrCalc.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/data_sources/drcalc/client.py`

Cliente HTTP e parser de formulários/tabelas históricas do DrCalc.

### `class DrCalcClient`

Cliente simples para descobrir e baixar séries do DrCalc.

**Métodos:**

- `def __init__(self, session: requests.Session | None=None, timeout: int=30) -> None` — Inicializa a instância com as dependências e configurações necessárias ao componente.
  - Entrada: `session: requests.Session | None`, `timeout: int`.
  - Saída: `None`.
- `def get(self, url: str) -> str` — Executa uma requisição HTTP com timeout e tratamento de falhas do cliente.
  - Entrada: `url: str`.
  - Saída: `str`.
- `def _request_form(self, *, method: str, url: str, payload: dict[str, str]) -> tuple[str, str]` — Submete o formulário histórico do DrCalc preservando o método informado pela página.
  - Entrada: `method: str`, `url: str`, `payload: dict[str, str]`.
  - Saída: `tuple[str, str]`.
- `def discover_series_urls(self) -> list[tuple[str, str, str]]` — Retorna tuplas ``(categoria, nome, url)`` encontradas nas categorias alvo.
  - Entrada: nenhuma entrada explícita.
  - Saída: `list[tuple[str, str, str]]`.
- `def fetch_historical_series(self) -> list[DrCalcSeries]` — Baixa as séries pela consulta histórica oficial do DrCalc.
  - Entrada: nenhuma entrada explícita.
  - Saída: `list[DrCalcSeries]`.
- `def _select_signature(select: Any) -> str` — Produz uma assinatura textual estável para classificar campos do formulário.
  - Entrada: `select: Any`.
  - Saída: `str`.
- `def _numeric_option_values(select: Any) -> list[int]` — Retorna valores inteiros das opções quando o campo é predominantemente numérico.
  - Entrada: `select: Any`.
  - Saída: `list[int]`.
- `def _select_role(self, select: Any) -> str` — Classifica ``select`` como categoria, mês, ano, série ou outro.
  - Entrada: `select: Any`.
  - Saída: `str`.
- `def _field_boundary(signature: str) -> str | None` — Infere se o campo representa o início ou o fim do intervalo pesquisado.
  - Entrada: `signature: str`.
  - Saída: `str | None`.
- `def _option_value_for_number(select: Any, number: int, *, nearest: str) -> str | None` — Escolhe a opção numérica desejada respeitando os valores efetivamente publicados.
  - Entrada: `select: Any`, `number: int`, `nearest: str`.
  - Saída: `str | None`.
- `def _selected_or_first_value(select: Any) -> str | None` — Lê a opção selecionada do formulário ou usa a primeira opção com valor.
  - Entrada: `select: Any`.
  - Saída: `str | None`.
- `def _find_history_form(self, soup: BeautifulSoup) -> tuple[Any, Any, list[Any], list[Any]] | None` — Localiza o formulário de consulta e seus campos de série, mês e ano.
  - Entrada: `soup: BeautifulSoup`.
  - Saída: `tuple[Any, Any, list[Any], list[Any]] | None`.
- `def _split_interval_selects(self, selects: list[Any]) -> tuple[Any, Any]` — Separa os dois campos equivalentes em início/fim usando nome e ordem do DOM.
  - Entrada: `selects: list[Any]`.
  - Saída: `tuple[Any, Any]`.
- `def _base_form_payload(self, form: Any) -> dict[str, str]` — Copia campos ocultos e defaults necessários para reproduzir a submissão do formulário.
  - Entrada: `form: Any`.
  - Saída: `dict[str, str]`.
- `def _fetch_category_form_series(self, *, category_name: str, category_id: int, category_url: str, html: str) -> list[DrCalcSeries]` — Submete o formulário histórico para todos os indexadores de uma categoria.
  - Entrada: `category_name: str`, `category_id: int`, `category_url: str`, `html: str`.
  - Saída: `list[DrCalcSeries]`.
- `def _infer_metric_from_columns(columns: Iterable[str]) -> str` — Infere a natureza da métrica pela semântica dos cabeçalhos.
  - Entrada: `columns: Iterable[str]`.
  - Saída: `str`.
- `def _discover_category_ids(self) -> list[tuple[str, int]]` — Descobre os IDs das três categorias relevantes sem depender de posição fixa.
  - Entrada: nenhuma entrada explícita.
  - Saída: `list[tuple[str, int]]`.
- `def _is_series_select(select: Any) -> bool` — Identifica o ``select`` de indexadores e ignora mês, ano e categoria.
  - Entrada: `select: Any`.
  - Saída: `bool`.
- `def _extract_links_from_category(self, html: str, base_url: str) -> list[tuple[str, str]]` — Extrai somente links plausíveis de séries da categoria informada.
  - Entrada: `html: str`, `base_url: str`.
  - Saída: `list[tuple[str, str]]`.
- `def fetch_series(self, category: str, name: str, url: str) -> DrCalcSeries | None` — Baixa e interpreta uma série do DrCalc em registros estruturados.
  - Entrada: `category: str`, `name: str`, `url: str`.
  - Saída: `DrCalcSeries | None`.
- `def _series_title(self, soup: BeautifulSoup, fallback: str) -> str` — Obtém um título estável para identificar a série baixada.
  - Entrada: `soup: BeautifulSoup`, `fallback: str`.
  - Saída: `str`.
- `def _extract_records_from_html(self, html: str, soup: BeautifulSoup, preferred_metric: str | None=None) -> tuple[list[DrCalcRecord], list[str]]` — Extrai registros temporais do HTML da série.
  - Entrada: `html: str`, `soup: BeautifulSoup`, `preferred_metric: str | None`.
  - Saída: `tuple[list[DrCalcRecord], list[str]]`.
- `def _records_from_table(self, df: pd.DataFrame, preferred_metric: str | None=None) -> list[DrCalcRecord]` — Converte uma tabela HTML em registros de período e valor.
  - Entrada: `df: pd.DataFrame`, `preferred_metric: str | None`.
  - Saída: `list[DrCalcRecord]`.
- `def _records_from_matrix_table(self, df: pd.DataFrame) -> list[DrCalcRecord]` — Interpreta tabelas históricas no formato ano x meses ou mês x anos.
  - Entrada: `df: pd.DataFrame`.
  - Saída: `list[DrCalcRecord]`.

## `src/judicial_calc/data_sources/drcalc/lifecycle.py`

Estado local, backup, restauração, cache e exclusão mútua do atualizador.

### `def _today_str() -> str`

Retorna a data corrente em formato ISO para gravação do estado do atualizador.

**Entrada:** nenhuma entrada explícita.

**Saída:** `str`.

### `def _data_dir(path: str | Path | None=None) -> Path`

Resolve a pasta que contém as planilhas locais de índices.

**Entrada:** `path: str | Path | None`.

**Saída:** `Path`.

### `def _state_path(data_dir: Path) -> Path`

Resolve o arquivo JSON usado para persistir o estado do atualizador.

**Entrada:** `data_dir: Path`.

**Saída:** `Path`.

### `def _lock_path(data_dir: Path) -> Path`

Resolve o arquivo de lock que impede duas atualizações simultâneas.

**Entrada:** `data_dir: Path`.

**Saída:** `Path`.

### `def _load_state(data_dir: Path) -> dict[str, Any]`

Lê o estado persistido do atualizador e retorna uma estrutura vazia quando não existe estado válido.

**Entrada:** `data_dir: Path`.

**Saída:** `dict[str, Any]`.

### `def _write_state(data_dir: Path, result: DrCalcUpdateResult) -> None`

Persiste o estado da atualização preservando o último sucesso.

**Entrada:** `data_dir: Path`, `result: DrCalcUpdateResult`.

**Saída:** `None`.

### `def _already_updated_today(data_dir: Path) -> bool`

Verifica se já existe atualização bem-sucedida registrada para a data corrente.

**Entrada:** `data_dir: Path`.

**Saída:** `bool`.

### `def _backup_planilhas(data_dir: Path) -> Path`

Cria cópia de segurança das planilhas antes de substituí-las.

**Entrada:** `data_dir: Path`.

**Saída:** `Path`.

### `def _atomic_replace(src: Path, dst: Path) -> None`

Substitui um arquivo de destino de forma atômica após gravação temporária.

**Entrada:** `src: Path`, `dst: Path`.

**Saída:** `None`.

### `def list_drcalc_backups(data_dir: str | Path | None=None) -> list[dict[str, Any]]`

Lista backups locais das planilhas de índices.

**Entrada:** `data_dir: str | Path | None`.

**Saída:** `list[dict[str, Any]]`.

### `def restaurar_backup_drcalc(backup_id_or_path: str, *, data_dir: str | Path | None=None) -> DrCalcUpdateResult`

Restaura as planilhas a partir de um backup criado pelo atualizador.

**Entrada:** `backup_id_or_path: str`, `data_dir: str | Path | None`.

**Saída:** `DrCalcUpdateResult`.

### `def _clear_local_caches() -> None`

Limpa caches de leitura de índices para que os próximos cálculos usem os arquivos atuais.

**Entrada:** nenhuma entrada explícita.

**Saída:** `None`.

### `def _acquire_lock(data_dir: Path, wait_seconds: int=20) -> bool`

Adquire o lock de atualização e retorna o recurso usado para liberação posterior.

**Entrada:** `data_dir: Path`, `wait_seconds: int`.

**Saída:** `bool`.

### `def _release_lock(data_dir: Path) -> None`

Libera o lock de atualização adquirido pelo processo.

**Entrada:** `data_dir: Path`.

**Saída:** `None`.

## `src/judicial_calc/data_sources/drcalc/models.py`

Tipos e constantes compartilhados pela integração DrCalc.

### `class DrCalcRecord`

Uma observação extraída de uma série do DrCalc.

**Atributos declarados:** `periodo: date | str`, `valor: Decimal`.


### `class DrCalcSeries`

Série histórica extraída de uma página do DrCalc.

**Atributos declarados:** `name: str`, `url: str`, `category: str`, `records: list[DrCalcRecord]`, `periodicity: str`, `raw_columns: list[str]`, `metric: str`.


### `class DrCalcUpdateResult`

Resultado rastreável da tentativa de atualização.

**Atributos declarados:** `executed: bool`, `skipped: bool`, `success: bool`, `date: str`, `message: str`, `backup_dir: str | None`, `updated_files: list[str]`, `updated_series: list[str]`, `preserved_columns: list[str]`, `source_url: str`, `categories: list[str]`, `row_counts: dict[str, int]`, `previous_row_counts: dict[str, int]`, `diff_summary: list[dict[str, Any]]`, `consistency_checks: list[dict[str, Any]]`, `has_new_competence: bool`, `new_competencies: list[dict[str, str]]`, `restored_backup: str | None`, `errors: list[str]`.

**Métodos:**

- `def to_dict(self) -> dict[str, Any]` — Serializa o resultado da atualização do DrCalc para um dicionário simples e rastreável.
  - Entrada: nenhuma entrada explícita.
  - Saída: `dict[str, Any]`.

### `class DrCalcUpdateError(RuntimeError)`

Falha controlada da atualização das planilhas locais.


## `src/judicial_calc/data_sources/drcalc/parsing.py`

Normalização de texto, números, períodos e URLs da fonte DrCalc.

### `def _normalize_text(value: Any) -> str`

Normaliza texto HTML para comparação de títulos e cabeçalhos de séries.

**Entrada:** `value: Any`.

**Saída:** `str`.

### `def _decimal_from_ptbr(value: Any) -> Decimal | None`

Converte números em formatos PT-BR/EN para Decimal.

**Entrada:** `value: Any`.

**Saída:** `Decimal | None`.

### `def _parse_date_like(value: Any) -> date | str | None`

Normaliza datas/competências extraídas do HTML.

**Entrada:** `value: Any`.

**Saída:** `date | str | None`.

### `def _periodicity(records: Iterable[DrCalcRecord]) -> str`

Infere a periodicidade de uma série a partir dos períodos observados.

**Entrada:** `records: Iterable[DrCalcRecord]`.

**Saída:** `str`.

### `def _competencia_from_period(periodo: date | str) -> str`

Converte um período mensal para a competência canônica AAAA-MM.

**Entrada:** `periodo: date | str`.

**Saída:** `str`.

### `def _build_category_url(category_id: int) -> str`

Monta a URL inicial de uma categoria do DrCalc.

**Entrada:** `category_id: int`.

**Saída:** `str`.

## `src/judicial_calc/data_sources/drcalc/service.py`

Orquestra download, staging, validação, promoção e fallback dos índices.

### `def baixar_series_drcalc(timeout: int=30) -> list[DrCalcSeries]`

Baixa as séries disponíveis nas três categorias alvo do DrCalc.

**Entrada:** `timeout: int`.

**Saída:** `list[DrCalcSeries]`.

### `def atualizar_planilhas_drcalc(*, data_dir: str | Path | None=None, timeout: int=30, series_list: list[DrCalcSeries] | None=None) -> DrCalcUpdateResult`

Força atualização das três planilhas locais a partir do DrCalc.

**Entrada:** `data_dir: str | Path | None`, `timeout: int`, `series_list: list[DrCalcSeries] | None`.

**Saída:** `DrCalcUpdateResult`.

### `def atualizar_planilhas_drcalc_se_necessario(*, data_dir: str | Path | None=None, force: bool=False, timeout: int=30, strict: bool=False) -> DrCalcUpdateResult`

Atualiza as planilhas apenas uma vez por dia.

**Entrada:** `data_dir: str | Path | None`, `force: bool`, `timeout: int`, `strict: bool`.

**Saída:** `DrCalcUpdateResult`.

## `src/judicial_calc/data_sources/drcalc/workbook.py`

Seleção, mesclagem e validação das planilhas de índices.

### `def _series_score(series_name: str, target_label: str, extra_aliases: Iterable[str]=()) -> int`

Calcula uma pontuação heurística para escolher a série mais compatível com um destino.

**Entrada:** `series_name: str`, `target_label: str`, `extra_aliases: Iterable[str]`.

**Saída:** `int`.

### `def _looks_like_rate_percent(series: DrCalcSeries) -> bool`

Avalia de forma conservadora se uma série sem unidade parece percentual.

**Entrada:** `series: DrCalcSeries`.

**Saída:** `bool`.

### `def _best_series_for_monthly_column(column: str, series_list: list[DrCalcSeries]) -> DrCalcSeries | None`

Seleciona a melhor série mensal para alimentar uma coluna da planilha local.

**Entrada:** `column: str`, `series_list: list[DrCalcSeries]`.

**Saída:** `DrCalcSeries | None`.

### `def _best_daily_series(kind: str, series_list: list[DrCalcSeries]) -> DrCalcSeries | None`

Seleciona a melhor série diária entre as séries descobertas.

**Entrada:** `kind: str`, `series_list: list[DrCalcSeries]`.

**Saída:** `DrCalcSeries | None`.

### `def _convert_monthly_value(column: str, valor: Decimal, *, source_metric: str='unknown') -> Decimal`

Converte o valor mensal da fonte para a unidade esperada pela planilha local.

**Entrada:** `column: str`, `valor: Decimal`, `source_metric: str`.

**Saída:** `Decimal`.

### `def _convert_daily_value(valor: Decimal, *, source_metric: str='unknown') -> Decimal`

Converte o valor diário da fonte para a unidade esperada pela planilha local.

**Entrada:** `valor: Decimal`, `source_metric: str`.

**Saída:** `Decimal`.

### `def _monthly_dataframe_from_workbook(path: Path) -> pd.DataFrame`

Lê a planilha mensal existente e normaliza seu conteúdo em DataFrame.

**Entrada:** `path: Path`.

**Saída:** `pd.DataFrame`.

### `def _daily_dataframe_from_workbook(path: Path) -> pd.DataFrame`

Lê a planilha diária existente e normaliza seu conteúdo em DataFrame.

**Entrada:** `path: Path`.

**Saída:** `pd.DataFrame`.

### `def _write_monthly_workbook(df: pd.DataFrame, path: Path) -> None`

Grava a tabela mensal normalizada no arquivo Excel de destino.

**Entrada:** `df: pd.DataFrame`, `path: Path`.

**Saída:** `None`.

### `def _write_daily_workbook(df: pd.DataFrame, path: Path) -> None`

Grava a tabela diária normalizada no arquivo Excel de destino.

**Entrada:** `df: pd.DataFrame`, `path: Path`.

**Saída:** `None`.

### `def _merge_monthly(existing_path: Path, series_list: list[DrCalcSeries]) -> tuple[pd.DataFrame, list[str], list[str]]`

Combina séries mensais baixadas com a estrutura da planilha local.

**Entrada:** `existing_path: Path`, `series_list: list[DrCalcSeries]`.

**Saída:** `tuple[pd.DataFrame, list[str], list[str]]`.

### `def _merge_daily(existing_path: Path, series: DrCalcSeries | None, label: str) -> tuple[pd.DataFrame, list[str]]`

Combina a série diária baixada com a estrutura da planilha local.

**Entrada:** `existing_path: Path`, `series: DrCalcSeries | None`, `label: str`.

**Saída:** `tuple[pd.DataFrame, list[str]]`.

### `def _validate_outputs(monthly: pd.DataFrame, daily_selic_ipcae: pd.DataFrame, daily_12_6: pd.DataFrame) -> None`

Valida se as planilhas produzidas possuem estrutura e conteúdo mínimos esperados.

**Entrada:** `monthly: pd.DataFrame`, `daily_selic_ipcae: pd.DataFrame`, `daily_12_6: pd.DataFrame`.

**Saída:** `None`.

### `def _df_row_count(path: Path, *, daily: bool=False) -> int`

Conta linhas úteis de uma planilha local de índices.

**Entrada:** `path: Path`, `daily: bool`.

**Saída:** `int`.

### `def _df_date_range(df: pd.DataFrame, date_col: str='data') -> tuple[str, str]`

Retorna intervalo textual mínimo/máximo de datas/competências.

**Entrada:** `df: pd.DataFrame`, `date_col: str`.

**Saída:** `tuple[str, str]`.

### `def _build_diff_row(filename: str, before_rows: int, after_df: pd.DataFrame) -> dict[str, Any]`

Resume diferença de linhas e intervalo de datas de uma planilha.

**Entrada:** `filename: str`, `before_rows: int`, `after_df: pd.DataFrame`.

**Saída:** `dict[str, Any]`.

### `def _monthly_last_competence_by_column(df: pd.DataFrame) -> dict[str, str]`

Obtém a última competência não nula de cada série mensal.

**Entrada:** `df: pd.DataFrame`.

**Saída:** `dict[str, str]`.

### `def _daily_last_competence(df: pd.DataFrame) -> str`

Retorna a última data útil de uma série diária como texto ISO.

**Entrada:** `df: pd.DataFrame`.

**Saída:** `str`.

### `def _coverage_advancements(before_monthly: pd.DataFrame, after_monthly: pd.DataFrame, before_daily_selic: pd.DataFrame, after_daily_selic: pd.DataFrame, before_daily_12_6: pd.DataFrame, after_daily_12_6: pd.DataFrame) -> list[dict[str, str]]`

Lista somente séries cuja competência máxima realmente avançou.

**Entrada:** `before_monthly: pd.DataFrame`, `after_monthly: pd.DataFrame`, `before_daily_selic: pd.DataFrame`, `after_daily_selic: pd.DataFrame`, `before_daily_12_6: pd.DataFrame`, `after_daily_12_6: pd.DataFrame`.

**Saída:** `list[dict[str, str]]`.

### `def _consistency_checks(monthly: pd.DataFrame, daily_selic_ipcae: pd.DataFrame, daily_12_6: pd.DataFrame) -> list[dict[str, Any]]`

Gera checagens legíveis para a tela administrativa de índices.

**Entrada:** `monthly: pd.DataFrame`, `daily_selic_ipcae: pd.DataFrame`, `daily_12_6: pd.DataFrame`.

**Saída:** `list[dict[str, Any]]`.

## `src/judicial_calc/data_sources/http_client.py`

Sessão HTTP compartilhada pelas consultas públicas do motor.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/data_sources/local_excel.py`

Leitura das planilhas locais usadas nos cálculos judiciais.

### `class LocalIndexSpec`

Metadados de uma coluna de índice na tabela mensal local.

**Atributos declarados:** `key: str`, `column: str`, `mode: IndexMode`, `aliases: tuple[str, ...]`.


### `class MissingLocalIndexSpec`

Metadados de índice conhecido, mas sem coluna na planilha local.

**Atributos declarados:** `key: str`, `label: str`, `available_range: str`.


### `class LocalIndexCoverage`

Cobertura efetivamente observada para uma coluna da planilha mensal.

**Atributos declarados:** `key: str`, `label: str`, `mode: IndexMode`, `first_competence: str`, `last_competence: str`, `maximum_update_competence: str`.


### `def _resource_path(filename: str) -> Path`

Resolve o caminho de uma planilha empacotada no projeto.

**Entrada:** `filename: str`.

**Saída:** `Path`.

### `def normalize_key(text: str) -> str`

Normaliza nomes e rótulos de índices para chaves seguras de API.

**Entrada:** `text: str`.

**Saída:** `str`.

### `def _spec(key: str, column: str, mode: IndexMode, *aliases: str) -> LocalIndexSpec`

Cria a especificação de uma coluna mensal com aliases normalizados.

**Entrada:** `key: str`, `column: str`, `mode: IndexMode`, `*aliases: str`.

**Saída:** `LocalIndexSpec`.

### `def local_index_specs() -> tuple[LocalIndexSpec, ...]`

Lista os índices efetivamente disponíveis na planilha mensal.

**Entrada:** nenhuma entrada explícita.

**Saída:** `tuple[LocalIndexSpec, ...]`.

### `def local_missing_index_specs() -> tuple[MissingLocalIndexSpec, ...]`

Lista índices conhecidos, mas sem dados na planilha mensal.

**Entrada:** nenhuma entrada explícita.

**Saída:** `tuple[MissingLocalIndexSpec, ...]`.

### `def resolve_index_key(key_or_label: str) -> str`

Resolve aliases para a chave técnica do índice.

**Entrada:** `key_or_label: str`.

**Saída:** `str`.

### `def get_index_spec(key_or_label: str) -> LocalIndexSpec`

Obtém metadados de um índice local.

**Entrada:** `key_or_label: str`.

**Saída:** `LocalIndexSpec`.

### `def _decimal_or_none(value: Any) -> Decimal | None`

Converte célula de planilha para ``Decimal`` ou ``None``.

**Entrada:** `value: Any`.

**Saída:** `Decimal | None`.

### `def _month_from_cell(value: Any) -> str | None`

Converte célula de competência mensal para ``AAAA-MM``.

**Entrada:** `value: Any`.

**Saída:** `str | None`.

### `def _date_from_cell(value: Any) -> date`

Converte célula diária da planilha para ``datetime.date``.

**Entrada:** `value: Any`.

**Saída:** `date`.

### `def load_monthly_indices(path: str | None=None) -> pd.DataFrame`

Carrega a tabela mensal local em formato largo.

**Entrada:** `path: str | None`.

**Saída:** `pd.DataFrame`.

### `def load_index_series(key_or_label: str, path: str | None=None) -> pd.DataFrame`

Retorna a série mensal de uma chave local.

**Entrada:** `key_or_label: str`, `path: str | None`.

**Saída:** `pd.DataFrame`.

### `def local_index_coverage(key_or_label: str, path: str | None=None) -> LocalIndexCoverage`

Retorna o intervalo real de uma série, sem datas escritas manualmente.

**Entrada:** `key_or_label: str`, `path: str | None`.

**Saída:** `LocalIndexCoverage`.

### `def load_taxa_legal_mensal_percentual(path: str | None=None) -> pd.DataFrame`

Carrega a coluna mensal da Taxa Legal em percentual ao mês.

**Entrada:** `path: str | None`.

**Saída:** `pd.DataFrame`.

### `def load_daily_rate_table(kind: str, path: str | None=None) -> pd.DataFrame`

Carrega uma tabela diária local de taxas em decimal ao dia.

**Entrada:** `kind: str`, `path: str | None`.

**Saída:** `pd.DataFrame`.

### `def available_indices() -> pd.DataFrame`

Retorna uma tabela de índices locais disponíveis.

**Entrada:** nenhuma entrada explícita.

**Saída:** `pd.DataFrame`.

### `def missing_indices() -> pd.DataFrame`

Retorna índices conhecidos que não possuem coluna na planilha.

**Entrada:** nenhuma entrada explícita.

**Saída:** `pd.DataFrame`.

## `src/judicial_calc/extraction/__init__.py`

Contratos e extratores usados para obter séries externas em formato tabular.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/extraction/base.py`

Contratos simples para extratores de tabelas mensais.

### `class MonthlyTableExtractor(ABC)`

Interface para fontes que entregam séries mensais.

**Atributos declarados:** `source_name: str`, `value_column: str`.

**Métodos:**

- `def extract(self, inicio: str, fim: str) -> pd.DataFrame` — Extrai uma janela mensal fechada.
  - Entrada: `inicio: str`, `fim: str`.
  - Saída: `pd.DataFrame`.

### `class InMemoryMonthlyTableExtractor(MonthlyTableExtractor)`

Extrator para tabelas já carregadas em memória.

**Métodos:**

- `def __init__(self, tabela: pd.DataFrame | list[dict[str, Any]], value_column: str='indice') -> None` — Armazena a tabela que será filtrada posteriormente.
  - Entrada: `tabela: pd.DataFrame | list[dict[str, Any]]`, `value_column: str`.
  - Saída: `None`.
- `def extract(self, inicio: str, fim: str) -> pd.DataFrame` — Filtra a tabela de memória no intervalo mensal.
  - Entrada: `inicio: str`, `fim: str`.
  - Saída: `pd.DataFrame`.

## `src/judicial_calc/extraction/sgs.py`

Download de séries mensais e diárias do SGS/Bacen.

### `def _baixar_sgs_curto(codigo: int, nome: str, inicio: str, fim: str) -> pd.DataFrame`

Baixa um bloco mensal curto do SGS e consolida por competência.

**Entrada:** `codigo: int`, `nome: str`, `inicio: str`, `fim: str`.

**Saída:** `pd.DataFrame`.

### `def baixar_sgs(codigo: int, nome: str, inicio: str, fim: str) -> pd.DataFrame`

Baixa série mensal do SGS/Bacen em blocos seguros.

**Entrada:** `codigo: int`, `nome: str`, `inicio: str`, `fim: str`.

**Saída:** `pd.DataFrame`.

### `def _baixar_sgs_diario_curto(codigo: int, nome: str, data_inicio: date, data_fim: date) -> pd.DataFrame`

Baixa um bloco diário curto do SGS/Bacen.

**Entrada:** `codigo: int`, `nome: str`, `data_inicio: date`, `data_fim: date`.

**Saída:** `pd.DataFrame`.

### `def baixar_sgs_diario(codigo: int, nome: str, data_inicio: date, data_fim: date) -> pd.DataFrame`

Baixa uma série diária do SGS preservando cada data observada.

**Entrada:** `codigo: int`, `nome: str`, `data_inicio: date`, `data_fim: date`.

**Saída:** `pd.DataFrame`.

### `class SGSMonthlyExtractor(MonthlyTableExtractor)`

Extrator mensal para uma série SGS/Bacen.

**Métodos:**

- `def __init__(self, codigo: int, nome: str) -> None` — Armazena metadados da série SGS.
  - Entrada: `codigo: int`, `nome: str`.
  - Saída: `None`.
- `def extract(self, inicio: str, fim: str) -> pd.DataFrame` — Baixa a janela mensal configurada no extrator.
  - Entrada: `inicio: str`, `fim: str`.
  - Saída: `pd.DataFrame`.

## `src/judicial_calc/indices/__init__.py`

Estratégias de correção monetária e resolução das séries de índices.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/indices/base.py`

Estratégias base para correção monetária.

### `class CorrectionIndexStrategy(ABC)`

Contrato para qualquer índice de correção monetária.

**Atributos declarados:** `key: str`.

**Métodos:**

- `def final_competence(self, competencia_atualizacao: str) -> str` — Retorna a competência final usada no cálculo do índice.
  - Entrada: `competencia_atualizacao: str`.
  - Saída: `str`.
- `def factor(self, *, data_parcela: date, competencia_atualizacao: str, tabela_indices: pd.DataFrame | list[dict[str, Any]] | None, deflacionar_valor_nominal: bool) -> Decimal` — Calcula o fator de correção da parcela.
  - Entrada: `data_parcela: date`, `competencia_atualizacao: str`, `tabela_indices: pd.DataFrame | list[dict[str, Any]] | None`, `deflacionar_valor_nominal: bool`.
  - Saída: `Decimal`.
- `def _apply_floor(self, fator: Decimal, deflacionar_valor_nominal: bool) -> Decimal` — Aplica piso de fator mínimo igual a um quando não há deflação.
  - Entrada: `fator: Decimal`, `deflacionar_valor_nominal: bool`.
  - Saída: `Decimal`.

### `class NoCorrectionIndex(CorrectionIndexStrategy)`

Estratégia que não aplica correção monetária.

**Atributos declarados:** `key: tipo inferido em execução`.

**Métodos:**

- `def final_competence(self, competencia_atualizacao: str) -> str` — Retorna o mês anterior por consistência com índices mensais.
  - Entrada: `competencia_atualizacao: str`.
  - Saída: `str`.
- `def factor(self, *, data_parcela: date, competencia_atualizacao: str, tabela_indices: pd.DataFrame | list[dict[str, Any]] | None, deflacionar_valor_nominal: bool) -> Decimal` — Retorna fator neutro para qualquer parcela.
  - Entrada: `data_parcela: date`, `competencia_atualizacao: str`, `tabela_indices: pd.DataFrame | list[dict[str, Any]] | None`, `deflacionar_valor_nominal: bool`.
  - Saída: `Decimal`.

### `class ValueTableCorrectionIndex(CorrectionIndexStrategy)`

Correção por tabela customizada de número-índice mensal.

**Métodos:**

- `def __init__(self, key: str='custom_value_table', final_uses_update_month: bool=False) -> None` — Inicializa a estratégia de tabela customizada.
  - Entrada: `key: str`, `final_uses_update_month: bool`.
  - Saída: `None`.
- `def final_competence(self, competencia_atualizacao: str) -> str` — Retorna a competência final da tabela customizada.
  - Entrada: `competencia_atualizacao: str`.
  - Saída: `str`.
- `def factor(self, *, data_parcela: date, competencia_atualizacao: str, tabela_indices: pd.DataFrame | list[dict[str, Any]] | None, deflacionar_valor_nominal: bool) -> Decimal` — Calcula fator pela tabela customizada do usuário.
  - Entrada: `data_parcela: date`, `competencia_atualizacao: str`, `tabela_indices: pd.DataFrame | list[dict[str, Any]] | None`, `deflacionar_valor_nominal: bool`.
  - Saída: `Decimal`.

### `def fator_tabela_valor_mensal(tabela: pd.DataFrame | list[dict[str, Any]], inicio: str, fim: str) -> Decimal`

Calcula fator por tabela de número-índice mensal.

**Entrada:** `tabela: pd.DataFrame | list[dict[str, Any]]`, `inicio: str`, `fim: str`.

**Saída:** `Decimal`.

## `src/judicial_calc/indices/local_excel.py`

Estratégias de correção monetária baseadas na planilha mensal local.

### `def _series_map(tabela: Tabela) -> dict[str, Decimal]`

Normaliza uma tabela mensal em dicionário de acesso rápido.

**Entrada:** `tabela: Tabela`.

**Saída:** `dict[str, Decimal]`.

### `def _default_series_map(key: str) -> dict[str, Decimal]`

Carrega e cacheia a série mensal local de uma chave de índice.

**Entrada:** `key: str`.

**Saída:** `dict[str, Decimal]`.

### `def _fator_por_taxa_decimal_map(mapa: dict[str, Decimal], inicio: str, fim: str) -> Decimal`

Acumula variações mensais em decimal usando um mapa já normalizado.

**Entrada:** `mapa: dict[str, Decimal]`, `inicio: str`, `fim: str`.

**Saída:** `Decimal`.

### `def _fator_por_numero_indice_map(mapa: dict[str, Decimal], inicio: str, fim: str) -> Decimal`

Calcula fator por razão entre número-índice final e inicial.

**Entrada:** `mapa: dict[str, Decimal]`, `inicio: str`, `fim: str`.

**Saída:** `Decimal`.

### `def fator_por_taxa_decimal(tabela: Tabela, inicio: str, fim: str) -> Decimal`

Acumula uma tabela mensal de taxas decimais.

**Entrada:** `tabela: Tabela`, `inicio: str`, `fim: str`.

**Saída:** `Decimal`.

### `def fator_por_numero_indice(tabela: Tabela, inicio: str, fim: str) -> Decimal`

Calcula fator de correção por número-índice mensal.

**Entrada:** `tabela: Tabela`, `inicio: str`, `fim: str`.

**Saída:** `Decimal`.

### `class LocalExcelCorrectionIndex(CorrectionIndexStrategy)`

Estratégia de correção por uma coluna do arquivo ``taxas_mensais.xlsx``.

**Métodos:**

- `def __init__(self, spec: LocalIndexSpec) -> None` — Inicializa a estratégia e seus aliases públicos.
  - Entrada: `spec: LocalIndexSpec`.
  - Saída: `None`.
- `def final_competence(self, competencia_atualizacao: str) -> str` — Retorna a competência final usada no índice.
  - Entrada: `competencia_atualizacao: str`.
  - Saída: `str`.
- `def factor(self, *, data_parcela: date, competencia_atualizacao: str, tabela_indices: pd.DataFrame | list[dict[str, Any]] | None, deflacionar_valor_nominal: bool) -> Decimal` — Calcula o fator de correção monetária de uma parcela.
  - Entrada: `data_parcela: date`, `competencia_atualizacao: str`, `tabela_indices: pd.DataFrame | list[dict[str, Any]] | None`, `deflacionar_valor_nominal: bool`.
  - Saída: `Decimal`.

### `def create_local_excel_index_strategies() -> list[LocalExcelCorrectionIndex]`

Cria as estratégias para todas as colunas cadastradas na planilha.

**Entrada:** nenhuma entrada explícita.

**Saída:** `list[LocalExcelCorrectionIndex]`.

### `def is_local_excel_index(key_or_label: str) -> bool`

Verifica se uma chave ou rótulo existe na planilha local.

**Entrada:** `key_or_label: str`.

**Saída:** `bool`.

## `src/judicial_calc/indices/registry.py`

Registro central das estratégias de correção monetária.

### `class IndexRegistry`

Mapa de chaves de índices para suas estratégias de cálculo.

**Métodos:**

- `def __init__(self) -> None` — Cria um registro vazio de estratégias.
  - Entrada: nenhuma entrada explícita.
  - Saída: `None`.
- `def register(self, strategy: CorrectionIndexStrategy, *aliases: str, overwrite: bool=True) -> None` — Registra uma estratégia por chave principal e aliases.
  - Entrada: `strategy: CorrectionIndexStrategy`, `*aliases: str`, `overwrite: bool`.
  - Saída: `None`.
- `def get(self, key: str) -> CorrectionIndexStrategy | None` — Busca uma estratégia pelo nome do índice.
  - Entrada: `key: str`.
  - Saída: `CorrectionIndexStrategy | None`.
- `def names(self) -> list[str]` — Lista as chaves registradas em ordem alfabética.
  - Entrada: nenhuma entrada explícita.
  - Saída: `list[str]`.

### `def create_default_index_registry() -> IndexRegistry`

Monta e cacheia o registro padrão de índices.

**Entrada:** nenhuma entrada explícita.

**Saída:** `IndexRegistry`.

### `def resolve_index_strategy(indice: str, tabela_indices_informada: bool=False) -> CorrectionIndexStrategy`

Resolve a estratégia de correção monetária a partir da chave informada.

**Entrada:** `indice: str`, `tabela_indices_informada: bool`.

**Saída:** `CorrectionIndexStrategy`.

## `src/judicial_calc/indices/sgs_percentage.py`

Índices de correção obtidos de séries percentuais mensais SGS/Bacen.

### `def fator_percentual_mensal_por_tabela(tabela: pd.DataFrame | list[dict[str, Any]], competencia_inicio: str, competencia_fim: str, coluna_preferida: str) -> Decimal`

Acumula uma tabela mensal de percentuais.

**Entrada:** `tabela: pd.DataFrame | list[dict[str, Any]]`, `competencia_inicio: str`, `competencia_fim: str`, `coluna_preferida: str`.

**Saída:** `Decimal`.

### `def fator_percentual_mensal(indice: str, competencia_inicio: str, competencia_fim: str) -> Decimal`

Baixa e acumula um índice percentual mensal do SGS.

**Entrada:** `indice: str`, `competencia_inicio: str`, `competencia_fim: str`.

**Saída:** `Decimal`.

### `class SGSPercentageCorrectionIndex(CorrectionIndexStrategy)`

Estratégia de correção por série percentual mensal SGS.

**Métodos:**

- `def __init__(self, key: str, codigo: int, value_column: str) -> None` — Inicializa os metadados da série SGS.
  - Entrada: `key: str`, `codigo: int`, `value_column: str`.
  - Saída: `None`.
- `def final_competence(self, competencia_atualizacao: str) -> str` — Usa a competência anterior ao mês de atualização.
  - Entrada: `competencia_atualizacao: str`.
  - Saída: `str`.
- `def factor(self, *, data_parcela: date, competencia_atualizacao: str, tabela_indices: pd.DataFrame | list[dict[str, Any]] | None, deflacionar_valor_nominal: bool) -> Decimal` — Calcula o fator de correção pela série SGS.
  - Entrada: `data_parcela: date`, `competencia_atualizacao: str`, `tabela_indices: pd.DataFrame | list[dict[str, Any]] | None`, `deflacionar_valor_nominal: bool`.
  - Saída: `Decimal`.

## `src/judicial_calc/interest/__init__.py`

Regras de juros moratórios, separadas por forma de cálculo e fonte de taxa.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/interest/daily_rates.py`

Juros moratórios por tabelas diárias locais.

### `def _normalizar_tabela_diaria(tabela: Tabela, kind: str) -> pd.DataFrame`

Normaliza uma tabela diária para cálculo de juros.

**Entrada:** `tabela: Tabela`, `kind: str`.

**Saída:** `pd.DataFrame`.

### `def _data_fim_periodo(competencia_atualizacao: str, competencia_final_taxa_legal: str | None) -> date`

Define o último dia do período diário a acumular.

**Entrada:** `competencia_atualizacao: str`, `competencia_final_taxa_legal: str | None`.

**Saída:** `date`.

### `def soma_taxas_diarias(*, data_inicio: date, data_fim: date, tabela_diaria: Tabela, kind: str) -> tuple[Decimal, Decimal]`

Soma taxas diárias em decimal dentro de um intervalo fechado.

**Entrada:** `data_inicio: date`, `data_fim: date`, `tabela_diaria: Tabela`, `kind: str`.

**Saída:** `tuple[Decimal, Decimal]`.

### `def _taxa_legal_decimal_competencia(competencia: str) -> Decimal`

Obtém a Taxa Legal mensal local em decimal para uma competência.

**Entrada:** `competencia: str`.

**Saída:** `Decimal`.

### `def _percentual_selic_ipcae_diario(*, data_inicio: date, data_fim: date, tabela_diaria: Tabela, competencia_atualizacao: str, aplicar_extensao_pos_tabela: bool) -> tuple[Decimal, Decimal]`

Soma a tabela diária SELIC-IPCAE e eventual extensão mensal.

**Entrada:** `data_inicio: date`, `data_fim: date`, `tabela_diaria: Tabela`, `competencia_atualizacao: str`, `aplicar_extensao_pos_tabela: bool`.

**Saída:** `tuple[Decimal, Decimal]`.

### `def calcular_juros_moratorios_diario(*, valor_base: Decimal, data_inicio: date, competencia_atualizacao: str, tabela_diaria: Tabela, competencia_final_taxa_legal: str | None, kind: str, aplicar_extensao_pos_tabela: bool=False) -> tuple[Decimal, Decimal, Decimal]`

Calcula juros moratórios pela soma de taxas diárias.

**Entrada:** `valor_base: Decimal`, `data_inicio: date`, `competencia_atualizacao: str`, `tabela_diaria: Tabela`, `competencia_final_taxa_legal: str | None`, `kind: str`, `aplicar_extensao_pos_tabela: bool`.

**Saída:** `tuple[Decimal, Decimal, Decimal]`.

## `src/judicial_calc/interest/fixed.py`

Cálculo de juros fixos simples ou compostos.

### `def meses_juros_simples(data_inicio: date, competencia_atualizacao: str, pro_rata: bool=False) -> Decimal`

Conta meses de juros simples até a competência de atualização.

**Entrada:** `data_inicio: date`, `competencia_atualizacao: str`, `pro_rata: bool`.

**Saída:** `Decimal`.

### `def _periodos_compostos(data_inicio: date, competencia_atualizacao: str, periodicidade: str) -> Decimal`

Conta períodos inteiros usados na capitalização composta.

**Entrada:** `data_inicio: date`, `competencia_atualizacao: str`, `periodicidade: str`.

**Saída:** `Decimal`.

### `def calcular_juros_fixo(valor_base: Decimal, data_inicio: date, competencia_atualizacao: str, taxa: str | Decimal | int | float, periodicidade: str='mensal', pro_rata: bool=False, tipo: str='capitalizacao_simples') -> tuple[Decimal, Decimal, Decimal]`

Calcula juros fixos simples ou compostos.

**Entrada:** `valor_base: Decimal`, `data_inicio: date`, `competencia_atualizacao: str`, `taxa: str | Decimal | int | float`, `periodicidade: str`, `pro_rata: bool`, `tipo: str`.

**Saída:** `tuple[Decimal, Decimal, Decimal]`.

## `src/judicial_calc/interest/service.py`

Seleciona a forma de calcular juros moratórios a partir do tipo configurado.

### `def calcular_juros(*, valor_base: Decimal, valor_nominal: Decimal, data_parcela: date, competencia_atualizacao: str, taxa: Any, periodicidade: str, pro_rata: bool, tipo: str, data_inicio: str | date | None, tabela_taxa_legal: pd.DataFrame | list[dict[str, Any]] | None, tabela_selic: pd.DataFrame | list[dict[str, Any]] | None, tabela_selic_diaria: pd.DataFrame | list[dict[str, Any]] | None, tabela_ipca_deducao: pd.DataFrame | list[dict[str, Any]] | None, tabela_taxa_legal_diaria_selic_ipcae: pd.DataFrame | list[dict[str, Any]] | None=None, tabela_taxa_legal_diaria_12_6: pd.DataFrame | list[dict[str, Any]] | None=None, competencia_final_taxa_legal: str | None=None, deduzir_correcao_pre_lei: bool=True, aplicar_taxa_legal_pos_lei: bool=True, data_fim_selic_stj1368: date | None=None, competencia_final_taxa_legal_stj1368: str | None=None, usar_selic_mensal_sem_deducao: bool=False) -> tuple[Decimal, Decimal, Decimal]`

Seleciona e executa a regra de juros aplicável.

**Entrada:** `valor_base: Decimal`, `valor_nominal: Decimal`, `data_parcela: date`, `competencia_atualizacao: str`, `taxa: Any`, `periodicidade: str`, `pro_rata: bool`, `tipo: str`, `data_inicio: str | date | None`, `tabela_taxa_legal: pd.DataFrame | list[dict[str, Any]] | None`, `tabela_selic: pd.DataFrame | list[dict[str, Any]] | None`, `tabela_selic_diaria: pd.DataFrame | list[dict[str, Any]] | None`, `tabela_ipca_deducao: pd.DataFrame | list[dict[str, Any]] | None`, `tabela_taxa_legal_diaria_selic_ipcae: pd.DataFrame | list[dict[str, Any]] | None`, `tabela_taxa_legal_diaria_12_6: pd.DataFrame | list[dict[str, Any]] | None`, `competencia_final_taxa_legal: str | None`, `deduzir_correcao_pre_lei: bool`, `aplicar_taxa_legal_pos_lei: bool`, `data_fim_selic_stj1368: date | None`, `competencia_final_taxa_legal_stj1368: str | None`, `usar_selic_mensal_sem_deducao: bool`.

**Saída:** `tuple[Decimal, Decimal, Decimal]`.

## `src/judicial_calc/interest/taxa_legal.py`

Juros legais especiais usados para replicar opções do critério de referência.

### `def _normalizar_percentual_mensal(tabela: pd.DataFrame | list[dict[str, Any]], coluna: str) -> pd.DataFrame`

Normaliza uma tabela mensal percentual.

**Entrada:** `tabela: pd.DataFrame | list[dict[str, Any]]`, `coluna: str`.

**Saída:** `pd.DataFrame`.

### `def _normalizar_selic_diaria(tabela: pd.DataFrame | list[dict[str, Any]]) -> pd.DataFrame`

Normaliza tabela diária da Selic.

**Entrada:** `tabela: pd.DataFrame | list[dict[str, Any]]`.

**Saída:** `pd.DataFrame`.

### `def _mapa_mensal(tabela: pd.DataFrame, coluna: str) -> dict[str, Decimal]`

Converte tabela mensal normalizada em dicionário ``{AAAA-MM: Decimal}``.

**Entrada:** `tabela: pd.DataFrame`, `coluna: str`.

**Saída:** `dict[str, Decimal]`.

### `def _acumular_percentuais_mensais(comps: Iterable[str], mapa: dict[str, Decimal], nome: str) -> Decimal`

Acumula percentuais mensais em fator composto.

**Entrada:** `comps: Iterable[str]`, `mapa: dict[str, Decimal]`, `nome: str`.

**Saída:** `Decimal`.

### `def baixar_tabela_taxa_legal_oficial(inicio: str, fim: str) -> pd.DataFrame`

Baixa a Taxa Legal oficial do Bacen/SGS 29543.

**Entrada:** `inicio: str`, `fim: str`.

**Saída:** `pd.DataFrame`.

### `def gerar_tabela_taxa_legal(inicio: str, fim: str) -> pd.DataFrame`

Gera tabela mensal da Taxa Legal usando exclusivamente SGS 29543.

**Entrada:** `inicio: str`, `fim: str`.

**Saída:** `pd.DataFrame`.

### `def baixar_tabela_selic_mensal(inicio: str, fim: str) -> pd.DataFrame`

Baixa Selic mensal acumulada no mês, SGS 4390.

**Entrada:** `inicio: str`, `fim: str`.

**Saída:** `pd.DataFrame`.

### `def baixar_tabela_selic_diaria(data_inicio: date, data_fim: date) -> pd.DataFrame`

Baixa Selic diária, SGS 11, preservando todas as datas da série.

**Entrada:** `data_inicio: date`, `data_fim: date`.

**Saída:** `pd.DataFrame`.

### `def baixar_tabela_ipca_deducao(inicio: str, fim: str, codigo_sgs: int=SGS_IPCA_15) -> pd.DataFrame`

Baixa a inflação usada como dedução no modo STJ 1368.

**Entrada:** `inicio: str`, `fim: str`, `codigo_sgs: int`.

**Saída:** `pd.DataFrame`.

### `def resolver_competencia_final_taxa_legal(competencia_atualizacao: str, competencia_final_taxa_legal: str | None) -> str`

Resolve a última competência usada em juros/Taxa Legal.

**Entrada:** `competencia_atualizacao: str`, `competencia_final_taxa_legal: str | None`.

**Saída:** `str`.

### `def _tabela_taxa_legal(inicio: str, fim: str, tabela_taxa_legal: Tabela) -> pd.DataFrame`

Obtém tabela mensal da Taxa Legal para o intervalo solicitado.

**Entrada:** `inicio: str`, `fim: str`, `tabela_taxa_legal: Tabela`.

**Saída:** `pd.DataFrame`.

### `def _somar_taxa_legal_percentual(inicio: str, fim: str, tabela_taxa_legal: Tabela) -> Decimal`

Soma percentuais mensais da Taxa Legal em regime simples.

**Entrada:** `inicio: str`, `fim: str`, `tabela_taxa_legal: Tabela`.

**Saída:** `Decimal`.

### `def soma_taxa_legal(*, valor_base: Decimal, data_inicio: date, competencia_atualizacao: str, tabela_taxa_legal: Tabela, competencia_final_taxa_legal: str | None) -> tuple[Decimal, Decimal]`

Calcula juros usando somente a Taxa Legal oficial.

**Entrada:** `valor_base: Decimal`, `data_inicio: date`, `competencia_atualizacao: str`, `tabela_taxa_legal: Tabela`, `competencia_final_taxa_legal: str | None`.

**Saída:** `tuple[Decimal, Decimal]`.

### `def fator_selic_mensal(inicio: str, fim: str, tabela_selic: Tabela) -> Decimal`

Acumula a Selic mensal SGS 4390 entre duas competências.

**Entrada:** `inicio: str`, `fim: str`, `tabela_selic: Tabela`.

**Saída:** `Decimal`.

### `def fator_selic_mensal_local_sem_deducao(inicio: str, fim: str, tabela_selic: Tabela) -> Decimal`

Acumula Selic mensal no padrão observado para IGP-M no critério de referência.

**Entrada:** `inicio: str`, `fim: str`, `tabela_selic: Tabela`.

**Saída:** `Decimal`.

### `def fator_selic_diaria(data_inicio: date, data_fim: date, tabela_selic_diaria: Tabela) -> Decimal`

Acumula Selic diária SGS 11 entre duas datas, inclusive.

**Entrada:** `data_inicio: date`, `data_fim: date`, `tabela_selic_diaria: Tabela`.

**Saída:** `Decimal`.

### `def fator_ipca_deducao(inicio: str, fim: str, tabela_ipca_deducao: Tabela) -> Decimal`

Acumula a inflação mensal deduzida no modo SELIC - correção.

**Entrada:** `inicio: str`, `fim: str`, `tabela_ipca_deducao: Tabela`.

**Saída:** `Decimal`.

### `def _fator_selic_pre_lei(*, data_inicio: date, data_fim_selic: date, tabela_selic: Tabela, tabela_selic_diaria: Tabela, usar_selic_mensal_sem_deducao: bool) -> Decimal`

Escolhe a série Selic correta para o trecho pré-Lei.

**Entrada:** `data_inicio: date`, `data_fim_selic: date`, `tabela_selic: Tabela`, `tabela_selic_diaria: Tabela`, `usar_selic_mensal_sem_deducao: bool`.

**Saída:** `Decimal`.

### `def _juros_pre_lei_stj1368(*, valor_nominal: Decimal, data_inicio: date, data_fim_selic: date, fim_deducao_correcao: str, tabela_selic: Tabela, tabela_selic_diaria: Tabela, tabela_ipca_deducao: Tabela, deduzir_correcao_pre_lei: bool, usar_selic_mensal_sem_deducao: bool) -> Decimal`

Calcula o trecho pré-Lei como diferença de montantes.

**Entrada:** `valor_nominal: Decimal`, `data_inicio: date`, `data_fim_selic: date`, `fim_deducao_correcao: str`, `tabela_selic: Tabela`, `tabela_selic_diaria: Tabela`, `tabela_ipca_deducao: Tabela`, `deduzir_correcao_pre_lei: bool`, `usar_selic_mensal_sem_deducao: bool`.

**Saída:** `Decimal`.

### `def calcular_juros_stj1368_selic_menos_correcao(*, valor_nominal: Decimal, valor_corrigido: Decimal, data_inicio: date, competencia_atualizacao: str, tabela_selic: Tabela, tabela_selic_diaria: Tabela, tabela_ipca_deducao: Tabela, tabela_taxa_legal: Tabela, competencia_final_taxa_legal: str | None, deduzir_correcao_pre_lei: bool=True, aplicar_taxa_legal_pos_lei: bool=True, data_fim_selic_stj1368: date | None=None, competencia_final_taxa_legal_stj1368: str | None=None, usar_selic_mensal_sem_deducao: bool=False) -> tuple[Decimal, Decimal, Decimal]`

Replica o seletor critério de referência "Taxa Legal + STJ Tema 1368".

**Entrada:** `valor_nominal: Decimal`, `valor_corrigido: Decimal`, `data_inicio: date`, `competencia_atualizacao: str`, `tabela_selic: Tabela`, `tabela_selic_diaria: Tabela`, `tabela_ipca_deducao: Tabela`, `tabela_taxa_legal: Tabela`, `competencia_final_taxa_legal: str | None`, `deduzir_correcao_pre_lei: bool`, `aplicar_taxa_legal_pos_lei: bool`, `data_fim_selic_stj1368: date | None`, `competencia_final_taxa_legal_stj1368: str | None`, `usar_selic_mensal_sem_deducao: bool`.

**Saída:** `tuple[Decimal, Decimal, Decimal]`.

### `def _percentual_juros_fixos_legais(data_inicio: date, competencia_atualizacao: str) -> tuple[Decimal, Decimal]`

Calcula o trecho fixo histórico anterior à Taxa Legal.

**Entrada:** `data_inicio: date`, `competencia_atualizacao: str`.

**Saída:** `tuple[Decimal, Decimal]`.

### `def soma_juros_moratorios_ctn_lei_14905(*, valor_base: Decimal, data_inicio: date, competencia_atualizacao: str, tabela_taxa_legal: Tabela, competencia_final_taxa_legal: str | None) -> tuple[Decimal, Decimal, Decimal]`

Calcula a opção histórica 6%/12% a.a. + Taxa Legal.

**Entrada:** `valor_base: Decimal`, `data_inicio: date`, `competencia_atualizacao: str`, `tabela_taxa_legal: Tabela`, `competencia_final_taxa_legal: str | None`.

**Saída:** `tuple[Decimal, Decimal, Decimal]`.

### `def soma_juros_moratorios_stj1368_lei_14905(**kwargs: Any) -> tuple[Decimal, Decimal, Decimal]`

Atalho para o cálculo STJ 1368 com SELIC menos correção.

**Entrada:** `**kwargs: Any`.

**Saída:** `tuple[Decimal, Decimal, Decimal]`.

## `src/judicial_calc/io/__init__.py`

Entradas e saídas do motor, como geração de Excel e memória PDF.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/io/excel.py`

Exportação do resultado do cálculo para planilha Excel auditável.

### `def _safe_df(value: Any) -> pd.DataFrame`

Converte listas/dicts/escalares para DataFrame sem quebrar exportação.

**Entrada:** `value: Any`.

**Saída:** `pd.DataFrame`.

### `def _write_if_not_empty(writer: pd.ExcelWriter, sheet_name: str, value: Any) -> None`

Escreve uma aba somente quando há conteúdo.

**Entrada:** `writer: pd.ExcelWriter`, `sheet_name: str`, `value: Any`.

**Saída:** `None`.

### `def salvar_resultado_excel(resultado: ResultadoCalculo, caminho: str | Path) -> None`

Salva a memória, resumo e trilha rastreável do cálculo em Excel.

**Entrada:** `resultado: ResultadoCalculo`, `caminho: str | Path`.

**Saída:** `None`.

## `src/judicial_calc/io/pdf.py`

Geração da memória de cálculo em PDF.

### `def _resumo_dict(resultado: ResultadoCalculo) -> dict[str, Any]`

Converte o DataFrame de resumo em dicionário campo -> valor.

**Entrada:** `resultado: ResultadoCalculo`.

**Saída:** `dict[str, Any]`.

### `def _as_decimal(value: Any, default: str='0') -> Decimal`

Converte números do motor para Decimal sem arredondamento binário.

**Entrada:** `value: Any`, `default: str`.

**Saída:** `Decimal`.

### `def _format_decimal_br(value: Any) -> str`

Formata número com separadores brasileiros e duas casas decimais.

**Entrada:** `value: Any`.

**Saída:** `str`.

### `def _format_currency_br(value: Any) -> str`

Formata valor monetário em reais.

**Entrada:** `value: Any`.

**Saída:** `str`.

### `def _format_percent(value: Any) -> str`

Formata percentual sem zeros decimais desnecessários.

**Entrada:** `value: Any`.

**Saída:** `str`.

### `def _format_date_br(value: Any) -> str`

Formata datas em DD/MM/AAAA.

**Entrada:** `value: Any`.

**Saída:** `str`.

### `def _month_label(month: Any) -> str`

Normaliza mês textual/numeral para apresentação.

**Entrada:** `month: Any`.

**Saída:** `str`.

### `def _competencia_label(parametros: dict[str, Any]) -> str`

Retorna a competência final de uma natureza de dano.

**Entrada:** `parametros: dict[str, Any]`.

**Saída:** `str`.

### `def _indice_label(indice: Any) -> str`

Converte chave interna de índice para rótulo legível.

**Entrada:** `indice: Any`.

**Saída:** `str`.

### `def _juros_label(parametros: dict[str, Any]) -> str`

Descreve o critério de juros moratórios de uma natureza de dano.

**Entrada:** `parametros: dict[str, Any]`.

**Saída:** `str`.

### `def _scoped_parameters(parametros: dict[str, Any], damage: str) -> dict[str, Any]`

Obtém os critérios próprios do dano e usa os campos gerais quando necessário.

**Entrada:** `parametros: dict[str, Any]`, `damage: str`.

**Saída:** `dict[str, Any]`.

### `def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph`

Cria parágrafo escapando conteúdo vindo dos documentos.

**Entrada:** `text: Any`, `style: ParagraphStyle`.

**Saída:** `Paragraph`.

### `def _build_styles() -> dict[str, ParagraphStyle]`

Cria estilos tipográficos reutilizados por todo o documento.

**Entrada:** nenhuma entrada explícita.

**Saída:** `dict[str, ParagraphStyle]`.

### `def _identity_text(parametros: dict[str, Any]) -> str`

Monta linha de identificação sem exigir metadados inexistentes.

**Entrada:** `parametros: dict[str, Any]`.

**Saída:** `str`.

### `def _calculation_identity_table(parametros: dict[str, Any], styles: dict[str, ParagraphStyle], available_width: float, *, identificador_calculo: str | None, versao_calculo: int | None) -> Table`

Exibe a identidade de negócio e a versão sem misturá-las às fórmulas.

**Entrada:** `parametros: dict[str, Any]`, `styles: dict[str, ParagraphStyle]`, `available_width: float`, `identificador_calculo: str | None`, `versao_calculo: int | None`.

**Saída:** `Table`.

### `def _metric_cell(label: str, value: str, styles: dict[str, ParagraphStyle], width: float, *, highlight: bool=False) -> Table`

Cria card pequeno para uma métrica do resumo executivo.

**Entrada:** `label: str`, `value: str`, `styles: dict[str, ParagraphStyle]`, `width: float`, `highlight: bool`.

**Saída:** `Table`.

### `def _build_executive_summary(resultado: ResultadoCalculo, styles: dict[str, ParagraphStyle], available_width: float) -> list[Any]`

Monta o resumo inicial com os principais números do cálculo.

**Entrada:** `resultado: ResultadoCalculo`, `styles: dict[str, ParagraphStyle]`, `available_width: float`.

**Saída:** `list[Any]`.

### `def _damage_card(damage: str, memory: pd.DataFrame, parametros: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> Table`

Cria card de critérios e valores para uma natureza do dano.

**Entrada:** `damage: str`, `memory: pd.DataFrame`, `parametros: dict[str, Any]`, `styles: dict[str, ParagraphStyle]`, `width: float`.

**Saída:** `Table`.

### `def _build_damage_summary(resultado: ResultadoCalculo, styles: dict[str, ParagraphStyle], available_width: float) -> list[Any]`

Mostra critérios independentes de material e moral quando presentes.

**Entrada:** `resultado: ResultadoCalculo`, `styles: dict[str, ParagraphStyle]`, `available_width: float`.

**Saída:** `list[Any]`.

### `def _table_columns(_memory: pd.DataFrame, _parametros: dict[str, Any]) -> list[tuple[str, str, str, int]]`

Retorna sempre as sete colunas oficiais da memória de cálculo.

**Entrada:** `_memory: pd.DataFrame`, `_parametros: dict[str, Any]`.

**Saída:** `list[tuple[str, str, str, int]]`.

### `def _col_widths(columns: list[tuple[str, str, str, int]], available_width: float) -> list[float]`

Distribui a largura preservando espaço maior para a descrição.

**Entrada:** `columns: list[tuple[str, str, str, int]]`, `available_width: float`.

**Saída:** `list[float]`.

### `def _build_memory_table(memory: pd.DataFrame, parametros: dict[str, Any], styles: dict[str, ParagraphStyle], available_width: float) -> Table`

Cria a memória detalhada com as sete colunas definidas pelo produto.

**Entrada:** `memory: pd.DataFrame`, `parametros: dict[str, Any]`, `styles: dict[str, ParagraphStyle]`, `available_width: float`.

**Saída:** `Table`.

### `def _summary_rows(resumo: dict[str, Any], parametros: dict[str, Any]) -> list[tuple[str, str]]`

Monta a composição financeira final com nomenclatura simples.

**Entrada:** `resumo: dict[str, Any]`, `parametros: dict[str, Any]`.

**Saída:** `list[tuple[str, str]]`.

### `def _build_summary_table(resumo: dict[str, Any], parametros: dict[str, Any], styles: dict[str, ParagraphStyle], available_width: float) -> Table`

Cria quadro de composição do total no fim da memória detalhada.

**Entrada:** `resumo: dict[str, Any]`, `parametros: dict[str, Any]`, `styles: dict[str, ParagraphStyle]`, `available_width: float`.

**Saída:** `Table`.

### `def _draw_footer(canvas, doc) -> None`

Desenha rodapé discreto e consistente em todas as páginas.

**Entrada:** `canvas: tipo não declarado`, `doc: tipo não declarado`.

**Saída:** `None`.

### `def salvar_resultado_pdf(resultado: ResultadoCalculo, caminho: str | Path, *, identificador_calculo: str | None=None, versao_calculo: int | None=None) -> None`

Gera a memória PDF com resumo didático, identidade e versão do cálculo.

**Entrada:** `resultado: ResultadoCalculo`, `caminho: str | Path`, `identificador_calculo: str | None`, `versao_calculo: int | None`.

**Saída:** `None`.

## `src/judicial_calc/services/__init__.py`

Serviços que coordenam etapas do motor financeiro sem expor detalhes internos.

Este módulo não expõe classes ou funções de nível superior.

## `src/judicial_calc/services/calculation_adjustments.py`

Compensação aplicada ao resultado final do cálculo.

### `def _calcular_valor_compensacao(cfg: CalculoParams, total_geral_bruto: Decimal) -> Decimal`

Calcula o valor a descontar por compensação sobre o total final bruto.

**Entrada:** `cfg: CalculoParams`, `total_geral_bruto: Decimal`.

**Saída:** `Decimal`.

### `def _aplicar_compensacao_na_memoria(memoria: pd.DataFrame, valor_compensacao: Decimal) -> pd.DataFrame`

Rateia a compensação final entre parcelas para manter memória rastreável.

**Entrada:** `memoria: pd.DataFrame`, `valor_compensacao: Decimal`.

**Saída:** `pd.DataFrame`.

## `src/judicial_calc/services/calculation_parameters.py`

Normalização e validação dos parâmetros públicos do motor de cálculo.

### `def _subtrair_anos_data(data_base: date, anos: int) -> date`

Subtrai anos preservando mês/dia sempre que possível.

**Entrada:** `data_base: date`, `anos: int`.

**Saída:** `date`.

### `def _normalizar_inteiro_flexivel(valor: Any, nome: str, *, permitir_vazio: bool=False, default: int=0) -> int`

Converte entradas comuns de UI/IA para inteiro.

**Entrada:** `valor: Any`, `nome: str`, `permitir_vazio: bool`, `default: int`.

**Saída:** `int`.

### `def _normalizar_flag_binaria(valor: Any, nome: str, true_aliases: set[str], false_aliases: set[str]) -> int`

Normaliza flags 0/1 aceitando aliases textuais e numéricos flexíveis.

**Entrada:** `valor: Any`, `nome: str`, `true_aliases: set[str]`, `false_aliases: set[str]`.

**Saída:** `int`.

### `def _normalizar_flag_prescricao(valor: Any) -> int`

Normaliza a flag de prescrição para 0 ou 1.

**Entrada:** `valor: Any`.

**Saída:** `int`.

### `def _normalizar_tipo_data_referencia_prescricao(valor: Any) -> str`

Valida o tipo da data de referência usada para a prescrição.

**Entrada:** `valor: Any`.

**Saída:** `str`.

### `def _param_prescricao(params: dict[str, Any], nome: str, default: Any=None) -> Any`

Lê parâmetros de prescrição aceitando aliases de integração.

**Entrada:** `params: dict[str, Any]`, `nome: str`, `default: Any`.

**Saída:** `Any`.

### `def _resolver_prescricao(params: dict[str, Any]) -> tuple[int, int | None, str | None, date | None, date | None]`

Resolve os parâmetros de prescrição e calcula a data inicial do cálculo.

**Entrada:** `params: dict[str, Any]`.

**Saída:** `tuple[int, int | None, str | None, date | None, date | None]`.

### `def _normalizar_flag_compensacao(valor: Any) -> int`

Normaliza a flag de compensação para 0 ou 1.

**Entrada:** `valor: Any`.

**Saída:** `int`.

### `def _normalizar_tipo_compensacao(valor: Any) -> str`

Valida o tipo do cálculo da compensação.

**Entrada:** `valor: Any`.

**Saída:** `str`.

### `def _param_compensacao(params: dict[str, Any], nome: str, default: Any=None) -> Any`

Lê parâmetros de compensação aceitando aliases de integração.

**Entrada:** `params: dict[str, Any]`, `nome: str`, `default: Any`.

**Saída:** `Any`.

### `def _resolver_compensacao(params: dict[str, Any]) -> tuple[int, str, Decimal]`

Resolve os parâmetros de compensação aplicados no final do cálculo.

**Entrada:** `params: dict[str, Any]`.

**Saída:** `tuple[int, str, Decimal]`.

### `def _normalizar_flag_duplo_indice(valor: Any) -> int`

Normaliza a flag de duplo índice para 0 ou 1.

**Entrada:** `valor: Any`.

**Saída:** `int`.

### `def _param_duplo_indice(params: dict[str, Any], nome: str, default: Any=None) -> Any`

Lê parâmetros de duplo índice aceitando aliases de integração.

**Entrada:** `params: dict[str, Any]`, `nome: str`, `default: Any`.

**Saída:** `Any`.

### `def _validar_faixa_duplo_indice(prefixo: str, data_inicio: date, data_fim: date) -> None`

Valida uma faixa fechada de datas para duplo índice.

**Entrada:** `prefixo: str`, `data_inicio: date`, `data_fim: date`.

**Saída:** `None`.

### `def _resolver_valor_parcela_duplo_indice(valor_raw: Any, nome: str) -> Decimal | None`

Normaliza o valor opcional de parcela informado para uma faixa.

**Entrada:** `valor_raw: Any`, `nome: str`.

**Saída:** `Decimal | None`.

### `class FaixaDuploIndice`

Configuração de uma faixa fechada de datas corrigida por índice próprio.

**Atributos declarados:** `indice: str`, `data_inicio: date`, `data_fim: date`, `valor_parcela: Decimal | None`, `ordem: int`.

**Métodos:**

- `def contem(self, data_parcela: date) -> bool` — Retorna True quando a data da parcela está no intervalo fechado.
  - Entrada: `data_parcela: date`.
  - Saída: `bool`.

### `def _resolver_duplo_indice(params: dict[str, Any], indice_padrao: str) -> tuple[int, FaixaDuploIndice | None, FaixaDuploIndice | None]`

Resolve parâmetros de duplo índice e cria as duas faixas fechadas.

**Entrada:** `params: dict[str, Any]`, `indice_padrao: str`.

**Saída:** `tuple[int, FaixaDuploIndice | None, FaixaDuploIndice | None]`.

### `def _moeda_art_523(valor: Decimal) -> Decimal`

Arredondamento usado pelo critério de referência no bloco do art. 523.

**Entrada:** `valor: Decimal`.

**Saída:** `Decimal`.

### `def normalizar_art_523(valor: Any) -> str`

Normaliza o seletor do art. 523 do CPC para os nomes internos.

**Entrada:** `valor: Any`.

**Saída:** `str`.

### `class CalculoParams`

Parâmetros normalizados usados internamente pelo serviço.

**Atributos declarados:** `competencia_atualizacao: str`, `indice: str`, `deflacionar: bool`, `competencia_final_taxa_legal: str | None`, `tipo_juros_moratorios: str`, `data_inicio_moratorios: Any`, `incidir_multa_sobre_parcelas_a_vencer: bool`, `art_523: str`, `prescricao_flag: int`, `prescricao_anos: int | None`, `prescricao_data_referencia_tipo: str | None`, `prescricao_data_referencia: date | None`, `data_inicio_prescricao: date | None`, `compensacao_flag: int`, `compensacao_tipo_calculo: str`, `compensacao_valor: Decimal`, `duplo_indice_flag: int`, `duplo_indice_primeiro: FaixaDuploIndice | None`, `duplo_indice_segundo: FaixaDuploIndice | None`, `valor_dobrado_flag: bool`.

**Métodos:**

- `def from_raw(cls, params: dict[str, Any]) -> 'CalculoParams'` — Cria parâmetros normalizados a partir do dicionário público.
  - Entrada: `params: dict[str, Any]`.
  - Saída: `'CalculoParams'`.
- `def tipos_juros(self) -> set[str]` — Retorna os tipos de juros usados no cálculo.
  - Entrada: nenhuma entrada explícita.
  - Saída: `set[str]`.
- `def usa_stj1368(self) -> bool` — Indica se o cálculo precisa de séries do modo STJ 1368.
  - Entrada: nenhuma entrada explícita.
  - Saída: `bool`.
- `def usa_taxa_legal(self) -> bool` — Indica se a Taxa Legal mensal será necessária.
  - Entrada: nenhuma entrada explícita.
  - Saída: `bool`.
- `def stj1368_deduz_correcao(self) -> bool` — Indica se o modo STJ 1368 deduz inflação da Selic.
  - Entrada: nenhuma entrada explícita.
  - Saída: `bool`.
- `def tem_prescricao(self) -> bool` — Indica se o cálculo deve aplicar corte por prescrição.
  - Entrada: nenhuma entrada explícita.
  - Saída: `bool`.
- `def tem_compensacao(self) -> bool` — Indica se o cálculo deve descontar compensação no total final.
  - Entrada: nenhuma entrada explícita.
  - Saída: `bool`.
- `def tem_duplo_indice(self) -> bool` — Indica se a correção monetária deve variar por faixa de datas.
  - Entrada: nenhuma entrada explícita.
  - Saída: `bool`.
- `def indices_correcao_usados(self) -> set[str]` — Lista os índices de correção que podem ser usados no cálculo.
  - Entrada: nenhuma entrada explícita.
  - Saída: `set[str]`.
- `def faixa_duplo_indice_para_data(self, data_parcela: date) -> FaixaDuploIndice | None` — Retorna a faixa de duplo índice aplicável à data da parcela.
  - Entrada: `data_parcela: date`.
  - Saída: `FaixaDuploIndice | None`.

## `src/judicial_calc/services/calculation_penalties.py`

Multas, rateios monetários e art. 523 do CPC usados pelo motor.

### `class MultaLinha`

Detalhamento da multa percentual informada pelo usuário.

**Atributos declarados:** `base_manual: Decimal`, `manual: Decimal`, `total: Decimal`.


### `def _parcela_a_vencer(data_parcela, competencia_atualizacao: str) -> bool`

Indica se a parcela vence depois da competência de atualização.

**Entrada:** `data_parcela: tipo não declarado`, `competencia_atualizacao: str`.

**Saída:** `bool`.

### `def _multa_pode_incidir(data_parcela, cfg: CalculoParams) -> bool`

Aplica a opção 'incidir multa sobre parcelas a vencer'.

**Entrada:** `data_parcela: tipo não declarado`, `cfg: CalculoParams`.

**Saída:** `bool`.

### `def _base_multa_manual(*, valor_atualizado: Decimal, juros_mora: Decimal, params: dict[str, Any]) -> Decimal`

Calcula a base da multa percentual informada pelo usuário.

**Entrada:** `valor_atualizado: Decimal`, `juros_mora: Decimal`, `params: dict[str, Any]`.

**Saída:** `Decimal`.

### `def _tipo_multa(params: dict[str, Any]) -> str`

Normaliza o tipo da multa comum e aceita o campo percentual alternativo.

**Entrada:** `params: dict[str, Any]`.

**Saída:** `str`.

### `def _valor_multa(params: dict[str, Any]) -> Decimal`

Obtém o valor canônico da multa e aceita o campo percentual alternativo.

**Entrada:** `params: dict[str, Any]`.

**Saída:** `Decimal`.

### `def _calcular_multa_linha(*, data_parcela, valor_atualizado: Decimal, juros_mora: Decimal, cfg: CalculoParams, params: dict[str, Any]) -> MultaLinha`

Calcula somente a multa percentual comum de uma parcela.

**Entrada:** `data_parcela: tipo não declarado`, `valor_atualizado: Decimal`, `juros_mora: Decimal`, `cfg: CalculoParams`, `params: dict[str, Any]`.

**Saída:** `MultaLinha`.

### `def _rateio_monetario(total: Decimal, pesos: list[Decimal]) -> list[Decimal]`

Distribui um valor monetário entre linhas preservando a soma exata.

**Entrada:** `total: Decimal`, `pesos: list[Decimal]`.

**Saída:** `list[Decimal]`.

### `def _aplicar_multa_fixa_na_memoria(memoria: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame`

Rateia uma multa fixa uma única vez entre as parcelas elegíveis.

**Entrada:** `memoria: pd.DataFrame`, `params: dict[str, Any]`.

**Saída:** `pd.DataFrame`.

### `def _total_art_523(cfg: CalculoParams, base_art_523: Decimal) -> tuple[Decimal, Decimal]`

Calcula multa e honorários legais do art. 523 sobre a base final.

**Entrada:** `cfg: CalculoParams`, `base_art_523: Decimal`.

**Saída:** `tuple[Decimal, Decimal]`.

### `def _aplicar_art_523_na_memoria(*, memoria: pd.DataFrame, cfg: CalculoParams, honorarios_informados: Decimal) -> pd.DataFrame`

Inclui na memória de cálculo os campos do art. 523.

**Entrada:** `memoria: pd.DataFrame`, `cfg: CalculoParams`, `honorarios_informados: Decimal`.

**Saída:** `pd.DataFrame`.

## `src/judicial_calc/services/calculation_prescription.py`

Filtro de parcelas alcançadas pela configuração de prescrição.

### `def _aplicar_prescricao(df: pd.DataFrame, cfg: CalculoParams) -> pd.DataFrame`

Filtra as parcelas prescritas e mantém apenas valores a partir do corte.

**Entrada:** `df: pd.DataFrame`, `cfg: CalculoParams`.

**Saída:** `pd.DataFrame`.

## `src/judicial_calc/services/calculation_service.py`

Orquestração do cálculo de atualização de débitos judiciais.

### `def _parametros_por_dano(params: dict[str, Any]) -> dict[str, dict[str, Any]]`

Resolve atualização e juros independentes para material e moral.

**Entrada:** `params: dict[str, Any]`.

**Saída:** `dict[str, dict[str, Any]]`.

### `def _aplicar_prescricao_somente_material(df: pd.DataFrame, cfg: CalculoParams) -> pd.DataFrame`

Aplica o corte prescricional exclusivamente às parcelas materiais.

**Entrada:** `df: pd.DataFrame`, `cfg: CalculoParams`.

**Saída:** `pd.DataFrame`.

### `class TabelasCalculo`

Conjunto de tabelas pré-carregadas para evitar chamadas repetidas.

**Atributos declarados:** `indices: Tabela`, `taxa_legal: Tabela`, `selic: Tabela`, `selic_diaria: Tabela`, `ipca_deducao: Tabela`, `taxa_legal_diaria_selic_ipcae: Tabela`, `taxa_legal_diaria_12_6: Tabela`, `indices_por_indice: dict[str, Tabela] | None`.


### `class DamageCalculationContext`

Agrupa tudo que uma natureza de dano precisa para calcular suas parcelas.

**Atributos declarados:** `params: dict[str, Any]`, `config: CalculoParams`, `tables: TabelasCalculo`.


### `def competencia_final_correcao(indice: str, competencia_atualizacao: str) -> str`

Retorna a competência final usada pelo índice de correção.

**Entrada:** `indice: str`, `competencia_atualizacao: str`.

**Saída:** `str`.

### `def obter_fator_correcao(*, indice: str, data_parcela, competencia_atualizacao: str, tabela_indices: Tabela, deflacionar_valor_nominal: bool)`

Obtém o fator de correção monetária de uma parcela.

**Entrada:** `indice: str`, `data_parcela: tipo não declarado`, `competencia_atualizacao: str`, `tabela_indices: Tabela`, `deflacionar_valor_nominal: bool`.

**Saída:** tipo de saída não declarado.

### `def _tabela_indices_para(indice: str, tabelas: TabelasCalculo) -> Tabela`

Retorna a tabela de índices pré-carregada para uma chave específica.

**Entrada:** `indice: str`, `tabelas: TabelasCalculo`.

**Saída:** `Tabela`.

### `def _indice_correcao_linha(data_parcela: date, cfg: CalculoParams) -> tuple[str, Decimal | None, FaixaDuploIndice | None]`

Resolve o índice e eventual valor base específico de uma linha.

**Entrada:** `data_parcela: date`, `cfg: CalculoParams`.

**Saída:** `tuple[str, Decimal | None, FaixaDuploIndice | None]`.

### `def _data_inicio_com_prescricao(data_inicio: date, cfg: CalculoParams) -> date`

Aplica a data de corte prescricional ao termo inicial de juros.

**Entrada:** `data_inicio: date`, `cfg: CalculoParams`.

**Saída:** `date`.

### `def _data_inicio_juros_efetiva(params: dict[str, Any], cfg: CalculoParams, prefixo: str, data_parcela: date) -> date`

Calcula a data inicial efetivamente usada nos juros de uma linha.

**Entrada:** `params: dict[str, Any]`, `cfg: CalculoParams`, `prefixo: str`, `data_parcela: date`.

**Saída:** `date`.

### `def _datas_inicio_juros(df: pd.DataFrame, cfg: CalculoParams, tipos: set[str]) -> list`

Obtém a data inicial dos juros moratórios quando o tipo exige série externa.

**Entrada:** `df: pd.DataFrame`, `cfg: CalculoParams`, `tipos: set[str]`.

**Saída:** `list`.

### `def _precarregar_indices(df: pd.DataFrame, cfg: CalculoParams, tabelas: TabelasCalculo) -> None`

Pré-carrega somente os índices que ainda dependem de SGS.

**Entrada:** `df: pd.DataFrame`, `cfg: CalculoParams`, `tabelas: TabelasCalculo`.

**Saída:** `None`.

### `def _precarregar_taxa_legal(df: pd.DataFrame, cfg: CalculoParams, tabelas: TabelasCalculo) -> None`

Carrega a Taxa Legal mensal a partir da planilha critério de referência anexada.

**Entrada:** `df: pd.DataFrame`, `cfg: CalculoParams`, `tabelas: TabelasCalculo`.

**Saída:** `None`.

### `def _precarregar_selic(df: pd.DataFrame, cfg: CalculoParams, tabelas: TabelasCalculo) -> None`

Baixa Selic mensal ou diária para o modo STJ 1368.

**Entrada:** `df: pd.DataFrame`, `cfg: CalculoParams`, `tabelas: TabelasCalculo`.

**Saída:** `None`.

### `def _precarregar_ipca_deducao(df: pd.DataFrame, cfg: CalculoParams, tabelas: TabelasCalculo) -> None`

Baixa a série de correção deduzida no modo STJ 1368.

**Entrada:** `df: pd.DataFrame`, `cfg: CalculoParams`, `tabelas: TabelasCalculo`.

**Saída:** `None`.

### `def _precarregar_tabelas(df: pd.DataFrame, cfg: CalculoParams, params: dict[str, Any]) -> TabelasCalculo`

Centraliza a pré-carga das fontes externas.

**Entrada:** `df: pd.DataFrame`, `cfg: CalculoParams`, `params: dict[str, Any]`.

**Saída:** `TabelasCalculo`.

### `def _parametros_stj1368(cfg: CalculoParams) -> dict[str, Any]`

Monta os ajustes de transição do modo critério de referência/STJ 1368.

**Entrada:** `cfg: CalculoParams`.

**Saída:** `dict[str, Any]`.

### `def _calcular_juros_moratorios_da_linha(*, params: dict[str, Any], cfg: CalculoParams, tabelas: TabelasCalculo, valor_base: Decimal, valor_nominal: Decimal, data_parcela) -> tuple[Decimal, Decimal, Decimal]`

Calcula exclusivamente os juros moratórios de uma parcela.

**Entrada:** `params: dict[str, Any]`, `cfg: CalculoParams`, `tabelas: TabelasCalculo`, `valor_base: Decimal`, `valor_nominal: Decimal`, `data_parcela: tipo não declarado`.

**Saída:** `tuple[Decimal, Decimal, Decimal]`.

### `def _linha_memoria(row: dict[str, Any], cfg: CalculoParams, params: dict[str, Any], tabelas: TabelasCalculo) -> dict[str, Any]`

Calcula uma parcela e devolve uma linha da memória de cálculo.

**Entrada:** `row: dict[str, Any]`, `cfg: CalculoParams`, `params: dict[str, Any]`, `tabelas: TabelasCalculo`.

**Saída:** `dict[str, Any]`.

### `def _prepare_installments(parcelas: pd.DataFrame | list[dict[str, Any]]) -> pd.DataFrame`

Converte as parcelas recebidas em uma tabela interna validada.

**Entrada:** `parcelas: pd.DataFrame | list[dict[str, Any]]`.

**Saída:** `pd.DataFrame`.

### `def _build_damage_contexts(frame: pd.DataFrame, params: dict[str, Any]) -> tuple[CalculoParams, dict[str, DamageCalculationContext], DamageCalculationContext]`

Prepara parâmetros e tabelas para cada natureza de dano.

**Entrada:** `frame: pd.DataFrame`, `params: dict[str, Any]`.

**Saída:** `tuple[CalculoParams, dict[str, DamageCalculationContext], DamageCalculationContext]`.

### `def _build_memory(frame: pd.DataFrame, contexts: dict[str, DamageCalculationContext], general_context: DamageCalculationContext) -> pd.DataFrame`

Calcula cada parcela e monta a memória tabular completa.

**Entrada:** `frame: pd.DataFrame`, `contexts: dict[str, DamageCalculationContext]`, `general_context: DamageCalculationContext`.

**Saída:** `pd.DataFrame`.

### `def _apply_calculation_post_processing(memory: pd.DataFrame, params: dict[str, Any], config: CalculoParams) -> tuple[pd.DataFrame, pd.DataFrame]`

Aplica regras que dependem do conjunto completo de parcelas.

**Entrada:** `memory: pd.DataFrame`, `params: dict[str, Any]`, `config: CalculoParams`.

**Saída:** `tuple[pd.DataFrame, pd.DataFrame]`.

### `def _bool_param(valor: Any, default: bool=False) -> bool`

Normaliza parâmetros booleanos vindos de UI/JSON/ambiente.

**Entrada:** `valor: Any`, `default: bool`.

**Saída:** `bool`.

### `def _executar_atualizacao_indices_se_necessario(params: dict[str, Any]) -> dict[str, Any]`

Executa a atualização diária das planilhas antes do cálculo.

**Entrada:** `params: dict[str, Any]`.

**Saída:** `dict[str, Any]`.

### `def calcular_debitos(parcelas: pd.DataFrame | list[dict[str, Any]], **params: Any) -> ResultadoCalculo`

Calcula a atualização completa de um conjunto de parcelas.

**Entrada:** `parcelas: pd.DataFrame | list[dict[str, Any]]`, `**params: Any`.

**Saída:** `ResultadoCalculo`.

## `src/judicial_calc/services/calculation_summary.py`

Composição do resumo final e dos honorários do cálculo.

### `class HonorariosResumo`

Detalhamento dos honorários e acréscimos finais.

**Atributos declarados:** `base_manual: Decimal`, `manual: Decimal`, `base_art_523: Decimal`, `multa_art_523: Decimal`, `honorarios_art_523: Decimal`.

**Métodos:**

- `def total_honorarios(self) -> Decimal` — Honorários totais: informados + legais do art. 523.
  - Entrada: nenhuma entrada explícita.
  - Saída: `Decimal`.
- `def total_art_523(self) -> Decimal` — Acréscimo total do art. 523: multa + honorários legais.
  - Entrada: nenhuma entrada explícita.
  - Saída: `Decimal`.

### `def _calcular_honorarios_informados(*, total_atualizado: Decimal, total_mora: Decimal, total_multa: Decimal, params: dict[str, Any]) -> tuple[Decimal, Decimal]`

Calcula apenas os honorários informados pelo usuário.

**Entrada:** `total_atualizado: Decimal`, `total_mora: Decimal`, `total_multa: Decimal`, `params: dict[str, Any]`.

**Saída:** `tuple[Decimal, Decimal]`.

### `def _calcular_honorarios_resumo(*, total_atualizado: Decimal, total_mora: Decimal, total_multa: Decimal, memoria: pd.DataFrame, params: dict[str, Any]) -> HonorariosResumo`

Consolida honorários informados e acréscimos do art. 523.

**Entrada:** `total_atualizado: Decimal`, `total_mora: Decimal`, `total_multa: Decimal`, `memoria: pd.DataFrame`, `params: dict[str, Any]`.

**Saída:** `HonorariosResumo`.

### `def _total_multa_resumo(memoria: pd.DataFrame, params: dict[str, Any]) -> Decimal`

Calcula o total de multa como o critério de referência exibe na linha de totais.

**Entrada:** `memoria: pd.DataFrame`, `params: dict[str, Any]`.

**Saída:** `Decimal`.

### `def _montar_resumo(memoria: pd.DataFrame, params: dict[str, Any], cfg: CalculoParams) -> pd.DataFrame`

Agrega os totais finais no mesmo encadeamento visual do critério de referência.

**Entrada:** `memoria: pd.DataFrame`, `params: dict[str, Any]`, `cfg: CalculoParams`.

**Saída:** `pd.DataFrame`.

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

## `frontend/src/app/calculation/evidence-info.component.ts`

Exibe a origem documental e as considerações de extração sem ocupar uma aba própria.

Símbolos exportados: `EvidenceInfoComponent`.

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

Símbolos exportados: `ParameterKey`, `DamageType`, `SelectOption`, `ParamField`, `PARAM_FIELDS`, `REQUIRED_PARAMETER_KEYS`, `DAMAGE_SCOPED_PARAMETER_KEYS`, `MANUAL_DEFAULT_PARAMETERS`, `PROCESS_DEFAULT_PARAMETERS`, `monthOptions`, `interestTypeOptions`, `periodicityOptions`, `feeTypeOptions`, `prescricaoReferenceOptions`, `compensationTypeOptions`.

## `frontend/src/app/calculation/parameter-panel.component.ts`

Organiza os critérios por tipo de dano e mantém parcelas no primeiro bloco.

Símbolos exportados: `ParameterPanelComponent`.

## `frontend/src/app/calculation/pdf-viewer.component.ts`

O visualizador consome somente Blob da API, com cancelamento e descarte de URLs.

Símbolos exportados: `PdfViewerComponent`.

## `frontend/src/app/calculation/process-selector.component.ts`

A seleção é vazia no início e mantém a busca sob controle do usuário.

Símbolos exportados: `ProcessSelectorComponent`.

## `frontend/src/app/calculation/result-calculation-summary.component.ts`

Resumo operacional do cálculo exibido somente na guia Resultado.

Símbolos exportados: `ResultCalculationSummaryComponent`.

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

Símbolos exportados: `CalculationHistoryFilters`, `CalculationApiService`.

## `frontend/src/app/core/calculation-mapper.ts`

Único adaptador de formulário camelCase para os contratos snake_case.

Símbolos exportados: `CalculationOrigin`, `ParameterForm`, `DamageTypeKey`, `DamageParameterForms`, `InstallmentForm`, `WorkspaceDraft`, `blankDraft`, `draftFromCalculationVersion`, `decimalText`, `missingFields`, `toCalculationRequest`, `applyExtraction`.

## `frontend/src/app/core/config.ts`

Configuração lida antes de iniciar Angular, sem recompilar por ambiente.

Símbolos exportados: `ApiConfiguration`.

## `frontend/src/app/core/connection-api.service.ts`

Disponibilidade é consultada antes do upload, sem enviar a chave ao navegador.

Símbolos exportados: `ConnectionApiService`.

## `frontend/src/app/core/contracts.ts`

Gerado de docs/openapi.json. Atualize por scripts/generate_contracts.py.

Símbolos exportados: `AiUsage`, `AiUsageSummary`, `BatchImport`, `BatchItem`, `BatchRequest`, `BatchResponse`, `Body_import_batch_api_v2_lotes_importar_post`, `Body_import_installments_api_v2_documentos_parcelas_importar_post`, `Body_upload_api_v2_documentos_upload_post`, `CalculationComparison`, `CalculationDefaults`, `CalculationDiff`, `CalculationDraft`, `CalculationExecutionRef`, `CalculationExecutionSummary`, `CalculationExecutionsPage`, `CalculationFieldDiff`, `CalculationHistoryItem`, `CalculationHistoryPage`, `CalculationMetadata`, `CalculationParameters_Input`, `CalculationParameters_Output`, `CalculationPolicyView`, `CalculationRequest_Input`, `CalculationRequest_Output`, `CalculationResponse`, `CalculationStateChange`, `CalculationStateResult`, `CalculationVersionDetail`, `CalculationVersionRef`, `CalculationVersionSummary`, `CalculationVersionsPage`, `ChronologyDecision`, `DamageFinancialCriteria_Input`, `DamageFinancialCriteria_Output`, `DamageParameters_Input`, `DamageParameters_Output`, `DataTable`, `DatasetSnapshot`, `DocumentMetadata`, `ExtractionConfiguration`, `ExtractionRequest`, `ExtractionResult`, `ExtractionStatus`, `FeePreparation`, `FeedbackCurationInput`, `FeedbackEventRecord`, `FeedbackFieldMetric`, `FeedbackPage`, `FeedbackReasonMetric`, `FieldEvidence`, `FinOpsStageMetric`, `FinOpsSummary`, `HTTPValidationError`, `Health`, `IndexOption`, `IndexStatus`, `Installment_Input`, `Installment_Output`, `InstallmentDiff`, `OperationalAdjustment`, `ParameterCatalogItem`, `ParameterChangeInput`, `ParameterChangeRecord`, `ParameterOption`, `ProcessSummary`, `QualitySummary`, `ReviewCaptureResult`, `ReviewSnapshotInput`, `SummaryEntry`, `UploadResponse`, `ValidationError`, `VersionedCalculationResponse`, `CalculationParameters`, `CalculationRequest`, `DamageFinancialCriteria`, `DamageParameters`, `Installment`.

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

## `frontend/src/app/core/quality-api.service.ts`

Feedback supervisionado, dataset e FinOps da extração.

Símbolos exportados: `QualityApiService`.

## `frontend/src/app/core/result-presentation.ts`

Rótulos de apresentação: os valores são sempre os retornados pelo motor.

Símbolos exportados: `summaryRows`, `finalTotal`, `DamageCalculationSummary`, `damageCalculationSummaries`.

## `frontend/src/app/core/revision-audit-api.service.ts`

Trilha de revisão humana; nenhum cálculo é executado neste serviço.

Símbolos exportados: `RevisionAuditApiService`.

## `frontend/src/app/core/workspace-audit.store.ts`

Trilha de revisão humana isolada do restante da área de trabalho.

Símbolos exportados: `WorkspaceAuditStore`.

## `frontend/src/app/core/workspace-calculation.store.ts`

Revisão, cálculo e exportação ficam separados da navegação e extração.

Símbolos exportados: `WorkspaceCalculationStore`.

## `frontend/src/app/core/workspace-extraction.store.ts`

Upload, polling e aplicação de extração vivem isolados do restante da UI.

Símbolos exportados: `WorkspaceExtractionStore`.

## `frontend/src/app/core/workspace-state.store.ts`

Estado puro da área de trabalho; não executa HTTP nem regras de negócio remotas.

Símbolos exportados: `MANUAL_DRAFT_KEY`, `WorkspaceStateStore`.

## `frontend/src/app/core/workspace.store.ts`

Fachada fina da área de trabalho; estado, extração, cálculo e auditoria vivem em stores específicos.

Símbolos exportados: `WorkspaceStore`.

## `frontend/src/app/history/calculation-history-page.component.ts`

Página orquestradora do histórico; filtros, diff, comparação e execuções são componentes independentes.

Símbolos exportados: `CalculationHistoryPageComponent`.

## `frontend/src/app/history/history-diff.component.ts`

Exibe diferenças entre versões sem conhecer carregamento, paginação ou estado da página.

Símbolos exportados: `HistoryDiffComponent`.

## `frontend/src/app/history/history-executions.component.ts`

Execuções técnicas paginadas e carregadas apenas quando a versão é expandida.

Símbolos exportados: `HistoryExecutionsComponent`.

## `frontend/src/app/history/history-filters.component.ts`

Filtros do histórico isolados da paginação e da consulta HTTP.

Símbolos exportados: `HistoryFiltersComponent`.

## `frontend/src/app/history/history-version-comparator.component.ts`

Comparador isolado: carrega somente quando o usuário solicita a comparação.

Símbolos exportados: `HistoryVersionComparatorComponent`.

## `frontend/src/app/indices/indices-page.component.ts`

Estado de atualização é consultado no servidor; não há sucesso presumido.

Símbolos exportados: `IndicesPageComponent`.

## `frontend/src/app/quality/quality-page.component.ts`

Painel operacional de qualidade supervisionada e FinOps, sem expor documento bruto.

Símbolos exportados: `QualityPageComponent`.

## `frontend/src/app/shared/notifications.component.ts`

Região acessível de avisos com fechamento individual.

Símbolos exportados: `NotificationsComponent`.

## `frontend/src/app/templates/application-template-page.component.ts`

Página template reutilizável para aplicações futuras do sistema.

Símbolos exportados: `ApplicationTemplatePageComponent`.

"""Contratos oficiais: recusam campos desconhecidos e preservam decimais."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.calculation_policy import CalculationOrigin, apply_missing_defaults, parameter_keys

ProcessId = Annotated[str, Field(pattern=r"^[0-9][0-9.\-]{0,39}$")]
Money = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2, allow_inf_nan=False)]
Rate = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=8, allow_inf_nan=False)]
DamageType = Literal["dano_material", "dano_moral", "honorarios", "custas"]
EvidenceNature = Literal["pedido", "fato", "comando_decisorio", "fundamentacao", "classificacao_documental", "indeterminado"]
EvidenceEffect = Literal["informa", "mantem", "altera", "afasta", "majora", "reduz", "substitui", "nao_se_aplica"]
InterestType = Literal["sem_juros", "capitalizacao_simples", "capitalizacao_composta", "juros_moratorios_stj1368_lei_14905", "taxa_legal_12_aa_6_aa", "taxa_legal_diaria_selic_ipcae", "taxa_legal", "juros_moratorios_ctn_lei_14905"]
Periodicity = Literal["diaria", "mensal", "anual"]
Month = Literal["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
Scalar = str | int | float | bool | None


class Contract(BaseModel):
    """Base fechada para impedir erros de digitação silenciosos nos contratos."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_default=True)


class Installment(Contract):
    """Parcela informada/revisada com multiplicador explícito quando houver comando específico."""
    data: date
    valor_singelo: Money
    descricao: str = Field(default="", max_length=500)
    verba_tipo: DamageType
    # ``None`` herda a flag global; 1 força valor simples; 2 força repetição em dobro.
    multiplicador: Literal[1, 2] | None = None
    origem: Literal["informada", "honorarios_dano_moral"] = "informada"


class CalculationParameters(Contract):
    """Parâmetros normalizados que chegam ao motor de cálculo.

    Os tipos de juros são obrigatórios neste contrato interno. Quando a requisição de
    cálculo os omite, ``CalculationDraft`` injeta os padrões conforme a origem do
    cálculo antes de validar esta estrutura.
    """
    mes_atualizacao: Month
    ano_atualizacao: int = Field(ge=1900, le=2200)
    indice: str = Field(min_length=1, max_length=120)
    juros_moratorios_tipo: InterestType
    juros_compensatorios_tipo: InterestType
    deflacionar_valor_nominal: bool | None = None
    competencia_final_taxa_legal: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    juros_compensatorios_taxa: Rate | None = None
    juros_compensatorios_periodicidade: Periodicity | None = None
    juros_compensatorios_pro_rata: bool | None = None
    juros_compensatorios_data_inicio: date | None = None
    juros_moratorios_taxa: Rate | None = None
    juros_moratorios_periodicidade: Periodicity | None = None
    juros_moratorios_pro_rata: bool | None = None
    juros_moratorios_data_inicio: date | None = None
    juros_moratorios_sobre_compensatorios: bool | None = None
    incidir_multa_sobre_juros_compensatorios: bool | None = None
    incidir_multa_sobre_juros_moratorios: bool | None = None
    incidir_multa_sobre_parcelas_a_vencer: bool | None = None
    incidir_honorarios_sobre_multa: bool | None = None
    multa_percentual: Rate | None = None
    honorarios: Rate | None = None
    honorarios_tipo: Literal["percentual", "fixo"] | None = None
    art_523: Literal["nao_aplicar", "aplicar_multa", "aplicar_multa_honorarios"] | None = None
    prescricao_flag: bool | None = None
    prescricao_anos: int | None = Field(default=None, ge=0, le=100)
    prescricao_data_referencia_tipo: Literal["data_ajuizamento", "data_decisao", "data_ultima_parcela"] | None = None
    prescricao_data_referencia: date | None = None
    compensacao_flag: bool | None = None
    compensacao_tipo_calculo: Literal["percentual", "fixo"] | None = None
    compensacao_valor: Rate | None = None
    duplo_indice_flag: bool | None = None
    duplo_indice_primeiro_indice: str | None = None
    duplo_indice_primeiro_data_inicio: date | None = None
    duplo_indice_primeiro_data_fim: date | None = None
    duplo_indice_primeiro_valor_parcela: Money | None = None
    duplo_indice_segundo_indice: str | None = None
    duplo_indice_segundo_data_inicio: date | None = None
    duplo_indice_segundo_data_fim: date | None = None
    duplo_indice_segundo_valor_parcela: Money | None = None
    valor_dobrado_flag: bool | None = None

    @model_validator(mode="after")
    def require_active_fields(self) -> CalculationParameters:
        """Valida completude; a decisão sobre aplicação de regras fica no motor."""
        for prefix in ("juros_compensatorios", "juros_moratorios"):
            if getattr(self, prefix + "_tipo") in {"capitalizacao_simples", "capitalizacao_composta"}:
                if getattr(self, prefix + "_taxa") is None or getattr(self, prefix + "_periodicidade") is None:
                    raise ValueError(f"Informe taxa e periodicidade para {prefix}.")
        required = []
        if self.prescricao_flag:
            required += ["prescricao_anos", "prescricao_data_referencia_tipo"]
            if self.prescricao_data_referencia_tipo != "data_ultima_parcela":
                required += ["prescricao_data_referencia"]
        if self.compensacao_flag:
            required += ["compensacao_tipo_calculo", "compensacao_valor"]
        if self.duplo_indice_flag:
            required += [f"duplo_indice_{part}_{field}" for part in ("primeiro", "segundo") for field in ("indice", "data_inicio", "data_fim")]
        missing = [field for field in required if getattr(self, field) is None or getattr(self, field) == ""]
        if missing:
            raise ValueError("Complete os parâmetros habilitados: " + ", ".join(missing))
        return self


class CalculationDraft(Contract):
    """Entrada completa de um cálculo antes da confirmação humana definitiva.

    ``origem_calculo`` torna explícita a diferença entre um teste manual e um
    cálculo associado a documentos reais. O modo manual não usa número de processo;
    a origem ``processo`` exige um identificador válido. Os padrões são obtidos do
    catálogo central em ``config/calculation_policy.json`` e somente preenchem campos
    ausentes.
    """
    origem_calculo: CalculationOrigin
    numero_processo: ProcessId | None = None
    parcelas: list[Installment] = Field(min_length=1, max_length=10000)
    parametros: CalculationParameters
    revisao_humana_confirmada: bool = False
    honorarios_sobre_danos_morais: bool = False
    competencia_automatica: bool = False

    @model_validator(mode="before")
    @classmethod
    def apply_origin_defaults(cls, raw: object) -> object:
        """Aplica os padrões da origem antes de validar ``CalculationParameters``."""
        if not isinstance(raw, dict):
            return raw
        prepared = dict(raw)
        origin = str(prepared.get("origem_calculo") or "")
        if origin not in {"manual", "processo"}:
            return prepared
        prepared["parametros"] = apply_missing_defaults(dict(prepared.get("parametros") or {}), origin)  # type: ignore[arg-type]
        return prepared

    @model_validator(mode="after")
    def validate_origin_identity(self) -> "CalculationDraft":
        """Impede que o modo manual seja confundido com um processo documental."""
        if self.origem_calculo == "manual" and self.numero_processo is not None:
            raise ValueError("Cálculo manual não deve informar numero_processo.")
        if self.origem_calculo == "processo" and self.numero_processo is None:
            raise ValueError("numero_processo é obrigatório para cálculos de processo.")
        return self


class CalculationRequest(CalculationDraft):
    """Execução e exportação exigem confirmação humana explícita."""
    revisao_humana_confirmada: Literal[True]


class DataTable(Contract):
    """Tabela de saída: colunas variam conforme recursos ativados no motor."""
    colunas: list[str]
    linhas: list[list[Scalar]]


class SummaryEntry(Contract):
    """Campo e valor tal como retornados pelo resumo do motor."""
    campo: str
    valor: str


class CalculationMetadata(Contract):
    """Identifica de forma reproduzível a entrada, política, motor e séries usadas."""
    entrada_sha256: str
    politica_sha256: str
    motor_sha256: str
    indices_sha256: str
    duracao_ms: float
    revisao_humana_confirmada: bool


class CalculationResponse(Contract):
    """Saída oficial que o Angular apresenta sem recalcular valores."""
    origem_calculo: CalculationOrigin
    numero_processo: str | None
    memoria: DataTable
    resumo: list[SummaryEntry]
    parametros: CalculationParameters
    metadata: CalculationMetadata


class DocumentMetadata(Contract):
    """Metadados públicos do arquivo, sem expor caminhos de servidor."""
    identificador: str
    numero_processo: str
    nome: str
    sha256: str
    tamanho_bytes: int
    paginas: int
    classificacao: str


class ProcessSummary(Contract):
    """Processo e contagem obtidos dos documentos persistidos."""
    numero_processo: str
    quantidade_documentos: int




class AiUsage(Contract):
    """Telemetria técnica de uma chamada corporativa, sem conteúdo documental."""
    etapa: str
    modelo: str
    tokens_entrada: int | None = Field(default=None, ge=0)
    tokens_entrada_cache: int | None = Field(default=None, ge=0)
    tokens_saida: int | None = Field(default=None, ge=0)
    tokens_total: int | None = Field(default=None, ge=0)
    custo_estimado_usd: Decimal | None = Field(default=None, ge=0, decimal_places=6)
    duracao_ms: float = Field(ge=0)
    paginas_contexto: int | None = Field(default=None, ge=0)
    caracteres_entrada: int | None = Field(default=None, ge=0)
    correcao_estrutural: bool = False


class AiUsageSummary(Contract):
    """Resumo de chamadas; tokens/custo ficam nulos quando o serviço não os informa."""
    chamadas: int = Field(ge=0)
    tokens_entrada: int | None = Field(default=None, ge=0)
    tokens_entrada_cache: int | None = Field(default=None, ge=0)
    tokens_saida: int | None = Field(default=None, ge=0)
    tokens_total: int | None = Field(default=None, ge=0)
    custo_estimado_usd: Decimal | None = Field(default=None, ge=0, decimal_places=6)
    duracao_total_ms: float = Field(default=0, ge=0)
    detalhamento: list[AiUsage] = Field(default_factory=list)

class ExtractionRequest(Contract):
    """Identifica exclusivamente o processo cuja extração será iniciada."""
    numero_processo: ProcessId


class ExtractionStatus(Contract):
    """Estado de negócio persistido para acompanhamento e recuperação."""
    numero_processo: str
    identificador: str
    estado: Literal["aguardando", "executando", "pronto", "falha", "bloqueada", "interrompida"]
    etapa: str
    mensagem: str
    atualizado_em: str
    codigo_erro: str | None = None
    uso_ia: AiUsageSummary | None = None


class ExtractionConfiguration(Contract):
    """Presença da configuração corporativa sem expor segredos ou testar credenciais."""
    provedor: Literal["bradesco_iagen"] = "bradesco_iagen"
    configurada: bool
    modelo: str
    mensagem: str
    leitura_documental: str
    tokens_disponiveis: bool = False
    custo_disponivel: bool = False


class UploadResponse(Contract):
    """Documentos recebidos e seus trabalhos de extração associados."""
    documentos: list[DocumentMetadata]
    extracoes: list[ExtractionStatus]


class FieldEvidence(Contract):
    """Trecho rastreável enriquecido com papel processual e efeito cronológico."""
    campo: str
    valor: Scalar
    documento: str
    pagina: int = Field(ge=1)
    trecho: str
    escopo: Literal["caso_concreto", "jurisprudencia_citada", "indeterminado"]
    natureza: EvidenceNature = "indeterminado"
    efeito: EvidenceEffect = "informa"


class OperationalAdjustment(Contract):
    """Regra configurada pelo operador; não é citação de documento."""
    campo: str
    valor: Scalar
    motivo: str


class CalculationDefaults(Contract):
    """Competência do relógio do backend, em horário de Brasília."""
    mes: Month
    ano: int


class FeePreparation(Contract):
    """Recalcula somente a composição nominal autorizada, antes da revisão."""
    parcelas: list[Installment] = Field(max_length=10000)
    percentual: Rate


class ChronologyDecision(Contract):
    """Resultado explicável da consolidação temporal de um parâmetro."""
    campo: str
    valor: Scalar
    documento: str
    pagina: int
    sequencia: int
    natureza: EvidenceNature
    efeito: EvidenceEffect
    motivo: str


class ExtractionResult(Contract):
    """Sugestões rastreáveis que ainda exigem conferência humana."""
    numero_processo: str
    campos: list[FieldEvidence]
    parcelas: list[Installment]
    alertas: list[str]
    versao_prompts: str
    parametros_consolidados: dict[str, Scalar] = Field(default_factory=dict)
    decisoes_cronologicas: list[ChronologyDecision] = Field(default_factory=list)
    ajustes_operacionais: list[OperationalAdjustment] = Field(default_factory=list)
    honorarios_sobre_danos_morais: bool = False
    competencia_automatica: bool = False
    uso_ia: AiUsageSummary | None = None


class ParameterOption(Contract):
    """Opção de seleção exibida no frontend a partir do catálogo central."""
    value: Scalar
    label: str
    hidden: bool = False


class ParameterCatalogItem(Contract):
    """Metadados oficiais de apresentação e uso de um parâmetro."""
    key: str
    label: str
    type: Literal["text", "number", "date", "select", "checkbox"]
    section: str
    options: list[ParameterOption] | None = None
    help: str | None = None
    damageTypes: list[DamageType] | None = None


class CalculationPolicyView(Contract):
    """Padrões e catálogo fornecidos pelo backend para uma origem de cálculo."""
    origem_calculo: CalculationOrigin
    parametros_padrao: dict[str, Scalar]
    campos_obrigatorios: list[str]
    catalogo: list[ParameterCatalogItem]


class ParameterChangeInput(Contract):
    """Alteração de parâmetro enviada pela interface para trilha imutável de revisão."""
    origem_calculo: CalculationOrigin
    numero_processo: ProcessId | None = None
    rascunho_id: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    campo: str
    valor_anterior: Scalar = None
    valor_novo: Scalar = None
    extracao_id: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def validate_change(self) -> "ParameterChangeInput":
        """Restringe eventos às chaves do catálogo e à identidade da origem."""
        if self.campo not in parameter_keys():
            raise ValueError("campo não pertence ao catálogo de parâmetros.")
        if self.origem_calculo == "manual" and self.numero_processo is not None:
            raise ValueError("Revisão manual não deve informar numero_processo.")
        if self.origem_calculo == "processo" and self.numero_processo is None:
            raise ValueError("numero_processo é obrigatório para revisão de processo.")
        return self


class ParameterChangeRecord(ParameterChangeInput):
    """Evento persistido com carimbo de tempo e origem documental resolvida no servidor."""
    identificador: int
    registrado_em: str
    ator_tecnico: str
    valor_extraido: Scalar = None
    origem_extraida: str | None = None


class IndexOption(Contract):
    """Chave registrada no motor e rótulo de apresentação."""
    chave: str
    nome: str


class IndexStatus(Contract):
    """Estado observado da atualização e hashes dos arquivos existentes."""
    estado: Literal["nao_verificado", "atualizado", "falha", "executando"]
    mensagem: str
    atualizado_em: str | None = None
    arquivos_sha256: dict[str, str]


class BatchRequest(Contract):
    """Lote limitado de requisições integralmente validadas."""
    processos: list[CalculationRequest] = Field(min_length=1, max_length=100)


class BatchItem(Contract):
    """Sucesso ou falha identificável por processo, sem descarte silencioso."""
    numero_processo: str | None
    resultado: CalculationResponse | None = None
    erro: str | None = None


class BatchResponse(Contract):
    """Resultados de cada processo do lote, incluindo falhas."""
    resultados: list[BatchItem]


class BatchImport(Contract):
    """Prévia que não representa execução ou confirmação de revisão."""
    processos: list[CalculationDraft]
    erros: list[str]

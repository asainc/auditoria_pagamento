"""Normalização e validação dos parâmetros públicos do motor de cálculo.

Este módulo concentra somente regras de entrada: flags, prescrição, compensação,
duplo índice e art. 523. As fórmulas financeiras permanecem no serviço de
cálculo, o que deixa a orquestração menor sem alterar o resultado numérico.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_DOWN
from typing import Any

from judicial_calc.core.dates import parse_data, parse_mes_ano
from judicial_calc.core.errors import CalculationValidationError
from judicial_calc.core.numbers import D
from judicial_calc.interest.daily_rates import TIPOS_JUROS_MORATORIOS_DIARIOS
from judicial_calc.interest.taxa_legal import (
    INDICES_STJ1368_SEM_DEDUCAO_CORRECAO,
    TIPOS_JUROS_MORATORIOS_CTN_LEI_14905,
    TIPOS_JUROS_MORATORIOS_STJ1368,
    TIPOS_TAXA_LEGAL_OFICIAL,
)

ART_523_NAO_APLICAR = "nao_aplicar"
ART_523_APLICAR_MULTA = "aplicar_multa"
ART_523_APLICAR_MULTA_HONORARIOS = "aplicar_multa_honorarios"
PERCENTUAL_ART_523 = Decimal("10")
ART_523_ALIASES = {
    "": ART_523_NAO_APLICAR,
    "nao_aplicar": ART_523_NAO_APLICAR,
    "não_aplicar": ART_523_NAO_APLICAR,
    "nao aplicar": ART_523_NAO_APLICAR,
    "não aplicar": ART_523_NAO_APLICAR,
    "aplicar_multa": ART_523_APLICAR_MULTA,
    "aplicar multa": ART_523_APLICAR_MULTA,
    "aplicar_multa_honorarios": ART_523_APLICAR_MULTA_HONORARIOS,
    "aplicar_multa_honorarios_10": ART_523_APLICAR_MULTA_HONORARIOS,
    "aplicar_multa_e_honorarios": ART_523_APLICAR_MULTA_HONORARIOS,
    "aplicar multa + honorarios": ART_523_APLICAR_MULTA_HONORARIOS,
    "aplicar multa + honorários": ART_523_APLICAR_MULTA_HONORARIOS,
}

TIPOS_DATA_REFERENCIA_PRESCRICAO = {"data_ajuizamento", "data_decisao", "data_ultima_parcela"}
PRESCRICAO_FLAG_ALIASES_TRUE = {"1", "true", "sim", "s", "yes", "y"}
PRESCRICAO_FLAG_ALIASES_FALSE = {"0", "false", "nao", "não", "n", "no", ""}

TIPOS_COMPENSACAO = {"percentual", "fixo"}
COMPENSACAO_FLAG_ALIASES_TRUE = {"1", "true", "sim", "s", "yes", "y"}
COMPENSACAO_FLAG_ALIASES_FALSE = {"0", "false", "nao", "não", "n", "no", ""}

DUPLO_INDICE_FLAG_ALIASES_TRUE = {"1", "true", "sim", "s", "yes", "y"}
DUPLO_INDICE_FLAG_ALIASES_FALSE = {"0", "false", "nao", "não", "n", "no", ""}


def _subtrair_anos_data(data_base: date, anos: int) -> date:
    """Subtrai anos preservando mês/dia sempre que possível.

    Em 29/02 de ano bissexto, quando o ano de destino não possui 29/02,
    retorna 28/02. Esse comportamento evita erro em prescrições calculadas a
    partir de datas de referência em anos bissextos.
    """
    try:
        return data_base.replace(year=data_base.year - anos)
    except ValueError:
        return data_base.replace(year=data_base.year - anos, day=28)


def _normalizar_inteiro_flexivel(valor: Any, nome: str, *, permitir_vazio: bool = False, default: int = 0) -> int:
    """Converte entradas comuns de UI/IA para inteiro.

    Aceita inteiros, floats inteiros, Decimals, strings como ``"1"``,
    ``"1.0"`` e ``"1,0"``. Isso evita falhas quando a interface web,
    pandas ou a extração por IA serializam flags e itens como números
    decimais, embora semanticamente sejam inteiros.
    """
    if valor is None or valor == "":
        if permitir_vazio:
            return default
        raise CalculationValidationError("invalid_integer", [nome], "O campo deve ser um número inteiro.")
    if isinstance(valor, bool):
        return 1 if valor else 0
    texto = str(valor).strip()
    try:
        decimal = D(texto.replace(",", "."))
    except Exception as exc:
        raise CalculationValidationError("invalid_integer", [nome], "O campo deve ser um número inteiro.") from exc
    if decimal != decimal.to_integral_value():
        raise CalculationValidationError("invalid_integer", [nome], "O campo deve ser um número inteiro.")
    return int(decimal)


def _normalizar_flag_binaria(valor: Any, nome: str, true_aliases: set[str], false_aliases: set[str]) -> int:
    """Normaliza flags 0/1 aceitando aliases textuais e numéricos flexíveis."""
    if isinstance(valor, bool):
        return 1 if valor else 0
    texto = str(0 if valor is None else valor).strip().lower()
    if texto in true_aliases:
        return 1
    if texto in false_aliases:
        return 0
    try:
        inteiro = _normalizar_inteiro_flexivel(texto, nome, permitir_vazio=True, default=0)
    except ValueError as exc:
        raise CalculationValidationError("invalid_binary_flag", [nome], "O campo deve ser 0 ou 1.") from exc
    if inteiro not in (0, 1):
        raise CalculationValidationError("invalid_binary_flag", [nome], "O campo deve ser 0 ou 1.")
    return inteiro


def _normalizar_flag_prescricao(valor: Any) -> int:
    """Normaliza a flag de prescrição para 0 ou 1."""
    return _normalizar_flag_binaria(valor, "prescricao_flag", PRESCRICAO_FLAG_ALIASES_TRUE, PRESCRICAO_FLAG_ALIASES_FALSE)


def _normalizar_tipo_data_referencia_prescricao(valor: Any) -> str:
    """Valida o tipo da data de referência usada para a prescrição."""
    tipo = str(valor or "").strip().lower()
    if tipo not in TIPOS_DATA_REFERENCIA_PRESCRICAO:
        aceitos = sorted(TIPOS_DATA_REFERENCIA_PRESCRICAO)
        raise CalculationValidationError("invalid_prescription_reference_type", ["prescricao_data_referencia_tipo"], "Tipo de data de referência da prescrição inválido.")
    return tipo


def _param_prescricao(params: dict[str, Any], nome: str, default: Any = None) -> Any:
    """Lê parâmetros de prescrição aceitando aliases de integração."""
    aliases = {
        "prescricao_flag": ("prescricao_flag", "tem_prescricao", "prescricao"),
        "prescricao_anos": ("prescricao_anos", "anos_prescricao"),
        "prescricao_data_referencia_tipo": ("prescricao_data_referencia_tipo", "tipo_data_referencia_prescricao"),
        "prescricao_data_referencia": ("prescricao_data_referencia", "data_referencia_prescricao"),
    }[nome]
    for alias in aliases:
        if alias in params:
            return params.get(alias)
    return default


def _resolver_prescricao(params: dict[str, Any]) -> tuple[int, int | None, str | None, date | None, date | None]:
    """Resolve os parâmetros de prescrição e calcula a data inicial do cálculo.

    Retorna ``(flag, anos, tipo_data_referencia, data_referencia, data_inicio)``.
    Quando ``flag`` é 0, os demais valores podem ser ``None`` e o cálculo segue
    o comportamento padrão sem prescrição.
    """
    flag = _normalizar_flag_prescricao(_param_prescricao(params, "prescricao_flag", 0))
    if not flag:
        return 0, None, None, None, None

    anos_raw = _param_prescricao(params, "prescricao_anos")
    if anos_raw in (None, ""):
        raise CalculationValidationError("missing_prescription_years", ["prescricao_anos"], "Informe os anos de prescrição.")
    try:
        anos = _normalizar_inteiro_flexivel(anos_raw, "prescricao_anos")
    except (TypeError, ValueError) as exc:
        raise CalculationValidationError("invalid_prescription_years", ["prescricao_anos"], "Os anos de prescrição devem ser um inteiro positivo.") from exc
    if anos <= 0:
        raise CalculationValidationError("invalid_prescription_years", ["prescricao_anos"], "Os anos de prescrição devem ser maiores que zero.")

    tipo = _normalizar_tipo_data_referencia_prescricao(_param_prescricao(params, "prescricao_data_referencia_tipo"))
    data_ref_raw = _param_prescricao(params, "prescricao_data_referencia")
    if data_ref_raw in (None, ""):
        raise CalculationValidationError("missing_prescription_reference_date", ["prescricao_data_referencia"], "Informe a data de referência da prescrição.")
    data_ref = parse_data(data_ref_raw)
    data_inicio = _subtrair_anos_data(data_ref, anos)
    return flag, anos, tipo, data_ref, data_inicio


def _normalizar_flag_compensacao(valor: Any) -> int:
    """Normaliza a flag de compensação para 0 ou 1."""
    return _normalizar_flag_binaria(valor, "compensacao_flag", COMPENSACAO_FLAG_ALIASES_TRUE, COMPENSACAO_FLAG_ALIASES_FALSE)


def _normalizar_tipo_compensacao(valor: Any) -> str:
    """Valida o tipo do cálculo da compensação."""
    tipo = str(valor or "").strip().lower()
    if tipo not in TIPOS_COMPENSACAO:
        aceitos = sorted(TIPOS_COMPENSACAO)
        raise CalculationValidationError("invalid_compensation_type", ["compensacao_tipo_calculo"], "Tipo de compensação inválido.")
    return tipo


def _param_compensacao(params: dict[str, Any], nome: str, default: Any = None) -> Any:
    """Lê parâmetros de compensação aceitando aliases de integração."""
    aliases = {
        "compensacao_flag": ("compensacao_flag", "tem_compensacao", "compensacao"),
        "compensacao_tipo_calculo": ("compensacao_tipo_calculo", "compensacao_tipo", "tipo_compensacao"),
        "compensacao_valor": ("compensacao_valor", "valor_compensacao"),
    }[nome]
    for alias in aliases:
        if alias in params:
            return params.get(alias)
    return default


def _resolver_compensacao(params: dict[str, Any]) -> tuple[int, str, Decimal]:
    """Resolve os parâmetros de compensação aplicados no final do cálculo.

    Retorna ``(flag, tipo_calculo, valor)``. Quando ``flag`` é 0, o valor é
    zero e o tipo é preservado apenas para documentação do resultado.
    """
    flag = _normalizar_flag_compensacao(_param_compensacao(params, "compensacao_flag", 0))
    tipo = _normalizar_tipo_compensacao(_param_compensacao(params, "compensacao_tipo_calculo", "fixo"))
    valor_raw = _param_compensacao(params, "compensacao_valor", "0")

    if flag and valor_raw in (None, ""):
        raise CalculationValidationError("missing_compensation_value", ["compensacao_valor"], "Informe o valor ou percentual da compensação.")

    valor = D("0" if valor_raw in (None, "") else valor_raw)
    if valor < 0:
        raise CalculationValidationError("invalid_compensation_value", ["compensacao_valor"], "O valor da compensação deve ser maior ou igual a zero.")
    return flag, tipo, valor




def _normalizar_flag_duplo_indice(valor: Any) -> int:
    """Normaliza a flag de duplo índice para 0 ou 1."""
    return _normalizar_flag_binaria(valor, "duplo_indice_flag", DUPLO_INDICE_FLAG_ALIASES_TRUE, DUPLO_INDICE_FLAG_ALIASES_FALSE)


def _param_duplo_indice(params: dict[str, Any], nome: str, default: Any = None) -> Any:
    """Lê parâmetros de duplo índice aceitando aliases de integração."""
    aliases = {
        "duplo_indice_flag": ("duplo_indice_flag", "tem_duplo_indice", "duplo_indice"),
        "duplo_indice_primeiro_indice": ("duplo_indice_primeiro_indice", "indice_primeiro", "primeiro_indice", "indice_1"),
        "duplo_indice_primeiro_data_inicio": ("duplo_indice_primeiro_data_inicio", "primeiro_indice_data_inicio", "indice_1_data_inicio"),
        "duplo_indice_primeiro_data_fim": ("duplo_indice_primeiro_data_fim", "primeiro_indice_data_fim", "indice_1_data_fim"),
        "duplo_indice_primeiro_valor_parcela": ("duplo_indice_primeiro_valor_parcela", "primeiro_indice_valor_parcela", "indice_1_valor_parcela"),
        "duplo_indice_segundo_indice": ("duplo_indice_segundo_indice", "indice_segundo", "segundo_indice", "indice_2"),
        "duplo_indice_segundo_data_inicio": ("duplo_indice_segundo_data_inicio", "segundo_indice_data_inicio", "indice_2_data_inicio"),
        "duplo_indice_segundo_data_fim": ("duplo_indice_segundo_data_fim", "segundo_indice_data_fim", "indice_2_data_fim"),
        "duplo_indice_segundo_valor_parcela": ("duplo_indice_segundo_valor_parcela", "segundo_indice_valor_parcela", "indice_2_valor_parcela"),
    }[nome]
    for alias in aliases:
        if alias in params:
            return params.get(alias)
    return default


def _validar_faixa_duplo_indice(prefixo: str, data_inicio: date, data_fim: date) -> None:
    """Valida uma faixa fechada de datas para duplo índice."""
    if data_fim < data_inicio:
        raise CalculationValidationError(
            "invalid_dual_index_interval",
            [f"{prefixo}_data_inicio", f"{prefixo}_data_fim"],
            "A data final do intervalo não pode ser anterior à data inicial.",
        )


def _resolver_valor_parcela_duplo_indice(valor_raw: Any, nome: str) -> Decimal | None:
    """Normaliza o valor opcional de parcela informado para uma faixa."""
    if valor_raw in (None, ""):
        return None
    valor = D(valor_raw)
    if valor < 0:
        raise CalculationValidationError("negative_parameter", [nome], "O valor informado deve ser maior ou igual a zero.")
    return moeda(valor)


@dataclass(frozen=True)
class FaixaDuploIndice:
    """Configuração de uma faixa fechada de datas corrigida por índice próprio."""

    indice: str
    data_inicio: date
    data_fim: date
    valor_parcela: Decimal | None = None
    ordem: int = 1

    def contem(self, data_parcela: date) -> bool:
        """Retorna True quando a data da parcela está no intervalo fechado."""
        return self.data_inicio <= data_parcela <= self.data_fim


def _resolver_duplo_indice(params: dict[str, Any], indice_padrao: str) -> tuple[int, FaixaDuploIndice | None, FaixaDuploIndice | None]:
    """Resolve parâmetros de duplo índice e cria as duas faixas fechadas."""
    flag = _normalizar_flag_duplo_indice(_param_duplo_indice(params, "duplo_indice_flag", 0))
    if not flag:
        return 0, None, None

    primeiro_indice = str(_param_duplo_indice(params, "duplo_indice_primeiro_indice", "") or "").strip() or indice_padrao
    segundo_indice = str(_param_duplo_indice(params, "duplo_indice_segundo_indice", "") or "").strip() or indice_padrao

    obrigatorios = [
        ("duplo_indice_primeiro_data_inicio", _param_duplo_indice(params, "duplo_indice_primeiro_data_inicio")),
        ("duplo_indice_primeiro_data_fim", _param_duplo_indice(params, "duplo_indice_primeiro_data_fim")),
        ("duplo_indice_segundo_data_inicio", _param_duplo_indice(params, "duplo_indice_segundo_data_inicio")),
        ("duplo_indice_segundo_data_fim", _param_duplo_indice(params, "duplo_indice_segundo_data_fim")),
    ]
    faltantes = [nome for nome, valor in obrigatorios if valor in (None, "")]
    if faltantes:
        raise CalculationValidationError("missing_dual_index_parameters", faltantes, "Preencha todos os parâmetros obrigatórios do duplo índice.")

    primeiro_inicio = parse_data(_param_duplo_indice(params, "duplo_indice_primeiro_data_inicio"))
    primeiro_fim = parse_data(_param_duplo_indice(params, "duplo_indice_primeiro_data_fim"))
    segundo_inicio = parse_data(_param_duplo_indice(params, "duplo_indice_segundo_data_inicio"))
    segundo_fim = parse_data(_param_duplo_indice(params, "duplo_indice_segundo_data_fim"))
    _validar_faixa_duplo_indice("duplo_indice_primeiro", primeiro_inicio, primeiro_fim)
    _validar_faixa_duplo_indice("duplo_indice_segundo", segundo_inicio, segundo_fim)

    primeiro_valor = _resolver_valor_parcela_duplo_indice(
        _param_duplo_indice(params, "duplo_indice_primeiro_valor_parcela"),
        "duplo_indice_primeiro_valor_parcela",
    )
    segundo_valor = _resolver_valor_parcela_duplo_indice(
        _param_duplo_indice(params, "duplo_indice_segundo_valor_parcela"),
        "duplo_indice_segundo_valor_parcela",
    )

    primeiro = FaixaDuploIndice(primeiro_indice, primeiro_inicio, primeiro_fim, primeiro_valor, ordem=1)
    segundo = FaixaDuploIndice(segundo_indice, segundo_inicio, segundo_fim, segundo_valor, ordem=2)
    return 1, primeiro, segundo


def _moeda_art_523(valor: Decimal) -> Decimal:
    """Arredondamento usado pelo critério de referência no bloco do art. 523.

    O demonstrativo do critério de referência arredonda 17.764,175 para 17.764,17 nesse
    bloco específico, enquanto os demais valores monetários seguem o
    arredondamento comercial comum.
    """
    return D(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_DOWN)


def normalizar_art_523(valor: Any) -> str:
    """Normaliza o seletor do art. 523 do CPC para os nomes internos.

    Valores aceitos:
        * ``nao_aplicar``;
        * ``aplicar_multa``;
        * ``aplicar_multa_honorarios``.

    Alguns aliases com acento/espaço também são aceitos para facilitar a
    integração com telas ou formulários.
    """
    chave = str(valor or ART_523_NAO_APLICAR).strip().lower()
    if chave in ART_523_ALIASES:
        return ART_523_ALIASES[chave]
    aceitos = sorted({ART_523_NAO_APLICAR, ART_523_APLICAR_MULTA, ART_523_APLICAR_MULTA_HONORARIOS})
    raise CalculationValidationError("invalid_article_523", ["art_523"], "Critério do Art. 523 do CPC inválido.")


@dataclass(frozen=True)
class CalculoParams:
    """Parâmetros normalizados usados internamente pelo serviço.

    A entrada pública continua sendo ``calcular_debitos(parcelas, **params)``.
    Esta classe apenas evita espalhar ``params.get(...)`` pelo código.
    """

    competencia_atualizacao: str
    indice: str
    deflacionar: bool
    juros_mora_sobre_compensatorios: bool
    competencia_final_taxa_legal: str | None
    tipo_juros_compensatorios: str
    tipo_juros_moratorios: str
    data_inicio_compensatorios: Any
    data_inicio_moratorios: Any
    incidir_multa_sobre_parcelas_a_vencer: bool
    art_523: str
    prescricao_flag: int
    prescricao_anos: int | None
    prescricao_data_referencia_tipo: str | None
    prescricao_data_referencia: date | None
    data_inicio_prescricao: date | None
    compensacao_flag: int
    compensacao_tipo_calculo: str
    compensacao_valor: Decimal
    duplo_indice_flag: int
    duplo_indice_primeiro: FaixaDuploIndice | None
    duplo_indice_segundo: FaixaDuploIndice | None

    @classmethod
    def from_raw(cls, params: dict[str, Any]) -> "CalculoParams":
        """Cria parâmetros normalizados a partir do dicionário público.

        Entrada:
            ``params``: ``dict`` recebido por ``calcular_debitos``.

        Saída:
            ``CalculoParams`` com competência, flags e tipos de juros normalizados.
        """
        (
            prescricao_flag,
            prescricao_anos,
            prescricao_data_referencia_tipo,
            prescricao_data_referencia,
            data_inicio_prescricao,
        ) = _resolver_prescricao(params)
        compensacao_flag, compensacao_tipo_calculo, compensacao_valor = _resolver_compensacao(params)
        indice_padrao = str(params.get("indice", "sem_correcao"))
        duplo_indice_flag, duplo_indice_primeiro, duplo_indice_segundo = _resolver_duplo_indice(params, indice_padrao)

        return cls(
            competencia_atualizacao=parse_mes_ano(params["mes_atualizacao"], params["ano_atualizacao"]),
            indice=indice_padrao,
            deflacionar=bool(params.get("deflacionar_valor_nominal", False)),
            juros_mora_sobre_compensatorios=bool(params.get("juros_moratorios_sobre_compensatorios", False)),
            competencia_final_taxa_legal=params.get("competencia_final_taxa_legal"),
            tipo_juros_compensatorios=str(params.get("juros_compensatorios_tipo", "capitalizacao_simples")),
            tipo_juros_moratorios=str(params.get("juros_moratorios_tipo", "capitalizacao_simples")),
            data_inicio_compensatorios=params.get("juros_compensatorios_data_inicio"),
            data_inicio_moratorios=params.get("juros_moratorios_data_inicio"),
            incidir_multa_sobre_parcelas_a_vencer=bool(params.get("incidir_multa_sobre_parcelas_a_vencer", False)),
            art_523=normalizar_art_523(params.get("art_523", ART_523_NAO_APLICAR)),
            prescricao_flag=prescricao_flag,
            prescricao_anos=prescricao_anos,
            prescricao_data_referencia_tipo=prescricao_data_referencia_tipo,
            prescricao_data_referencia=prescricao_data_referencia,
            data_inicio_prescricao=data_inicio_prescricao,
            compensacao_flag=compensacao_flag,
            compensacao_tipo_calculo=compensacao_tipo_calculo,
            compensacao_valor=compensacao_valor,
            duplo_indice_flag=duplo_indice_flag,
            duplo_indice_primeiro=duplo_indice_primeiro,
            duplo_indice_segundo=duplo_indice_segundo,
        )

    @property
    def tipos_juros(self) -> set[str]:
        """Retorna os tipos de juros usados no cálculo.

        Entrada:
            Nenhuma; usa os atributos normalizados da instância.

        Saída:
            ``set[str]`` com tipo compensatório e moratório.
        """
        return {self.tipo_juros_compensatorios, self.tipo_juros_moratorios}

    @property
    def usa_stj1368(self) -> bool:
        """Indica se o cálculo precisa de séries do modo STJ 1368.

        Entrada:
            Nenhuma.

        Saída:
            ``bool`` usado para decidir pré-carga de Selic e dedução.
        """
        return bool((self.tipos_juros & TIPOS_JUROS_MORATORIOS_STJ1368) - TIPOS_JUROS_MORATORIOS_DIARIOS)

    @property
    def usa_taxa_legal(self) -> bool:
        """Indica se a Taxa Legal mensal será necessária.

        Entrada:
            Nenhuma.

        Saída:
            ``bool`` usado para pré-carregar a tabela mensal local/oficial.
        """
        tipos = TIPOS_TAXA_LEGAL_OFICIAL | TIPOS_JUROS_MORATORIOS_CTN_LEI_14905 | TIPOS_JUROS_MORATORIOS_STJ1368
        return bool((self.tipos_juros & tipos) - TIPOS_JUROS_MORATORIOS_DIARIOS)

    @property
    def stj1368_deduz_correcao(self) -> bool:
        """Indica se o modo STJ 1368 deduz inflação da Selic.

        Entrada:
            Nenhuma.

        Saída:
            ``bool``. Índices sem dedução configurada retornam ``False``.
        """
        return self.indice not in INDICES_STJ1368_SEM_DEDUCAO_CORRECAO

    @property
    def tem_prescricao(self) -> bool:
        """Indica se o cálculo deve aplicar corte por prescrição."""
        return self.prescricao_flag == 1 and self.data_inicio_prescricao is not None

    @property
    def tem_compensacao(self) -> bool:
        """Indica se o cálculo deve descontar compensação no total final."""
        return self.compensacao_flag == 1 and self.compensacao_valor > 0

    @property
    def tem_duplo_indice(self) -> bool:
        """Indica se a correção monetária deve variar por faixa de datas."""
        return self.duplo_indice_flag == 1 and self.duplo_indice_primeiro is not None and self.duplo_indice_segundo is not None

    @property
    def indices_correcao_usados(self) -> set[str]:
        """Lista os índices de correção que podem ser usados no cálculo."""
        if not self.tem_duplo_indice:
            return {self.indice}
        assert self.duplo_indice_primeiro is not None and self.duplo_indice_segundo is not None
        return {self.duplo_indice_primeiro.indice, self.duplo_indice_segundo.indice}

    def faixa_duplo_indice_para_data(self, data_parcela: date) -> FaixaDuploIndice | None:
        """Retorna a faixa de duplo índice aplicável à data da parcela."""
        if not self.tem_duplo_indice:
            return None
        assert self.duplo_indice_primeiro is not None and self.duplo_indice_segundo is not None
        faixas = [faixa for faixa in (self.duplo_indice_primeiro, self.duplo_indice_segundo) if faixa.contem(data_parcela)]
        if not faixas:
            raise CalculationValidationError(
                "parcel_outside_dual_index_ranges",
                [
                    "duplo_indice_primeiro_data_inicio",
                    "duplo_indice_primeiro_data_fim",
                    "duplo_indice_segundo_data_inicio",
                    "duplo_indice_segundo_data_fim",
                ],
                "Existe parcela fora dos intervalos configurados para o duplo índice.",
            )
        faixas.sort(key=lambda faixa: faixa.ordem)
        return faixas[0]



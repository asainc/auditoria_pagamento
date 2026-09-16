"""Estratégias de correção monetária baseadas na planilha mensal local."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from functools import lru_cache
from typing import Any

import pandas as pd

from judicial_calc.core.dates import competencia_data, iter_competencias, somar_meses
from judicial_calc.core.numbers import D
from judicial_calc.data_sources.local_excel import (
    RATE_DECIMAL,
    VALUE_INDEX,
    LocalIndexSpec,
    get_index_spec,
    load_index_series,
    local_index_specs,
)
from judicial_calc.indices.base import CorrectionIndexStrategy


Tabela = pd.DataFrame | list[dict[str, Any]]


def _series_map(tabela: Tabela) -> dict[str, Decimal]:
    """Normaliza uma tabela mensal em dicionário de acesso rápido.

    Entrada:
        ``tabela``: ``DataFrame`` ou ``list[dict]`` com colunas ``mes``
        (``AAAA-MM``) e ``indice`` (``Decimal``, ``int``, ``float`` ou ``str``).

    Saída:
        ``dict[str, Decimal]`` no formato ``{"2024-08": Decimal("1.234")}``.

    Exemplo:
        ``_series_map([{"mes": "2024-08", "indice": "1,10"}])`` retorna
        ``{"2024-08": Decimal("1.10")}``.
    """
    df = pd.DataFrame(tabela).copy()
    if "mes" not in df.columns or "indice" not in df.columns:
        raise ValueError("Tabela de índice local precisa ter colunas 'mes' e 'indice'.")
    df["mes"] = df["mes"].astype(str).str[:7]
    df["indice"] = df["indice"].apply(D)
    return dict(zip(df["mes"], df["indice"]))


@lru_cache(maxsize=128)
def _default_series_map(key: str) -> dict[str, Decimal]:
    """Carrega e cacheia a série mensal local de uma chave de índice.

    Entrada:
        ``key``: chave do índice, por exemplo ``"tjsp_inpc_ipca15_lei_14905"``.

    Saída:
        ``dict[str, Decimal]`` com competência e valor do índice.

    Exemplo:
        ``_default_series_map("ipca_ibge")`` retorna um mapa mensal pronto
        para acumulação sem reler a planilha em cada parcela.
    """
    return _series_map(load_index_series(key))


def _fator_por_taxa_decimal_map(mapa: dict[str, Decimal], inicio: str, fim: str) -> Decimal:
    """Acumula variações mensais em decimal usando um mapa já normalizado.

    Entrada:
        ``mapa``: ``dict`` com taxa mensal em decimal, como ``0.0062``.
        ``inicio`` e ``fim``: competências ``AAAA-MM``.

    Saída:
        ``Decimal`` multiplicativo. Ex.: duas taxas de 1% retornam ``1.0201``.
    """
    if fim < inicio:
        return Decimal("1")
    fator = Decimal("1")
    for comp in iter_competencias(inicio, fim):
        if comp not in mapa:
            raise ValueError(f"Tabela local sem taxa decimal para {comp}.")
        fator *= Decimal("1") + mapa[comp]
    return fator


def _fator_por_numero_indice_map(mapa: dict[str, Decimal], inicio: str, fim: str) -> Decimal:
    """Calcula fator por razão entre número-índice final e inicial.

    Entrada:
        ``mapa``: ``dict`` com número-índice por competência.
        ``inicio`` e ``fim``: competências ``AAAA-MM``.

    Saída:
        ``Decimal`` multiplicativo. Ex.: inicial ``100`` e final ``125``
        retornam ``1.25``.
    """
    if fim < inicio:
        return Decimal("1")
    if inicio not in mapa:
        raise ValueError(f"Tabela local sem número-índice inicial para {inicio}.")
    if fim not in mapa:
        raise ValueError(f"Tabela local sem número-índice final para {fim}.")
    inicial = mapa[inicio]
    final = mapa[fim]
    if inicial == 0:
        raise ValueError(f"Número-índice inicial zerado em {inicio}; não é possível dividir por zero.")
    return final / inicial


def fator_por_taxa_decimal(tabela: Tabela, inicio: str, fim: str) -> Decimal:
    """Acumula uma tabela mensal de taxas decimais.

    Entrada:
        ``tabela``: ``DataFrame`` ou ``list[dict]`` com ``mes`` e ``indice``;
        ``inicio`` e ``fim``: competências ``AAAA-MM``.

    Saída:
        Fator ``Decimal``. Ex.: ``indice=0.01`` em jan/2024 retorna ``1.01``.
    """
    return _fator_por_taxa_decimal_map(_series_map(tabela), inicio, fim)


def fator_por_numero_indice(tabela: Tabela, inicio: str, fim: str) -> Decimal:
    """Calcula fator de correção por número-índice mensal.

    Entrada:
        ``tabela``: ``DataFrame`` ou ``list[dict]`` com ``mes`` e ``indice``;
        ``inicio`` e ``fim``: competências ``AAAA-MM``.

    Saída:
        Fator ``Decimal``. Ex.: ``100`` para ``125`` retorna ``1.25``.
    """
    return _fator_por_numero_indice_map(_series_map(tabela), inicio, fim)


class LocalExcelCorrectionIndex(CorrectionIndexStrategy):
    """Estratégia de correção por uma coluna do arquivo ``taxas_mensais.xlsx``.

    Entrada de construção:
        ``spec``: ``LocalIndexSpec`` com chave, coluna e modo de acumulação.

    Saída dos métodos:
        ``final_competence`` retorna ``AAAA-MM``; ``factor`` retorna o fator
        ``Decimal`` de correção da parcela.
    """

    def __init__(self, spec: LocalIndexSpec) -> None:
        """Inicializa a estratégia e seus aliases públicos.

        Exemplo:
            ``LocalExcelCorrectionIndex(spec).key`` pode ser ``"ipca_ibge"``.
        """
        self.spec = spec
        self.key = spec.key
        self.aliases = spec.aliases

    def final_competence(self, competencia_atualizacao: str) -> str:
        """Retorna a competência final usada no índice.

        Entrada:
            ``competencia_atualizacao``: mês-alvo ``AAAA-MM``.

        Saída:
            ``AAAA-MM``. Taxas mensais usam o mês anterior; números-índice
            usam a própria competência de atualização.
        """
        comp = competencia_atualizacao[:7]
        if self.spec.mode == RATE_DECIMAL:
            return somar_meses(comp, -1)
        return comp

    def factor(
        self,
        *,
        data_parcela: date,
        competencia_atualizacao: str,
        tabela_indices: pd.DataFrame | list[dict[str, Any]] | None,
        deflacionar_valor_nominal: bool,
    ) -> Decimal:
        """Calcula o fator de correção monetária de uma parcela.

        Entrada:
            ``data_parcela``: ``datetime.date`` da parcela original;
            ``competencia_atualizacao``: mês-alvo ``AAAA-MM``;
            ``tabela_indices``: tabela opcional informada pelo usuário;
            ``deflacionar_valor_nominal``: quando ``False``, não deixa o
            fator ficar abaixo de ``1``.

        Saída:
            Fator ``Decimal``. Ex.: ``1.10`` transforma ``1000`` em ``1100``.
        """
        inicio = competencia_data(data_parcela)
        fim = self.final_competence(competencia_atualizacao)
        if fim < inicio:
            return Decimal("1")

        mapa = _series_map(tabela_indices) if tabela_indices is not None else _default_series_map(self.key)
        if self.spec.mode == RATE_DECIMAL:
            fator = _fator_por_taxa_decimal_map(mapa, inicio, fim)
        elif self.spec.mode == VALUE_INDEX:
            fator = _fator_por_numero_indice_map(mapa, inicio, fim)
        else:  # defensive
            raise ValueError(f"Modo de índice local inválido: {self.spec.mode}")
        return self._apply_floor(fator, deflacionar_valor_nominal)


def create_local_excel_index_strategies() -> list[LocalExcelCorrectionIndex]:
    """Cria as estratégias para todas as colunas cadastradas na planilha.

    Entrada:
        Nenhuma.

    Saída:
        ``list[LocalExcelCorrectionIndex]`` pronta para registro.
    """
    return [LocalExcelCorrectionIndex(spec) for spec in local_index_specs()]


def is_local_excel_index(key_or_label: str) -> bool:
    """Verifica se uma chave ou rótulo existe na planilha local.

    Entrada:
        ``key_or_label``: chave técnica ou nome da coluna.

    Saída:
        ``bool``. Ex.: ``is_local_excel_index("ipca_ibge")`` retorna ``True``.
    """
    try:
        get_index_spec(key_or_label)
        return True
    except ValueError:
        return False

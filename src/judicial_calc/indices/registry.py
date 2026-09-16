"""Registro central das estratégias de correção monetária."""
from __future__ import annotations

from functools import lru_cache

from judicial_calc.indices.base import CorrectionIndexStrategy, NoCorrectionIndex, ValueTableCorrectionIndex
from judicial_calc.data_sources.local_excel import local_missing_index_specs
from judicial_calc.indices.local_excel import create_local_excel_index_strategies
from judicial_calc.indices.sgs_percentage import INDICES_SGS, SGSPercentageCorrectionIndex


class IndexRegistry:
    """Mapa de chaves de índices para suas estratégias de cálculo.

    Entrada:
        Nenhuma no construtor.

    Saída:
        Objeto consultável por ``get`` e expansível por ``register``.
    """

    def __init__(self) -> None:
        """Cria um registro vazio de estratégias.

        Exemplo:
            ``registry = IndexRegistry()`` inicia ``registry.names()`` vazio.
        """
        self._items: dict[str, CorrectionIndexStrategy] = {}

    def register(self, strategy: CorrectionIndexStrategy, *aliases: str, overwrite: bool = True) -> None:
        """Registra uma estratégia por chave principal e aliases.

        Entrada:
            ``strategy``: objeto que implementa ``CorrectionIndexStrategy``;
            ``aliases``: nomes alternativos aceitos;
            ``overwrite``: permite substituir registro existente.

        Saída:
            ``None``. O registro interno é atualizado.
        """
        if overwrite or strategy.key not in self._items:
            self._items[strategy.key] = strategy
        for alias in aliases:
            if overwrite or alias not in self._items:
                self._items[alias] = strategy

    def get(self, key: str) -> CorrectionIndexStrategy | None:
        """Busca uma estratégia pelo nome do índice.

        Entrada:
            ``key``: chave, por exemplo ``"ipca_ibge"``.

        Saída:
            Estratégia correspondente ou ``None``.
        """
        return self._items.get(key)

    def names(self) -> list[str]:
        """Lista as chaves registradas em ordem alfabética.

        Entrada:
            Nenhuma.

        Saída:
            ``list[str]`` com chaves e aliases disponíveis.
        """
        return sorted(self._items)


@lru_cache(maxsize=1)
def create_default_index_registry() -> IndexRegistry:
    """Monta e cacheia o registro padrão de índices.

    Entrada:
        Nenhuma.

    Saída:
        ``IndexRegistry`` com: sem correção, índices da planilha local e
        fallback para séries SGS/Bacen que não estejam na planilha.
    """
    registry = IndexRegistry()
    registry.register(NoCorrectionIndex(), "nenhum", "0")

    for strategy in create_local_excel_index_strategies():
        registry.register(strategy, *strategy.aliases)

    for key, meta in INDICES_SGS.items():
        registry.register(SGSPercentageCorrectionIndex(key, meta["codigo"], meta["nome"]), overwrite=False)
    return registry


def resolve_index_strategy(indice: str, tabela_indices_informada: bool = False) -> CorrectionIndexStrategy:
    """Resolve a estratégia de correção monetária a partir da chave informada.

    Entrada:
        ``indice``: chave do índice, por exemplo ``"tjsp_inpc_ipca15_lei_14905"``;
        ``tabela_indices_informada``: ``True`` quando o usuário forneceu uma
        tabela customizada de ``mes``/``indice``.

    Saída:
        Instância de ``CorrectionIndexStrategy``. Se não encontrar a chave e
        houver tabela customizada, retorna ``ValueTableCorrectionIndex``.
    """
    registry = create_default_index_registry()
    strategy = registry.get(indice)
    if strategy is not None:
        return strategy
    missing = {spec.key: spec for spec in local_missing_index_specs()}
    if indice in missing:
        spec = missing[indice]
        raise ValueError(
            f"Índice '{indice}' é conhecido, porém a série histórica não está disponível nesta instalação ({spec.available_range})."
        )
    if tabela_indices_informada:
        return ValueTableCorrectionIndex(key=indice)
    nomes = registry.names() + sorted(missing)
    raise ValueError(
        f"Índice '{indice}' não reconhecido. Informe tabela_indices ou use: {', '.join(nomes)}."
    )

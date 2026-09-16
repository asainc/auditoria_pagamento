"""Consolidação determinística da evolução documental de um processo.

O LLM identifica fatos, comandos decisórios e o efeito de cada trecho. Este módulo
não interpreta Direito por conta própria: ele aplica regras estruturais e explícitas
de sucessão documental para decidir qual valor permanece efetivo em cada parâmetro.
Conflitos que não podem ser resolvidos pelas marcações extraídas permanecem abertos
para revisão humana.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from backend.models import ChronologyDecision, DocumentMetadata, FieldEvidence, Scalar


def document_sequence(name: str) -> int:
    """Obtém a sequência cronológica do padrão ``processo_sequencia*.pdf``."""
    match = re.search(r"_(\d+)(?:_[^/\\]+)?\.pdf$", name, re.IGNORECASE)
    return int(match.group(1)) if match else -1


def ordered_documents(documents: list[DocumentMetadata]) -> list[DocumentMetadata]:
    """Ordena anexos do mais antigo para o mais recente de forma determinística."""
    return sorted(documents, key=lambda document: (document_sequence(document.nome), document.nome.casefold()))


class ChronologyReducer:
    """Resolve valores efetivos sem apagar as evidências históricas que os originaram."""

    _ACTIVE_EFFECTS = {"informa", "altera", "afasta", "majora", "reduz", "substitui"}
    _DECISION_NATURE = "comando_decisorio"

    def reduce(self, evidences: Iterable[FieldEvidence]) -> tuple[dict[str, Scalar], list[ChronologyDecision], list[str]]:
        """Consolida apenas ``parametros.*`` e devolve valor, decisão e alertas.

        Regras aplicadas:
        1. evidências idênticas são consideradas concordantes;
        2. comandos decisórios têm precedência sobre pedido/fundamentação;
        3. ``mantem`` preserva o estado anterior e não cria alteração por recência;
        4. ``altera/afasta/majora/reduz/substitui`` atualizam o estado quando trazem
           valor representável pelo contrato;
        5. dois valores ativos divergentes na mesma sequência não são escolhidos;
        6. sem comando decisório, conflito entre fatos/pedidos permanece para revisão.

        O método não remove nenhuma evidência. Isso preserva a linha do tempo completa
        para auditoria e explicabilidade.
        """
        by_field: dict[str, list[FieldEvidence]] = defaultdict(list)
        for evidence in evidences:
            if evidence.campo.startswith("parametros.") and evidence.escopo == "caso_concreto":
                by_field[evidence.campo].append(evidence)

        consolidated: dict[str, Scalar] = {}
        decisions: list[ChronologyDecision] = []
        alerts: list[str] = []

        for path, items in by_field.items():
            key = path.split(".", 1)[1]
            non_null = [item for item in items if item.valor is not None]

            commands = [item for item in items if item.natureza == self._DECISION_NATURE]
            if commands:
                resolved = self._resolve_commands(path, commands)
                if resolved is None:
                    alerts.append(f"Conflito decisório em {path}: revisão humana obrigatória.")
                    continue
                value, chosen, reason = resolved
                decisions.append(self._decision(path, chosen, reason))
                if value is not None:
                    consolidated[key] = value
                else:
                    alerts.append(
                        f"O comando mais recente de {path} afastou ou não representou um valor; "
                        "o campo permanece sem preenchimento automático e exige revisão humana."
                    )
                continue

            if not non_null:
                continue
            distinct = {self._value_key(item.valor) for item in non_null}
            if len(distinct) == 1:
                chosen = max(non_null, key=self._sort_key)
                consolidated[key] = chosen.valor
                decisions.append(self._decision(path, chosen, "Evidências factuais concordantes; mantido o valor documentado."))
                continue

            # Sem comando decisório, a recência isolada não basta para transformar pedido
            # ou narrativa em critério vigente. O conflito fica visível ao operador.
            alerts.append(f"Conflito documental em {path}: não há comando decisório suficiente para escolher um valor.")

        return consolidated, decisions, alerts

    def _resolve_commands(self, path: str, commands: list[FieldEvidence]) -> tuple[Scalar, FieldEvidence, str] | None:
        """Aplica os efeitos dos comandos em ordem cronológica."""
        state: Scalar = None
        chosen: FieldEvidence | None = None
        grouped: dict[int, list[FieldEvidence]] = defaultdict(list)
        for item in commands:
            grouped[document_sequence(item.documento)].append(item)

        for sequence in sorted(grouped):
            group = sorted(grouped[sequence], key=lambda item: item.pagina)
            active_with_value = [
                item for item in group
                if item.efeito in self._ACTIVE_EFFECTS - {"afasta"} and item.valor is not None
            ]
            removals = [item for item in group if item.efeito == "afasta"]
            active_values = {self._value_key(item.valor) for item in active_with_value}
            if len(active_values) > 1 or (active_with_value and removals):
                return None

            # Um comando "mantém" sem novo valor confirma o estado anterior. Quando ele
            # repete o valor, apenas atualiza a evidência de suporte sem mudar o estado.
            maintaining = [item for item in group if item.efeito == "mantem"]
            if removals:
                # ``afasta`` limpa o estado anterior. O valor nulo permanece rastreado e
                # bloqueia a aplicação silenciosa de um default na política operacional.
                state = None
                chosen = removals[-1]
            elif active_with_value:
                candidate = active_with_value[-1]
                state = candidate.valor
                chosen = candidate
            elif maintaining:
                explicit = [item for item in maintaining if item.valor is not None]
                if explicit:
                    if state is not None and any(self._value_key(item.valor) != self._value_key(state) for item in explicit):
                        return None
                    if state is None:
                        state = explicit[-1].valor
                    chosen = explicit[-1]
                elif chosen is None:
                    # Não existe estado anterior representável; um "mantém" isolado não
                    # fornece valor suficiente para preencher o formulário.
                    chosen = maintaining[-1]

        if chosen is None:
            return None
        if chosen.efeito == "mantem":
            reason = "Comando posterior marcou manutenção do critério anterior; preservado o último valor decisório representável."
        elif chosen.efeito == "afasta":
            reason = "Comando decisório posterior afastou o critério anterior; nenhum valor substituto foi inferido."
        else:
            reason = f"Comando decisório de sequência {document_sequence(chosen.documento)} com efeito '{chosen.efeito}' definiu o valor efetivo."
        return state, chosen, reason

    @staticmethod
    def _value_key(value: Scalar) -> str:
        """Compara escalares sem depender de hash de tipos heterogêneos."""
        return repr(value)

    @staticmethod
    def _sort_key(item: FieldEvidence) -> tuple[int, int, str]:
        """Ordenação estável para escolher a evidência mais recente entre concordantes."""
        return document_sequence(item.documento), item.pagina, item.documento.casefold()

    @staticmethod
    def _decision(path: str, evidence: FieldEvidence, reason: str) -> ChronologyDecision:
        """Materializa a decisão de consolidação para auditoria e UI."""
        return ChronologyDecision(
            campo=path,
            valor=evidence.valor,
            documento=evidence.documento,
            pagina=evidence.pagina,
            sequencia=document_sequence(evidence.documento),
            natureza=evidence.natureza,
            efeito=evidence.efeito,
            motivo=reason,
        )

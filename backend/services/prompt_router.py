"""Seleção determinística de páginas para reduzir payload sem usar outro modelo."""
from __future__ import annotations

import re
from dataclasses import dataclass

from backend.services.pdf_text_extractor import PdfTextDocument, PdfTextPage


@dataclass(frozen=True)
class PromptSelection:
    """Contexto selecionado e métricas observáveis da decisão determinística."""

    documentos: tuple[PdfTextDocument, ...]
    paginas: int
    caracteres: int
    estrategia: str


class PromptPageRouter:
    """Roteia somente páginas candidatas a cada tarefa especializada."""

    KEYWORDS: dict[str, tuple[str, ...]] = {
        "00_classificacao": ("sentença", "sentenca", "acórdão", "acordao", "petição", "peticao", "decisão", "decisao", "extrato", "comprovante"),
        "01_parcelas": ("r$", "parcela", "desconto", "pagamento", "dano material", "dano moral", "devolução", "devolucao", "restituição", "restituicao", "condenar"),
        "02_correcao": ("correção", "correcao", "atualização", "atualizacao", "índice", "indice", "ipca", "inpc", "igp", "selic", "tabela de correção"),
        "03_moratorios": ("juros de mora", "juros moratórios", "juros moratorios", "citação", "citacao", "1% ao mês", "1% a.m"),
        "04_compensatorios": ("juros compensatórios", "juros compensatorios", "remuneratórios", "remuneratorios"),
        "05_encargos": ("multa", "honorários", "honorarios", "art. 523", "artigo 523", "custas", "despesas processuais"),
        "06_prescricao": ("prescri", "prazo", "cinco anos", "05 anos", "5 anos", "ajuizamento", "propositura"),
        "07_compensacao": ("compensação", "compensacao", "abatimento", "dedução", "deducao", "compensar"),
        "08_duplo_indice": ("dois índices", "dois indices", "primeiro índice", "segundo índice", "a partir de", "até", "ate", "correção"),
        "09_valor_dobrado": ("dobro", "dobrada", "em dobro", "art. 42", "repetição do indébito", "repeticao do indebito", "devolução em dobro", "devolucao em dobro"),
    }

    def __init__(self, max_pages_per_task: int = 16, fallback_pages_per_document: int = 4):
        self.max_pages_per_task = max_pages_per_task
        self.fallback_pages_per_document = fallback_pages_per_document

    @staticmethod
    def _score(text: str, keywords: tuple[str, ...]) -> int:
        normalized = re.sub(r"\s+", " ", text).casefold()
        return sum(normalized.count(keyword.casefold()) for keyword in keywords)

    @staticmethod
    def _representative(pages: tuple[PdfTextPage, ...], limit: int) -> list[PdfTextPage]:
        if len(pages) <= limit:
            return list(pages)
        head = max(1, limit // 2)
        tail = max(1, limit - head)
        candidates = [*pages[:head], *pages[-tail:]]
        seen: set[int] = set()
        result: list[PdfTextPage] = []
        for page in candidates:
            if page.numero not in seen:
                seen.add(page.numero)
                result.append(page)
        return result[:limit]

    def select(self, stage: str, documents: list[PdfTextDocument]) -> PromptSelection:
        """Seleciona páginas por palavras-chave e aplica fallback representativo."""
        keywords = self.KEYWORDS.get(stage, ())
        scored: list[tuple[int, int, str, PdfTextPage]] = []
        for document in documents:
            for page in document.paginas_utilizaveis:
                score = self._score(page.texto, keywords) if keywords else 0
                scored.append((score, page.numero, document.nome, page))

        positives = [row for row in scored if row[0] > 0]
        selected_by_name: dict[str, list[PdfTextPage]] = {}
        strategy = "palavras_chave"
        if positives:
            positives.sort(key=lambda row: (-row[0], row[2], row[1]))
            for _, _, name, page in positives[: self.max_pages_per_task]:
                selected_by_name.setdefault(name, []).append(page)
        else:
            strategy = "paginas_representativas"
            remaining = self.max_pages_per_task
            for document in documents:
                if remaining <= 0:
                    break
                candidates = self._representative(
                    document.paginas_utilizaveis,
                    min(self.fallback_pages_per_document, remaining),
                )
                if candidates:
                    selected_by_name[document.nome] = candidates
                    remaining -= len(candidates)

        selected_documents: list[PdfTextDocument] = []
        for document in documents:
            pages = selected_by_name.get(document.nome, [])
            if pages:
                selected_documents.append(
                    PdfTextDocument(nome=document.nome, paginas=tuple(sorted(pages, key=lambda page: page.numero)), alertas=())
                )
        page_count = sum(len(document.paginas) for document in selected_documents)
        chars = sum(len(page.texto) for document in selected_documents for page in document.paginas)
        return PromptSelection(tuple(selected_documents), page_count, chars, strategy)

"""Leitura local de PDFs com score explícito de qualidade da camada textual."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import pymupdf

from backend.config import Settings
from backend.errors import ServiceError


@dataclass(frozen=True)
class PdfPageQuality:
    """Métricas técnicas da camada textual; nunca contém o texto da página."""

    caracteres: int
    caracteres_imprimiveis: int
    proporcao_imprimivel: float
    proporcao_alfanumerica: float
    caracteres_substituicao: int
    score: float
    status: str


@dataclass(frozen=True)
class PdfTextPage:
    """Texto de uma página e sua qualidade observada localmente."""

    numero: int
    texto: str
    qualidade: PdfPageQuality | None = None


@dataclass(frozen=True)
class PdfTextDocument:
    """Texto paginado do PDF e alertas de qualidade da camada textual."""

    nome: str
    paginas: tuple[PdfTextPage, ...]
    alertas: tuple[str, ...] = ()

    @property
    def paginas_utilizaveis(self) -> tuple[PdfTextPage, ...]:
        """Retorna somente páginas com texto suficientemente confiável para IA."""
        return tuple(
            page for page in self.paginas
            if page.texto and (page.qualidade is None or page.qualidade.status != "inutilizavel")
        )

    @property
    def caracteres_utilizaveis(self) -> int:
        return sum(len(page.texto) for page in self.paginas_utilizaveis)

    @property
    def requer_fonte_alternativa(self) -> bool:
        return not self.paginas_utilizaveis

    def texto_prompt(self) -> str:
        """Converte páginas utilizáveis em string rastreável pelo prompt."""
        blocos = [f"## DOCUMENTO: {self.nome}"]
        for pagina in self.paginas_utilizaveis:
            blocos.append(f"### PAGINA {pagina.numero}\n{pagina.texto}")
        return "\n\n".join(blocos)


class PdfTextExtractor:
    """Extrai texto localmente e bloqueia chamadas de IA sem conteúdo minimamente útil."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _quality(text: str) -> PdfPageQuality:
        cleaned = text.replace("\x00", "").strip()
        total = len(cleaned)
        if not total:
            return PdfPageQuality(0, 0, 0.0, 0.0, 0, 0.0, "inutilizavel")
        printable = sum(1 for char in cleaned if char.isprintable() or char in "\n\t")
        alnum = sum(1 for char in cleaned if char.isalnum())
        replacements = cleaned.count("�")
        printable_ratio = printable / total
        alnum_ratio = alnum / total
        replacement_ratio = replacements / total
        # O score privilegia conteúdo legível; não tenta inferir semântica jurídica.
        length_component = min(1.0, math.log10(max(total, 1)) / 3.0)
        score = max(
            0.0,
            min(
                1.0,
                0.35 * printable_ratio
                + 0.40 * min(1.0, alnum_ratio / 0.55)
                + 0.25 * length_component
                - min(0.5, replacement_ratio * 8),
            ),
        )
        if total < 20 or printable_ratio < 0.75 or alnum_ratio < 0.12 or replacement_ratio > 0.08:
            status = "inutilizavel"
        elif total < 80 or score < 0.55:
            status = "baixa"
        else:
            status = "boa"
        return PdfPageQuality(
            caracteres=total,
            caracteres_imprimiveis=printable,
            proporcao_imprimivel=round(printable_ratio, 4),
            proporcao_alfanumerica=round(alnum_ratio, 4),
            caracteres_substituicao=replacements,
            score=round(score, 4),
            status=status,
        )

    def read(self, files: list[tuple[str, bytes, int]]) -> list[PdfTextDocument]:
        """Lê PDFs com PyMuPDF e devolve texto paginado em memória."""
        documents: list[PdfTextDocument] = []
        for name, content, expected_pages in files:
            try:
                pdf = pymupdf.open(stream=content, filetype="pdf")
            except Exception as exc:
                raise ServiceError(f"Não foi possível abrir {name} com PyMuPDF. Reenvie um PDF válido.", 400) from exc

            pages: list[PdfTextPage] = []
            warnings: list[str] = []
            try:
                for page_number, page in enumerate(pdf, start=1):
                    text = page.get_text("text", sort=True).replace("\x00", "").strip()
                    quality = self._quality(text)
                    pages.append(PdfTextPage(numero=page_number, texto=text, qualidade=quality))
                    if quality.status == "inutilizavel":
                        warnings.append(
                            f"{name}: página {page_number} sem camada textual confiável; confira visualmente o PDF."
                        )
                    elif quality.status == "baixa":
                        warnings.append(
                            f"{name}: página {page_number} com baixa qualidade textual; evidências dessa página exigem conferência reforçada."
                        )
            finally:
                pdf.close()

            if expected_pages and len(pages) != expected_pages:
                warnings.append(
                    f"{name}: PyMuPDF identificou {len(pages)} páginas, enquanto o upload registrou {expected_pages}; confira o documento."
                )
            document = PdfTextDocument(nome=name, paginas=tuple(pages), alertas=tuple(warnings))
            if document.requer_fonte_alternativa:
                warnings.append(
                    f"{name}: nenhuma página possui texto suficientemente confiável para extração automática. Use outra versão digital do documento."
                )
                document = PdfTextDocument(nome=name, paginas=tuple(pages), alertas=tuple(warnings))
            documents.append(document)
        return documents

    @staticmethod
    def assert_usable(documents: list[PdfTextDocument]) -> None:
        """Evita gastar chamadas corporativas quando nenhum PDF tem texto utilizável."""
        if not any(document.paginas_utilizaveis for document in documents):
            raise ServiceError(
                "Os PDFs não possuem camada textual confiável para extração automática com PyMuPDF. Envie uma versão digital pesquisável dos documentos.",
                422,
            )

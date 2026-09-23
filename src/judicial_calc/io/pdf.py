"""Exportação da memória de cálculo em PDF no estilo de planilha judicial.

O PDF gerado por este módulo prioriza leitura e conferência manual, com layout
compacto semelhante aos demonstrativos usados em calculadoras judiciais como o
DrCalc: cabeçalho resumido, tabela de parcelas, subtotais, honorários e total
geral. A trilha auditável detalhada continua disponível nas estruturas do
``ResultadoCalculo``, mas não é despejada em várias abas ou páginas por padrão.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from judicial_calc.core.types import ResultadoCalculo

MESES_PT = {
    "01": "janeiro",
    "02": "fevereiro",
    "03": "março",
    "04": "abril",
    "05": "maio",
    "06": "junho",
    "07": "julho",
    "08": "agosto",
    "09": "setembro",
    "10": "outubro",
    "11": "novembro",
    "12": "dezembro",
}

INDICE_LABELS_FALLBACK = {
    "sem_correcao": "Sem correção",
    "igp_m_fgv": "IGP-M - (FGV)",
    "igp_di_fgv": "IGP-DI (FGV)",
    "ipca_ibge": "IPCA (IBGE)",
    "ipca_15_ibge": "IPCA-15 (IBGE)",
    "ipca_e_ibge": "IPCA-E (IBGE)",
    "inpc_ibge": "INPC-IBGE",
    "tjsp_inpc_ipca15_lei_14905": "Tabela TJSP - INPC/IPCA-15/Lei 14.905",
}

JUROS_LABELS = {
    "capitalizacao_simples": "Capitalização simples",
    "capitalizacao_composta": "Capitalização composta",
    "juros_moratorios_stj1368_lei_14905": "Taxa Legal-art 406/Lei 14.905/24 + STJ Tema 1368 (SELIC - IPCA)",
    "taxa_legal_12_aa_6_aa": "Taxa Legal/art.406 CC: a partir de 30/08/24; antes 12% ou 6% a.a.",
    "taxa_legal_oficial": "Taxa Legal oficial",
    "taxa_legal_14905": "Taxa Legal - Lei 14.905/2024",
    "juros_moratorios_ctn_lei_14905": "CTN/Lei 14.905",
    "stj1368_selic": "STJ Tema 1368 - Selic",
    "stj1368_selic_sem_deducao": "STJ Tema 1368 - Selic sem dedução",
    "sem_juros": "Sem juros",
}


def _resumo_dict(resultado: ResultadoCalculo) -> dict[str, Any]:
    """Converte o DataFrame de resumo em dicionário campo -> valor."""
    if resultado.resumo is None or resultado.resumo.empty:
        return {}
    resumo = {}
    for _, row in resultado.resumo.iterrows():
        resumo[str(row.get("campo", ""))] = row.get("valor")
    return resumo


def _as_decimal(value: Any, default: str = "0") -> Decimal:
    """Converte valores de pandas/strings/float para Decimal de forma tolerante."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace("R$", "").replace(".", "").replace(",", ".") if isinstance(value, str) and "," in value else str(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _format_decimal_br(value: Any) -> str:
    """Formata número com separador brasileiro, sem símbolo monetário."""
    value = _as_decimal(value).quantize(Decimal("0.01"))
    sinal = "-" if value < 0 else ""
    value = abs(value)
    inteiro, frac = f"{value:.2f}".split(".")
    grupos = []
    while inteiro:
        grupos.append(inteiro[-3:])
        inteiro = inteiro[:-3]
    return f"{sinal}{'.'.join(reversed(grupos))},{frac}"


def _format_currency_br(value: Any) -> str:
    """Formata número em reais para o bloco de subtotais."""
    return f"R$ {_format_decimal_br(value)}"


def _format_percent(value: Any) -> str:
    """Formata percentual com vírgula decimal."""
    return _format_decimal_br(value).rstrip("0").rstrip(",") if _format_decimal_br(value).endswith(",00") else _format_decimal_br(value)


def _format_date_br(value: Any) -> str:
    """Formata datas em DD/MM/AAAA."""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    text = str(value)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return text


def _competencia_label(resumo: dict[str, Any], parametros: dict[str, Any]) -> str:
    """Retorna competência de atualização em português."""
    comp = resumo.get("competencia_atualizacao") or parametros.get("competencia_atualizacao")
    if comp:
        text = str(comp)
        if len(text) >= 7 and text[4] == "-":
            return f"{MESES_PT.get(text[5:7], text[5:7])} / {text[:4]}"
        return text
    mes = str(parametros.get("mes_atualizacao", "")).strip().lower()
    ano = parametros.get("ano_atualizacao", "")
    return f"{mes} / {ano}".strip(" / ")


def _indice_label(indice: Any) -> str:
    """Tenta converter a chave interna do índice para o rótulo legível."""
    key = str(indice or "sem_correcao")
    if key in INDICE_LABELS_FALLBACK:
        return INDICE_LABELS_FALLBACK[key]
    try:
        from judicial_calc.data_sources.local_excel import available_indices

        df = available_indices()
        match = df.loc[df["key"].astype(str) == key]
        if not match.empty:
            return str(match.iloc[0].get("coluna") or key)
    except Exception:
        pass
    return key


def _indice_header(resumo: dict[str, Any], parametros: dict[str, Any]) -> str:
    """Monta o rótulo do indexador, incluindo duplo índice quando houver."""
    if str(resumo.get("duplo_indice_flag") or parametros.get("duplo_indice_flag") or "0") in {"1", "True", "true"}:
        primeiro = _indice_label(resumo.get("duplo_indice_primeiro_indice") or parametros.get("duplo_indice_primeiro_indice"))
        segundo = _indice_label(resumo.get("duplo_indice_segundo_indice") or parametros.get("duplo_indice_segundo_indice"))
        return f"Duplo índice: {primeiro} / {segundo}"
    return _indice_label(resumo.get("indice") or parametros.get("indice"))


def _juros_header(parametros: dict[str, Any], prefixo: str) -> str:
    """Monta descrição de juros para o cabeçalho."""
    tipo = str(parametros.get(f"{prefixo}_tipo", "capitalizacao_simples") or "capitalizacao_simples")
    taxa = parametros.get(f"{prefixo}_taxa", "0")
    label = JUROS_LABELS.get(tipo, tipo)
    if tipo in {"capitalizacao_simples", "capitalizacao_composta"}:
        periodicidade = parametros.get(f"{prefixo}_periodicidade", "mensal")
        return f"{label} - {taxa}% {periodicidade}"
    return label


def _truthy(value: Any) -> bool:
    """Interpreta valores comuns de configuração booleana."""
    return str(value).strip().lower() in {"1", "true", "sim", "s", "yes", "y"}


def _nonzero(value: Any) -> bool:
    """Retorna True quando o valor numérico é diferente de zero."""
    return _as_decimal(value) != Decimal("0")


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    """Cria Paragraph com HTML mínimo escapado e quebra de linha controlada."""
    import html

    safe = html.escape("" if text is None else str(text)).replace("\n", "<br/>")
    return Paragraph(safe, style)


def _build_styles() -> dict[str, ParagraphStyle]:
    """Cria os estilos tipográficos e de tabela utilizados na memória PDF."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "JudicialPDFTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            textColor=colors.red,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "header": ParagraphStyle(
            "JudicialPDFHeader",
            parent=base["Normal"],
            fontName="Courier-Bold",
            fontSize=7.8,
            leading=9.2,
            alignment=TA_LEFT,
            spaceAfter=1,
        ),
        "small": ParagraphStyle(
            "JudicialPDFSmall",
            parent=base["Normal"],
            fontName="Courier",
            fontSize=6.8,
            leading=8,
            alignment=TA_LEFT,
        ),
        "small_bold": ParagraphStyle(
            "JudicialPDFSmallBold",
            parent=base["Normal"],
            fontName="Courier-Bold",
            fontSize=6.8,
            leading=8,
            alignment=TA_LEFT,
        ),
        "center_bold": ParagraphStyle(
            "JudicialPDFCenterBold",
            parent=base["Normal"],
            fontName="Courier-Bold",
            fontSize=6.8,
            leading=8,
            alignment=TA_CENTER,
        ),
        "right": ParagraphStyle(
            "JudicialPDFRight",
            parent=base["Normal"],
            fontName="Courier",
            fontSize=6.8,
            leading=8,
            alignment=TA_RIGHT,
        ),
        "right_bold": ParagraphStyle(
            "JudicialPDFRightBold",
            parent=base["Normal"],
            fontName="Courier-Bold",
            fontSize=6.8,
            leading=8,
            alignment=TA_RIGHT,
        ),
    }


def _table_columns(memoria: pd.DataFrame, parametros: dict[str, Any]) -> list[tuple[str, str, str, int]]:
    """Define colunas compactas da tabela no padrão DrCalc."""
    columns: list[tuple[str, str, str, int]] = [
        ("item", "ITEM", "center", 8),
        ("descricao", "DESCRIÇÃO", "left", 34),
        ("data", "DATA", "center", 13),
        ("valor_singelo", "VALOR\nSINGELO", "right", 14),
        ("valor_atualizado", "VALOR\nATUALIZADO", "right", 16),
    ]
    if "juros_compensatorios" in memoria.columns and _nonzero(memoria["juros_compensatorios"].sum()):
        columns.append(("juros_compensatorios", "JUROS\nCOMPENSATÓRIOS", "right", 17))
    if "juros_moratorios" in memoria.columns and (
        _nonzero(memoria["juros_moratorios"].sum()) or _nonzero(parametros.get("juros_moratorios_taxa", "0"))
    ):
        columns.append(("juros_moratorios", "JUROS MORATÓRIOS\nTAXA LEGAL", "right", 17))
    if "multa" in memoria.columns and _nonzero(memoria["multa"].sum()):
        columns.append(("multa", "MULTA", "right", 12))
    columns.append(("total", "TOTAL", "right", 16))
    return columns


def _col_widths(columns: list[tuple[str, str, str, int]], available_width: float) -> list[float]:
    """Calcula larguras de colunas adequadas à tabela principal do PDF."""
    total_units = sum(col[3] for col in columns)
    return [available_width * col[3] / total_units for col in columns]


def _build_memory_table(memoria: pd.DataFrame, parametros: dict[str, Any], styles: dict[str, ParagraphStyle], available_width: float) -> Table:
    """Cria a tabela principal da memória de cálculo."""
    columns = _table_columns(memoria, parametros)
    header = []
    for _, label, align, _ in columns:
        style = styles["center_bold"] if align == "center" else styles["small_bold"]
        if align == "right":
            style = styles["right_bold"]
        header.append(_paragraph(label, style))

    data: list[list[Any]] = [header]
    for _, row in memoria.iterrows():
        line = []
        for field, _, align, _ in columns:
            if field == "data":
                text = _format_date_br(row.get(field))
            elif field in {"valor_singelo", "valor_atualizado", "juros_compensatorios", "juros_moratorios", "multa", "total"}:
                text = _format_decimal_br(row.get(field))
            else:
                text = row.get(field, "")
            style = styles["right"] if align == "right" else styles["small"]
            if align == "center":
                style = styles["center_bold"] if field == "item" else styles["small"]
            line.append(_paragraph(text, style))
        data.append(line)

    totals = []
    for field, _, align, _ in columns:
        if field == "descricao":
            text = "TOTAIS"
            style = styles["right_bold"]
        elif field in {"valor_singelo", "valor_atualizado", "juros_compensatorios", "juros_moratorios", "multa", "total"}:
            text = _format_decimal_br(memoria[field].sum())
            style = styles["right_bold"]
        else:
            text = ""
            style = styles["small_bold"]
        totals.append(_paragraph(text, style))
    data.append(totals)

    table = Table(data, colWidths=_col_widths(columns, available_width), repeatRows=1, hAlign="LEFT")
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6E6E6")),
        ("BACKGROUND", (0, 1), (-1, -2), colors.HexColor("#F2F2F2")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E6E6E6")),
        ("FONTNAME", (0, 0), (-1, -1), "Courier"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, -1), (-1, -1), 0.3, colors.black),
    ]
    table.setStyle(TableStyle(style_cmds))
    return table


def _summary_rows(resumo: dict[str, Any], parametros: dict[str, Any]) -> list[tuple[str, str]]:
    """Monta o bloco de subtotais no rodapé da planilha."""
    rows: list[tuple[str, str]] = []
    subtotal = resumo.get("subtotal")
    if subtotal is not None:
        rows.append(("Subtotal", _format_currency_br(subtotal)))

    honorarios = resumo.get("honorarios_informados")
    if honorarios is not None and _nonzero(honorarios):
        hon_tipo = str(parametros.get("honorarios_tipo", "percentual"))
        hon_param = parametros.get("honorarios", "")
        if hon_tipo == "percentual":
            label = f"Honorários advocatícios ({_format_percent(hon_param)}%) - não aplicável s/ a multa (+)"
        else:
            label = "Honorários advocatícios - valor fixo (+)"
        rows.append((label, _format_currency_br(honorarios)))

    if _nonzero(resumo.get("multa_art_523", "0")):
        rows.append(("Multa do art. 523 do CPC (+)", _format_currency_br(resumo.get("multa_art_523"))))
    if _nonzero(resumo.get("honorarios_art_523", "0")):
        rows.append(("Honorários do art. 523 do CPC (+)", _format_currency_br(resumo.get("honorarios_art_523"))))
    if _nonzero(resumo.get("valor_compensacao", "0")):
        tipo = parametros.get("compensacao_tipo_calculo") or resumo.get("compensacao_tipo_calculo") or "fixo"
        rows.append((f"Compensação ({tipo}) (-)", _format_currency_br(resumo.get("valor_compensacao"))))
    if subtotal is not None and rows:
        interim = resumo.get("subtotal_com_honorarios") or resumo.get("total_geral_bruto")
        if interim is not None and _as_decimal(interim) != _as_decimal(subtotal):
            rows.append(("Subtotal", _format_currency_br(interim)))

    rows.append(("TOTAL GERAL", _format_currency_br(resumo.get("total_geral", "0"))))
    return rows


def _build_summary_table(resumo: dict[str, Any], parametros: dict[str, Any], styles: dict[str, ParagraphStyle], available_width: float) -> Table:
    """Cria a tabela alinhada à direita com subtotais e total geral."""
    rows = _summary_rows(resumo, parametros)
    data = []
    for label, value in rows:
        is_total = label == "TOTAL GERAL"
        data.append([
            _paragraph(label, styles["right_bold"] if is_total else styles["right"]),
            _paragraph(value, styles["right_bold"] if is_total else styles["right_bold"]),
        ])
    table_width = available_width * 0.55
    table = Table(data, colWidths=[table_width * 0.66, table_width * 0.34], hAlign="RIGHT")
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Courier"),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 0.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.8),
        ("LINEABOVE", (0, 0), (-1, 0), 0.4, colors.black),
        ("LINEABOVE", (0, -1), (-1, -1), 0.4, colors.black),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E6E6E6")),
    ]))
    return table


def _build_header_lines(resultado: ResultadoCalculo) -> list[str]:
    """Monta o cabeçalho textual do PDF."""
    resumo = _resumo_dict(resultado)
    parametros = dict(resultado.parametros or {})
    multa = parametros.get("multa_percentual", "0")
    honorarios = parametros.get("honorarios", "0")
    hon_tipo = str(parametros.get("honorarios_tipo", "percentual") or "percentual")
    hon_text = f"{_format_percent(honorarios)}%" if hon_tipo == "percentual" else _format_currency_br(honorarios)
    return [
        f"Data de atualização dos valores: {_competencia_label(resumo, parametros)}",
        f"Indexador utilizado: {_indice_header(resumo, parametros)}",
        f"Juros moratórios - {_juros_header(parametros, 'juros_moratorios')}",
        f"Acréscimo de {_format_percent(multa)}% referente a multa.",
        f"Honorários advocatícios de {hon_text} - (não aplicável sobre a multa).",
    ]


def _draw_footer(canvas, doc) -> None:
    """Desenha numeração de páginas discreta."""
    canvas.saveState()
    canvas.setFont("Helvetica", 6)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 8 * mm, f"Página {doc.page}")
    canvas.restoreState()


def _records_table(
    title: str,
    records: list[dict[str, Any]],
    styles: dict[str, ParagraphStyle],
    available_width: float,
    *,
    max_rows: int = 80,
) -> list[Any]:
    """Cria uma seção auditável em tabela simples."""
    story: list[Any] = [Spacer(1, 7), Paragraph(title, styles["small_bold"])]
    if not records:
        story.append(Paragraph("Nenhum registro.", styles["small"]))
        return story

    # Escolhe colunas curtas e estáveis para caber no PDF.
    preferred = [
        "field_path", "field", "campo", "valor", "value", "source_file", "arquivo",
        "page", "source_page", "severity", "message", "escopo", "confidence", "evidence", "trecho",
    ]
    columns = [col for col in preferred if any(col in row for row in records)]
    if not columns:
        columns = list(records[0].keys())[:6]
    columns = columns[:7]

    data: list[list[Any]] = [[_paragraph(col, styles["small_bold"]) for col in columns]]
    for row in records[:max_rows]:
        data.append([_paragraph(str(row.get(col, ""))[:500], styles["small"]) for col in columns])

    col_width = available_width / max(1, len(columns))
    table = Table(data, colWidths=[col_width] * len(columns), repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6E6E6")),
        ("GRID", (0, 0), (-1, -1), 0.15, colors.HexColor("#D0D0D0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(table)
    return story


def _flatten_evidence_map(evidence_map: Any) -> list[dict[str, Any]]:
    """Transforma evidence_map em linhas para PDF auditável."""
    rows: list[dict[str, Any]] = []
    if not isinstance(evidence_map, dict):
        return rows
    for field_path, evidences in evidence_map.items():
        if isinstance(evidences, dict):
            evidences = [evidences]
        for evidence in evidences or []:
            if isinstance(evidence, dict):
                rows.append({"field_path": field_path, **evidence})
            else:
                rows.append({"field_path": field_path, "evidence": str(evidence)})
    return rows


def salvar_resultado_pdf_auditavel(resultado: ResultadoCalculo, caminho: str | Path) -> None:
    """Salva PDF auditável com memória sintética + evidências e alertas.

    Esta versão é mais longa que a planilha judicial: inclui metadados da versão
    do cálculo, mapa de evidências, conflitos e jurisprudência ignorada.
    Use para revisão interna/auditoria, não necessariamente para
    anexar ao processo.
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    memoria = resultado.memoria.copy() if resultado.memoria is not None else pd.DataFrame()
    if memoria.empty:
        raise ValueError("Não há memória de cálculo para exportar em PDF.")

    parametros = dict(resultado.parametros or {})
    resumo = _resumo_dict(resultado)
    page_size = landscape(A4)
    left = right = 18 * mm
    doc = SimpleDocTemplate(
        str(caminho),
        pagesize=page_size,
        leftMargin=left,
        rightMargin=right,
        topMargin=13 * mm,
        bottomMargin=14 * mm,
        title="Memória de Cálculo Auditável",
        author="judicial_calc",
    )
    styles = _build_styles()
    available_width = page_size[0] - left - right
    story: list[Any] = [Paragraph("MEMÓRIA DE CÁLCULO AUDITÁVEL", styles["title"])]
    for line in _build_header_lines(resultado):
        story.append(Paragraph(line, styles["header"]))
    story.append(Spacer(1, 8))
    story.append(_build_memory_table(memoria, parametros, styles, available_width))
    story.append(Spacer(1, 5))
    story.append(_build_summary_table(resumo, parametros, styles, available_width))

    metadata = parametros.get("calculation_metadata") or parametros.get("_calculation_metadata") or {}
    if isinstance(metadata, dict) and metadata:
        story.extend(_records_table("METADADOS DA VERSÃO DO CÁLCULO", [metadata], styles, available_width, max_rows=4))

    story.append(PageBreak())
    story.append(Paragraph("TRILHA DE AUDITORIA", styles["title"]))

    story.extend(_records_table("ALERTAS E VALIDAÇÕES", parametros.get("validation_issues") or [], styles, available_width))
    story.extend(_records_table("MAPA DE EVIDÊNCIAS POR PARÂMETRO", _flatten_evidence_map(parametros.get("evidence_map")), styles, available_width))
    story.extend(_records_table("DIVERGÊNCIAS ENTRE DOCUMENTOS", parametros.get("document_conflicts") or [], styles, available_width))
    story.extend(_records_table("JURISPRUDÊNCIA IGNORADA", parametros.get("ignored_jurisprudence_audit") or [], styles, available_width))
    story.extend(_records_table("DOCUMENTOS LIDOS", parametros.get("document_roles") or [], styles, available_width))

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)


def salvar_resultado_pdf(resultado: ResultadoCalculo, caminho: str | Path) -> None:
    """Salva a memória de cálculo em PDF no padrão de planilha judicial.

    Entrada:
        ``resultado``: objeto retornado por ``calcular_debitos``;
        ``caminho``: arquivo ``.pdf`` de destino.

    Saída:
        Grava um PDF em orientação paisagem, com cabeçalho, tabela de parcelas,
        subtotais, honorários/abatimentos e total geral.
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    memoria = resultado.memoria.copy() if resultado.memoria is not None else pd.DataFrame()
    if memoria.empty:
        raise ValueError("Não há memória de cálculo para exportar em PDF.")

    parametros = dict(resultado.parametros or {})
    resumo = _resumo_dict(resultado)
    page_size = landscape(A4)
    left = right = 20 * mm
    doc = SimpleDocTemplate(
        str(caminho),
        pagesize=page_size,
        leftMargin=left,
        rightMargin=right,
        topMargin=13 * mm,
        bottomMargin=14 * mm,
        title="Planilha de Débitos Judiciais",
        author="judicial_calc",
    )
    styles = _build_styles()
    story: list[Any] = [Paragraph("PLANILHA DE DÉBITOS JUDICIAIS", styles["title"])]
    for line in _build_header_lines(resultado):
        story.append(Paragraph(line, styles["header"]))
    story.append(Spacer(1, 8))
    available_width = page_size[0] - left - right
    story.append(_build_memory_table(memoria, parametros, styles, available_width))
    story.append(Spacer(1, 5))
    story.append(_build_summary_table(resumo, parametros, styles, available_width))

    # Mantém o PDF objetivo como a referência visual. Alertas aparecem apenas
    # quando existem bloqueios ou avisos, em uma seção curta no fim.
    issues = parametros.get("validation_issues") or []
    if issues:
        story.append(Spacer(1, 8))
        story.append(Paragraph("OBSERVAÇÕES DE AUDITORIA", styles["small_bold"]))
        for issue in issues[:8]:
            msg = issue.get("message") if isinstance(issue, dict) else str(issue)
            story.append(Paragraph(f"- {msg}", styles["small"]))

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)


__all__ = ["salvar_resultado_pdf", "salvar_resultado_pdf_auditavel"]

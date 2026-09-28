"""Geração da memória de cálculo em PDF.

O documento é deliberadamente único: a aplicação gera somente a memória de
cálculo. O layout segue a identidade visual da interface e prioriza três níveis
de leitura: resultado geral, critérios aplicados por natureza do dano e memória
detalhada linha a linha.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from judicial_calc.core.types import ResultadoCalculo

# Identidade visual alinhada à aplicação Angular.
CANVAS = colors.HexColor("#F3F5F7")
PAPER = colors.HexColor("#FFFFFF")
INK = colors.HexColor("#253440")
MUTED = colors.HexColor("#61727F")
LINE = colors.HexColor("#D9E0E7")
ACCENT = colors.HexColor("#BD2142")
ACCENT_DARK = colors.HexColor("#9F1835")
ACCENT_SOFT = colors.HexColor("#F9EDF0")
SOFT = colors.HexColor("#F7F8FA")

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
    "igp_m_fgv": "IGP-M (FGV)",
    "igp_di_fgv": "IGP-DI (FGV)",
    "ipca_ibge": "IPCA (IBGE)",
    "ipca_15_ibge": "IPCA-15 (IBGE)",
    "ipca_e_ibge": "IPCA-E (IBGE)",
    "inpc_ibge": "INPC (IBGE)",
    "tjsp_inpc_ipca15_lei_14905": "Tabela TJSP - INPC/IPCA-15/Lei 14.905",
}

JUROS_LABELS = {
    "capitalizacao_simples": "Capitalização simples",
    "capitalizacao_composta": "Capitalização composta",
    "juros_moratorios_stj1368_lei_14905": "Taxa Legal - Lei 14.905/2024 e STJ Tema 1368",
    "taxa_legal_12_aa_6_aa": "Taxa Legal - art. 406 CC",
    "taxa_legal_diaria_selic_ipcae": "Taxa Legal diária (Selic - IPCA-E)",
    "taxa_legal": "Taxa Legal oficial",
    "taxa_legal_oficial": "Taxa Legal oficial",
    "taxa_legal_14905": "Taxa Legal - Lei 14.905/2024",
    "juros_moratorios_ctn_lei_14905": "CTN / Lei 14.905/2024",
    "stj1368_selic": "STJ Tema 1368 - Selic",
    "stj1368_selic_sem_deducao": "STJ Tema 1368 - Selic sem dedução",
    "sem_juros": "Sem juros moratórios",
}

DAMAGE_LABELS = {
    "dano_material": "Dano Material",
    "dano_moral": "Dano Moral",
}

# A ordem e os nomes abaixo são requisito funcional da memória de cálculo.
MEMORY_COLUMNS: list[tuple[str, str, str, int]] = [
    ("item", "Item", "center", 7),
    ("descricao", "Descrição", "left", 32),
    ("data", "Data", "center", 13),
    ("valor_singelo", "Valor Singelo", "right", 15),
    ("valor_atualizado", "Valor Atualizado", "right", 17),
    ("juros_moratorios", "Juros Moratórios", "right", 17),
    ("total", "Total", "right", 16),
]


def _resumo_dict(resultado: ResultadoCalculo) -> dict[str, Any]:
    """Converte o DataFrame de resumo em dicionário campo -> valor."""
    if resultado.resumo is None or resultado.resumo.empty:
        return {}
    return {str(row.get("campo", "")): row.get("valor") for _, row in resultado.resumo.iterrows()}


def _as_decimal(value: Any, default: str = "0") -> Decimal:
    """Converte números do motor para Decimal sem arredondamento binário."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        if isinstance(value, str) and "," in value:
            cleaned = value.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
            return Decimal(cleaned)
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _format_decimal_br(value: Any) -> str:
    """Formata número com separadores brasileiros e duas casas decimais."""
    number = _as_decimal(value).quantize(Decimal("0.01"))
    sign = "-" if number < 0 else ""
    number = abs(number)
    integer, fraction = f"{number:.2f}".split(".")
    groups: list[str] = []
    while integer:
        groups.append(integer[-3:])
        integer = integer[:-3]
    return f"{sign}{'.'.join(reversed(groups))},{fraction}"


def _format_currency_br(value: Any) -> str:
    """Formata valor monetário em reais."""
    return f"R$ {_format_decimal_br(value)}"


def _format_percent(value: Any) -> str:
    """Formata percentual sem zeros decimais desnecessários."""
    text = _format_decimal_br(value)
    return text[:-3] if text.endswith(",00") else text


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


def _month_label(month: Any) -> str:
    """Normaliza mês textual/numeral para apresentação."""
    raw = str(month or "").strip().lower()
    if raw in MESES_PT:
        return MESES_PT[raw]
    return raw


def _competencia_label(parametros: dict[str, Any]) -> str:
    """Retorna a competência final de uma natureza de dano."""
    comp = parametros.get("competencia_atualizacao")
    if comp:
        text = str(comp)
        if len(text) >= 7 and text[4] == "-":
            return f"{MESES_PT.get(text[5:7], text[5:7])}/{text[:4]}"
        return text
    month = _month_label(parametros.get("mes_atualizacao"))
    year = str(parametros.get("ano_atualizacao") or "").strip()
    return f"{month}/{year}".strip("/")


def _indice_label(indice: Any) -> str:
    """Converte chave interna de índice para rótulo legível."""
    key = str(indice or "sem_correcao")
    if key in INDICE_LABELS_FALLBACK:
        return INDICE_LABELS_FALLBACK[key]
    try:
        from judicial_calc.data_sources.local_excel import available_indices

        frame = available_indices()
        match = frame.loc[frame["key"].astype(str) == key]
        if not match.empty:
            return str(match.iloc[0].get("coluna") or key)
    except Exception:
        # O PDF não deve falhar apenas porque o catálogo de apresentação não
        # estava disponível; a chave usada no cálculo continua sendo mostrada.
        pass
    return key


def _juros_label(parametros: dict[str, Any]) -> str:
    """Descreve o critério de juros moratórios de uma natureza de dano."""
    kind = str(parametros.get("juros_moratorios_tipo") or "sem_juros")
    label = JUROS_LABELS.get(kind, kind)
    if kind in {"capitalizacao_simples", "capitalizacao_composta"}:
        rate = _format_percent(parametros.get("juros_moratorios_taxa", "0"))
        periodicity = str(parametros.get("juros_moratorios_periodicidade") or "mensal")
        return f"{label} - {rate}% {periodicity}"
    return label


def _scoped_parameters(parametros: dict[str, Any], damage: str) -> dict[str, Any]:
    """Obtém os critérios próprios do dano e usa os campos gerais quando necessário."""
    raw = parametros.get("parametros_por_dano")
    if isinstance(raw, dict) and isinstance(raw.get(damage), dict):
        return dict(raw[damage])
    return dict(parametros)


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    """Cria parágrafo escapando conteúdo vindo dos documentos."""
    import html

    safe = html.escape("" if text is None else str(text)).replace("\n", "<br/>")
    return Paragraph(safe, style)


def _build_styles() -> dict[str, ParagraphStyle]:
    """Cria estilos tipográficos reutilizados por todo o documento."""
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "MemoryEyebrow", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.2, leading=9, textColor=ACCENT, tracking=0.7,
        ),
        "title": ParagraphStyle(
            "MemoryTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=20, leading=23, textColor=INK, alignment=TA_LEFT, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "MemorySubtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, leading=11, textColor=MUTED,
        ),
        "section": ParagraphStyle(
            "MemorySection", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=10.5, leading=13, textColor=INK, spaceBefore=2, spaceAfter=5,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.2, leading=9, textColor=MUTED,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=10.5, leading=13, textColor=INK,
        ),
        "total_label": ParagraphStyle(
            "TotalLabel", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8, leading=10, textColor=ACCENT_DARK,
        ),
        "total_value": ParagraphStyle(
            "TotalValue", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=19, leading=22, textColor=ACCENT_DARK,
        ),
        "card_title": ParagraphStyle(
            "CardTitle", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=11, textColor=INK,
        ),
        "card_label": ParagraphStyle(
            "CardLabel", parent=base["Normal"], fontName="Helvetica",
            fontSize=6.8, leading=8.5, textColor=MUTED,
        ),
        "card_value": ParagraphStyle(
            "CardValue", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.5, leading=9.3, textColor=INK,
        ),
        "table_header": ParagraphStyle(
            "MemoryTableHeader", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=6.4, leading=7.5, textColor=INK, alignment=TA_CENTER,
        ),
        "table_left": ParagraphStyle(
            "MemoryTableLeft", parent=base["Normal"], fontName="Helvetica",
            fontSize=6.5, leading=8.2, textColor=INK, alignment=TA_LEFT,
        ),
        "table_center": ParagraphStyle(
            "MemoryTableCenter", parent=base["Normal"], fontName="Helvetica",
            fontSize=6.5, leading=8.2, textColor=INK, alignment=TA_CENTER,
        ),
        "table_right": ParagraphStyle(
            "MemoryTableRight", parent=base["Normal"], fontName="Helvetica",
            fontSize=6.5, leading=8.2, textColor=INK, alignment=TA_RIGHT,
        ),
        "table_bold": ParagraphStyle(
            "MemoryTableBold", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=6.6, leading=8.2, textColor=INK, alignment=TA_RIGHT,
        ),
        "summary_label": ParagraphStyle(
            "SummaryLabel", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.3, leading=9.2, textColor=MUTED, alignment=TA_RIGHT,
        ),
        "summary_value": ParagraphStyle(
            "SummaryValue", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.6, leading=9.2, textColor=INK, alignment=TA_RIGHT,
        ),
        "note": ParagraphStyle(
            "MemoryNote", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.2, leading=9.5, textColor=MUTED,
        ),
    }


def _identity_text(parametros: dict[str, Any]) -> str:
    """Monta linha de identificação sem exigir metadados inexistentes."""
    process = str(parametros.get("numero_processo") or "").strip()
    manual = str(parametros.get("identificador_calculo") or "").strip()
    if process:
        return f"Processo {process}"
    if manual:
        return f"Cálculo {manual}"
    return "Memória consolidada do cálculo"


def _calculation_identity_table(
    parametros: dict[str, Any],
    styles: dict[str, ParagraphStyle],
    available_width: float,
    *,
    identificador_calculo: str | None,
    versao_calculo: int | None,
) -> Table:
    """Exibe a identidade de negócio e a versão sem misturá-las às fórmulas."""
    identifier = str(identificador_calculo or parametros.get("identificador_calculo") or "").strip() or "Não informado"
    version = f"V{versao_calculo}" if versao_calculo is not None else "Prévia não versionada"
    gap = 4 * mm
    cell_width = (available_width - gap) / 2
    data = [[
        Table(
            [[_paragraph("Identificador do cálculo", styles["metric_label"])], [_paragraph(identifier, styles["metric_value"])]],
            colWidths=[cell_width],
        ),
        "",
        Table(
            [[_paragraph("Versão do cálculo", styles["metric_label"])], [_paragraph(version, styles["metric_value"])]],
            colWidths=[cell_width],
        ),
    ]]
    outer = Table(data, colWidths=[cell_width, gap, cell_width], hAlign="LEFT")
    outer.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    for index in (0, 2):
        inner = data[0][index]
        inner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SOFT),
            ("BOX", (0, 0), (-1, -1), 0.5, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("TOPPADDING", (0, 0), (-1, 0), 2.2 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 0.8 * mm),
            ("TOPPADDING", (0, 1), (-1, 1), 0),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 2.2 * mm),
        ]))
    return outer


def _metric_cell(label: str, value: str, styles: dict[str, ParagraphStyle], width: float, *, highlight: bool = False) -> Table:
    """Cria card pequeno para uma métrica do resumo executivo."""
    data = [[_paragraph(label, styles["metric_label"])], [_paragraph(value, styles["total_value"] if highlight else styles["metric_value"])]]
    table = Table(data, colWidths=[width], rowHeights=None)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_SOFT if highlight else PAPER),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E8CCD3") if highlight else LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, 0), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1.2 * mm),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 3.2 * mm),
    ]))
    return table


def _build_executive_summary(resultado: ResultadoCalculo, styles: dict[str, ParagraphStyle], available_width: float) -> list[Any]:
    """Monta o resumo inicial com os principais números do cálculo."""
    resumo = _resumo_dict(resultado)
    gap = 3 * mm
    card_width = (available_width - (3 * gap)) / 4
    cards = [
        _metric_cell("Total geral", _format_currency_br(resumo.get("total_geral", 0)), styles, card_width, highlight=True),
        _metric_cell("Valor singelo", _format_currency_br(resumo.get("total_singelo", 0)), styles, card_width),
        _metric_cell("Valor atualizado", _format_currency_br(resumo.get("total_atualizado", 0)), styles, card_width),
        _metric_cell("Juros moratórios", _format_currency_br(resumo.get("total_juros_moratorios", 0)), styles, card_width),
    ]
    row = Table(
        [[cards[0], "", cards[1], "", cards[2], "", cards[3]]],
        colWidths=[card_width, gap, card_width, gap, card_width, gap, card_width],
        hAlign="LEFT",
    )
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [Paragraph("Resumo do cálculo", styles["section"]), row]


def _damage_card(
    damage: str,
    memory: pd.DataFrame,
    parametros: dict[str, Any],
    styles: dict[str, ParagraphStyle],
    width: float,
) -> Table:
    """Cria card de critérios e valores para uma natureza do dano."""
    scoped = _scoped_parameters(parametros, damage)
    subset = memory[memory["verba_tipo"].astype(str) == damage] if "verba_tipo" in memory.columns else memory
    count = len(subset)
    singular = subset["valor_singelo"].sum() if "valor_singelo" in subset.columns else Decimal("0")
    updated = subset["valor_atualizado"].sum() if "valor_atualizado" in subset.columns else Decimal("0")
    interest = subset["juros_moratorios"].sum() if "juros_moratorios" in subset.columns else Decimal("0")
    rows: list[list[Any]] = [
        [_paragraph(DAMAGE_LABELS[damage], styles["card_title"]), ""],
        [_paragraph("Parcelas", styles["card_label"]), _paragraph(str(count), styles["card_value"])],
        [_paragraph("Valor singelo", styles["card_label"]), _paragraph(_format_currency_br(singular), styles["card_value"])],
        [_paragraph("Valor atualizado", styles["card_label"]), _paragraph(_format_currency_br(updated), styles["card_value"])],
        [_paragraph("Juros moratórios", styles["card_label"]), _paragraph(_format_currency_br(interest), styles["card_value"])],
        [_paragraph("Indexador", styles["card_label"]), _paragraph(_indice_label(scoped.get("indice")), styles["card_value"])],
        [_paragraph("Atualização", styles["card_label"]), _paragraph(_competencia_label(scoped), styles["card_value"])],
        [_paragraph("Critério de juros", styles["card_label"]), _paragraph(_juros_label(scoped), styles["card_value"])],
    ]
    table = Table(rows, colWidths=[width * 0.34, width * 0.66], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (1, 0), ACCENT_SOFT),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#E8CCD3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, 0), 2.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2.5 * mm),
        ("TOPPADDING", (0, 1), (-1, -1), 1.4 * mm),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 1.4 * mm),
    ]))
    return table


def _build_damage_summary(resultado: ResultadoCalculo, styles: dict[str, ParagraphStyle], available_width: float) -> list[Any]:
    """Mostra critérios independentes de material e moral quando presentes."""
    memory = resultado.memoria
    parametros = dict(resultado.parametros or {})
    present = []
    if "verba_tipo" in memory.columns:
        values = set(memory["verba_tipo"].astype(str))
        present = [damage for damage in ("dano_material", "dano_moral") if damage in values]
    if not present:
        present = ["dano_material"]
    gap = 5 * mm
    width = available_width if len(present) == 1 else (available_width - gap) / 2
    cards = [_damage_card(damage, memory, parametros, styles, width) for damage in present]
    if len(cards) == 1:
        layout = Table([[cards[0]]], colWidths=[width], hAlign="LEFT")
    else:
        layout = Table([[cards[0], "", cards[1]]], colWidths=[width, gap, width], hAlign="LEFT")
    layout.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [Paragraph("Critérios por natureza do dano", styles["section"]), layout]


def _table_columns(_memory: pd.DataFrame, _parametros: dict[str, Any]) -> list[tuple[str, str, str, int]]:
    """Retorna sempre as sete colunas oficiais da memória de cálculo."""
    return list(MEMORY_COLUMNS)


def _col_widths(columns: list[tuple[str, str, str, int]], available_width: float) -> list[float]:
    """Distribui a largura preservando espaço maior para a descrição."""
    total = sum(column[3] for column in columns)
    return [available_width * column[3] / total for column in columns]


def _build_memory_table(memory: pd.DataFrame, parametros: dict[str, Any], styles: dict[str, ParagraphStyle], available_width: float) -> Table:
    """Cria a memória detalhada com as sete colunas definidas pelo produto."""
    columns = _table_columns(memory, parametros)
    header = [_paragraph(label, styles["table_header"]) for _, label, _, _ in columns]
    data: list[list[Any]] = [header]

    for row_index, (_, row) in enumerate(memory.iterrows(), start=1):
        line: list[Any] = []
        for field, _, alignment, _ in columns:
            if field == "data":
                text = _format_date_br(row.get(field))
            elif field in {"valor_singelo", "valor_atualizado", "juros_moratorios", "total"}:
                text = _format_currency_br(row.get(field))
            else:
                text = row.get(field, "")
            style = {
                "left": styles["table_left"],
                "center": styles["table_center"],
                "right": styles["table_right"],
            }[alignment]
            line.append(_paragraph(text, style))
        data.append(line)

    totals: list[Any] = []
    for field, _, _, _ in columns:
        if field == "descricao":
            totals.append(_paragraph("TOTAIS", styles["table_bold"]))
        elif field in {"valor_singelo", "valor_atualizado", "juros_moratorios", "total"}:
            totals.append(_paragraph(_format_currency_br(memory[field].sum()), styles["table_bold"]))
        else:
            totals.append(_paragraph("", styles["table_bold"]))
    data.append(totals)

    table = Table(data, colWidths=_col_widths(columns, available_width), repeatRows=1, hAlign="LEFT")
    commands: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF1F4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.1 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.1 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.9 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.9 * mm),
        ("BACKGROUND", (0, -1), (-1, -1), ACCENT_SOFT),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor("#E8CCD3")),
    ]
    for index in range(1, len(data) - 1):
        if index % 2 == 0:
            commands.append(("BACKGROUND", (0, index), (-1, index), SOFT))
        commands.append(("LINEBELOW", (0, index), (-1, index), 0.35, LINE))
    table.setStyle(TableStyle(commands))
    return table


def _summary_rows(resumo: dict[str, Any], parametros: dict[str, Any]) -> list[tuple[str, str]]:
    """Monta a composição financeira final com nomenclatura simples."""
    rows: list[tuple[str, str]] = [
        ("Valor atualizado", _format_currency_br(resumo.get("total_atualizado", 0))),
        ("Juros moratórios", _format_currency_br(resumo.get("total_juros_moratorios", 0))),
    ]
    if _as_decimal(resumo.get("total_multa")) != 0:
        rows.append(("Multa", _format_currency_br(resumo.get("total_multa"))))
    if _as_decimal(resumo.get("honorarios_informados")) != 0:
        rows.append(("Honorários", _format_currency_br(resumo.get("honorarios_informados"))))
    if _as_decimal(resumo.get("multa_art_523")) != 0:
        rows.append(("Multa do art. 523 do CPC", _format_currency_br(resumo.get("multa_art_523"))))
    if _as_decimal(resumo.get("honorarios_art_523")) != 0:
        rows.append(("Honorários do art. 523 do CPC", _format_currency_br(resumo.get("honorarios_art_523"))))
    if _as_decimal(resumo.get("valor_compensacao")) != 0:
        rows.append(("Compensação (-)", _format_currency_br(resumo.get("valor_compensacao"))))
    rows.append(("TOTAL GERAL", _format_currency_br(resumo.get("total_geral", 0))))
    return rows


def _build_summary_table(resumo: dict[str, Any], parametros: dict[str, Any], styles: dict[str, ParagraphStyle], available_width: float) -> Table:
    """Cria quadro de composição do total no fim da memória detalhada."""
    rows = _summary_rows(resumo, parametros)
    data: list[list[Any]] = []
    for label, value in rows:
        total = label == "TOTAL GERAL"
        data.append([
            _paragraph(label, styles["total_label"] if total else styles["summary_label"]),
            _paragraph(value, styles["total_label"] if total else styles["summary_value"]),
        ])
    width = min(105 * mm, available_width * 0.46)
    table = Table(data, colWidths=[width * 0.62, width * 0.38], hAlign="RIGHT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -2), PAPER),
        ("LINEBELOW", (0, 0), (-1, -2), 0.35, LINE),
        ("BACKGROUND", (0, -1), (-1, -1), ACCENT_SOFT),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor("#E8CCD3")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8 * mm),
    ]))
    return table


def _draw_footer(canvas, doc) -> None:
    """Desenha rodapé discreto e consistente em todas as páginas."""
    canvas.saveState()
    width, _ = doc.pagesize
    y = 7 * mm
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(doc.leftMargin, y + 4 * mm, width - doc.rightMargin, y + 4 * mm)
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, y, "Memória de cálculo judicial")
    canvas.drawRightString(width - doc.rightMargin, y, f"Página {doc.page}")
    canvas.restoreState()


def salvar_resultado_pdf(
    resultado: ResultadoCalculo,
    caminho: str | Path,
    *,
    identificador_calculo: str | None = None,
    versao_calculo: int | None = None,
) -> None:
    """Gera a memória PDF com resumo didático, identidade e versão do cálculo."""
    destination = Path(caminho)
    destination.parent.mkdir(parents=True, exist_ok=True)
    memory = resultado.memoria.copy() if resultado.memoria is not None else pd.DataFrame()
    if memory.empty:
        raise ValueError("Não há memória de cálculo para exportar em PDF.")

    parametros = dict(resultado.parametros or {})
    resumo = _resumo_dict(resultado)
    page_size = landscape(A4)
    left = right = 14 * mm
    top = 12 * mm
    bottom = 16 * mm
    available_width = page_size[0] - left - right
    styles = _build_styles()

    doc = SimpleDocTemplate(
        str(destination),
        pagesize=page_size,
        leftMargin=left,
        rightMargin=right,
        topMargin=top,
        bottomMargin=bottom,
        title="Memória de cálculo judicial",
        author="Auditoria de Pagamentos",
        subject="Memória de cálculo",
    )

    story: list[Any] = [
        Paragraph("APLICAÇÃO", styles["eyebrow"]),
        Paragraph("Memória de cálculo judicial", styles["title"]),
        Paragraph(_identity_text(parametros), styles["subtitle"]),
        Spacer(1, 3 * mm),
        _calculation_identity_table(
            parametros,
            styles,
            available_width,
            identificador_calculo=identificador_calculo,
            versao_calculo=versao_calculo,
        ),
        Spacer(1, 5 * mm),
    ]
    story.extend(_build_executive_summary(resultado, styles, available_width))
    story.append(Spacer(1, 5 * mm))
    story.extend(_build_damage_summary(resultado, styles, available_width))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Memória detalhada", styles["section"]))
    story.append(_build_memory_table(memory, parametros, styles, available_width))
    story.append(Spacer(1, 5 * mm))
    story.append(KeepTogether([
        Paragraph("Composição do resultado", styles["section"]),
        _build_summary_table(resumo, parametros, styles, available_width),
    ]))

    issues = parametros.get("validation_issues") or []
    if issues:
        notes: list[Any] = [Spacer(1, 5 * mm), Paragraph("Observações", styles["section"])]
        for issue in issues[:8]:
            message = issue.get("message") if isinstance(issue, dict) else str(issue)
            notes.append(_paragraph(f"- {message}", styles["note"]))
        story.append(KeepTogether(notes))

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)


__all__ = ["salvar_resultado_pdf"]

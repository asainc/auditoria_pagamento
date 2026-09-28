"""Regressões dos critérios financeiros independentes por natureza do dano."""
from __future__ import annotations

from decimal import Decimal

from pypdf import PdfReader

from judicial_calc import calcular_debitos, salvar_resultado_pdf
from judicial_calc.io.pdf import MEMORY_COLUMNS


def _params() -> dict:
    """Monta um cenário determinístico sem dependência de rede."""
    return {
        "indice": "sem_correcao",
        "mes_atualizacao": "março",
        "ano_atualizacao": 2026,
        "juros_moratorios_tipo": "sem_juros",
        "auto_atualizar_planilhas_indices": False,
        "tabela_indices": [
            {"mes": "2026-01", "indice": "100"},
            {"mes": "2026-02", "indice": "110"},
        ],
        "parametros_por_dano": {
            "dano_material": {
                "indice": "sem_correcao",
                "mes_atualizacao": "março",
                "ano_atualizacao": 2026,
                "juros_moratorios_tipo": "sem_juros",
            },
            "dano_moral": {
                "indice": "indice_moral_sintetico",
                "mes_atualizacao": "março",
                "ano_atualizacao": 2026,
                "juros_moratorios_tipo": "capitalizacao_simples",
                "juros_moratorios_taxa": "1",
                "juros_moratorios_periodicidade": "mensal",
                "juros_moratorios_pro_rata": False,
            },
        },
    }


def test_material_and_moral_use_independent_update_and_moratory_interest():
    """Cada dano usa seu próprio índice e sua própria configuração de juros."""
    result = calcular_debitos(
        [
            {"item": 1, "data": "2026-01-01", "valor_singelo": "100", "descricao": "Material", "verba_tipo": "dano_material"},
            {"item": 2, "data": "2026-01-01", "valor_singelo": "100", "descricao": "Moral", "verba_tipo": "dano_moral"},
        ],
        **_params(),
    )

    material = result.memoria.loc[result.memoria["verba_tipo"] == "dano_material"].iloc[0]
    moral = result.memoria.loc[result.memoria["verba_tipo"] == "dano_moral"].iloc[0]

    assert material["indice_correcao"] == "sem_correcao"
    assert material["valor_atualizado"] == Decimal("100.00")
    assert material["juros_moratorios"] == Decimal("0.00")

    assert moral["indice_correcao"] == "indice_moral_sintetico"
    assert moral["valor_atualizado"] == Decimal("110.00")
    assert moral["juros_moratorios"] == Decimal("2.20")
    assert result.parametros["parametros_por_dano"]["dano_material"]["indice"] == "sem_correcao"
    assert result.parametros["parametros_por_dano"]["dano_moral"]["indice"] == "indice_moral_sintetico"


def test_moral_damage_does_not_receive_material_only_penalty_rules():
    """Multa e compensação permanecem exclusivas do dano material em processo misto."""
    params = _params()
    params.update({
        "multa_tipo": "fixo",
        "multa_valor": "50",
        "compensacao_flag": True,
        "compensacao_tipo_calculo": "fixo",
        "compensacao_valor": "20",
    })
    result = calcular_debitos(
        [
            {"item": 1, "data": "2026-01-01", "valor_singelo": "100", "descricao": "Material", "verba_tipo": "dano_material"},
            {"item": 2, "data": "2026-01-01", "valor_singelo": "100", "descricao": "Moral", "verba_tipo": "dano_moral"},
        ],
        **params,
    )
    material = result.memoria.loc[result.memoria["verba_tipo"] == "dano_material"].iloc[0]
    moral = result.memoria.loc[result.memoria["verba_tipo"] == "dano_moral"].iloc[0]

    assert material["multa"] == Decimal("50.00")
    assert moral["multa"] == Decimal("0.00")
    assert material["compensacao_linha"] == Decimal("20.00")
    assert moral["compensacao_linha"] == Decimal("0.00")


def test_pdf_memory_columns_are_stable_and_do_not_include_penalty_column():
    """A tabela PDF mantém exatamente as sete colunas definidas pelo produto."""
    assert [(field, label) for field, label, _, _ in MEMORY_COLUMNS] == [
        ("item", "Item"),
        ("descricao", "Descrição"),
        ("data", "Data"),
        ("valor_singelo", "Valor Singelo"),
        ("valor_atualizado", "Valor Atualizado"),
        ("juros_moratorios", "Juros Moratórios"),
        ("total", "Total"),
    ]


def test_redesigned_pdf_starts_with_summary_and_keeps_separate_damage_criteria(tmp_path):
    """O PDF expõe resumo didático, critérios por dano e as sete colunas oficiais."""
    result = calcular_debitos(
        [
            {"item": 1, "data": "2026-01-01", "valor_singelo": "100", "descricao": "Material", "verba_tipo": "dano_material"},
            {"item": 2, "data": "2026-01-01", "valor_singelo": "100", "descricao": "Moral", "verba_tipo": "dano_moral"},
        ],
        **_params(),
    )
    result.parametros["numero_processo"] = "1234567-89.2026.8.26.0001"
    target = tmp_path / "memoria.pdf"
    salvar_resultado_pdf(result, target, identificador_calculo="CALC-TESTE-001", versao_calculo=7)
    text = " ".join(page.extract_text() or "" for page in PdfReader(str(target)).pages)
    assert "Resumo do cálculo" in text
    assert "Identificador do cálculo" in text
    assert "CALC-TESTE-001" in text
    assert "Versão do cálculo" in text
    assert "V7" in text
    assert "Critérios por natureza do dano" in text
    assert "Dano Material" in text and "Dano Moral" in text
    for header in ("Item", "Descrição", "Data", "Valor Singelo", "Valor Atualizado", "Juros Moratórios", "Total"):
        assert header in text
    assert "MULTA" not in text.upper().split("MEMÓRIA DETALHADA", 1)[-1].split("COMPOSIÇÃO DO RESULTADO", 1)[0]

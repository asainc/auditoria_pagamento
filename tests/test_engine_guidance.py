"""A orientação de erros usa campos estruturados e nunca ecoa valores recebidos."""
from backend.services.engine_guidance import engine_error_guidance
from judicial_calc.core.errors import CalculationValidationError


def test_guidance_identifies_dual_index_interval():
    error = CalculationValidationError(
        "invalid_dual_index_interval",
        ["duplo_indice_primeiro_data_inicio", "duplo_indice_primeiro_data_fim"],
    )
    message = engine_error_guidance(error)
    assert "Primeiro índice - data inicial" in message
    assert "Primeiro índice - data final" in message


def test_guidance_identifies_compensation_parameter_without_echoing_value():
    error = CalculationValidationError(
        "invalid_compensation_value",
        ["compensacao_valor"],
        "valor=999999",
    )
    message = engine_error_guidance(error)
    assert "Valor ou percentual da compensação" in message
    assert "999999" not in message


def test_guidance_maps_index_catalog_failure():
    error = CalculationValidationError("invalid_correction_index", ["indice"], "segredo")
    message = engine_error_guidance(error)
    assert "Índice de correção" in message
    assert "segredo" not in message


def test_guidance_does_not_parse_unstructured_exception_text():
    message = engine_error_guidance(ValueError("compensacao_valor=999999"))
    assert "999999" not in message
    assert "Revise os parâmetros" in message

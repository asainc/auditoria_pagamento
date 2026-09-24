"""Regressões da cobertura real dos índices no contrato HTTP de cálculo."""


def test_ipca15_future_competence_returns_precise_message(client):
    """Competência acima da série instalada deve informar o mês ausente e o limite."""
    payload = {
        "origem_calculo": "manual",
        "numero_processo": None,
        "identificador_calculo": "manual-ipca15",
        "parcelas": [{"data": "2026-01-15", "valor_singelo": "100.00", "verba_tipo": "dano_material"}],
        "parametros": {
            "indice": "ipca_15_ibge",
            "mes_atualizacao": "setembro",
            "ano_atualizacao": 2026,
            "juros_moratorios_tipo": "sem_juros",
            "juros_compensatorios_tipo": "sem_juros",
        },
        "revisao_humana_confirmada": True,
        "competencia_automatica": False,
    }

    response = client.post("/api/calculos", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "IPCA-15 (IBGE) não possui taxa para ago/2026" in detail
    assert "Última competência disponível: abr/2026" in detail
    assert "competência máxima de atualização suportada é mai/2026" in detail

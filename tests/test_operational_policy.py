"""Testes unitários dos padrões operacionais aplicados sobre extrações sintéticas."""
from datetime import date
from decimal import Decimal
import pytest
from backend.models import ChronologyDecision, ExtractionResult, FieldEvidence, Installment
from backend.services.operational_policy import OperationalPolicy, fee_installments
from judicial_calc.data_sources.local_excel import local_index_coverage


def result(fields=None, rows=None):
    """Somente conteúdo fictício para a regra posterior à verificação de fontes."""
    return ExtractionResult(numero_processo="1001",campos=[FieldEvidence(campo=key,valor=value,documento="1001_1.pdf",pagina=1,trecho="Trecho sintético",escopo="caso_concreto") for key,value in (fields or [])],parcelas=rows or [],alertas=[],versao_prompts="synthetic")


def adjustments(output):
    return {item.campo:item.valor for item in output.ajustes_operacionais}


def test_authorized_defaults_fill_only_absent_fields():
    output=OperationalPolicy().apply(result(),date(2027,2,12))
    values=adjustments(output)
    coverage=local_index_coverage("tjsp_inpc_ipca15_lei_14905")
    expected_year=int(coverage.maximum_update_competence[:4])
    expected_month={1:"janeiro",2:"fevereiro",3:"março",4:"abril",5:"maio",6:"junho",7:"julho",8:"agosto",9:"setembro",10:"outubro",11:"novembro",12:"dezembro"}[int(coverage.maximum_update_competence[5:7])]
    assert values["parametros.indice"]=="tjsp_inpc_ipca15_lei_14905"
    assert values["parametros.juros_moratorios_tipo"]=="taxa_legal_12_aa_6_aa"
    assert values["parametros.juros_compensatorios_tipo"]=="taxa_legal_12_aa_6_aa"
    assert values["parametros.art_523"]=="nao_aplicar"
    assert values["parametros.mes_atualizacao"]==expected_month
    assert values["parametros.ano_atualizacao"]==expected_year
    assert "parametros.honorarios_tipo" not in values
    assert output.competencia_automatica
    assert "parametros.juros_moratorios_data_inicio" not in values
    assert output.campos==[]  # Padrão não se transforma em citação fictícia.


def test_explicit_index_and_capitalization_are_preserved():
    source=result([("parametros.indice","sem_correcao"),("parametros.juros_moratorios_tipo","capitalizacao_simples"),("parametros.juros_moratorios_taxa","1"),("parametros.juros_compensatorios_tipo","sem_juros"),("parametros.art_523","aplicar_multa"),("parametros.mes_atualizacao","março"),("parametros.ano_atualizacao",2026)])
    output=OperationalPolicy().apply(source,date(2027,2,12))
    values=adjustments(output)
    assert "parametros.indice" not in values
    assert "parametros.juros_moratorios_tipo" not in values
    assert "parametros.juros_compensatorios_tipo" not in values
    assert "parametros.art_523" not in values
    assert "parametros.mes_atualizacao" not in values
    assert not output.competencia_automatica


def test_named_tjsp_table_maps_to_existing_key():
    output=OperationalPolicy().apply(result([("parametros.indice","Tabela Prática do TJSP")]))
    assert adjustments(output)["parametros.indice"]=="tjsp_inpc_ipca15_lei_14905"


@pytest.mark.parametrize("fields,expected",[
    ([("processo.data_peticao_inicial","2025-01-12")],"2025-01-12"),
    ([("processo.data_citacao","2025-02-10"),("processo.data_peticao_inicial","2025-01-12")],"2025-02-10"),
])
def test_citation_or_documented_petition_date(fields,expected):
    assert adjustments(OperationalPolicy().apply(result(fields)))["parametros.juros_moratorios_data_inicio"]==expected


def test_conflicting_citation_dates_are_not_treated_as_missing():
    source=result([("processo.data_citacao","2025-02-10"),("processo.data_citacao","2025-02-11"),("processo.data_peticao_inicial","2025-01-12")])
    assert "parametros.juros_moratorios_data_inicio" not in adjustments(OperationalPolicy().apply(source))


def test_fees_use_only_moral_nominal_values_and_documented_percentage():
    rows=[Installment(data="2025-01-01",valor_singelo="1000",verba_tipo="dano_moral"),Installment(data="2025-02-01",valor_singelo="5000",verba_tipo="dano_material")]
    output=OperationalPolicy().apply(result([("parametros.honorarios","10"),("parametros.honorarios_tipo","percentual")],rows))
    generated=[row for row in output.parcelas if row.origem=="honorarios_dano_moral"]
    assert len(generated)==1 and generated[0].valor_singelo==Decimal("100.00")
    assert generated[0].data==date(2025,1,1)
    assert output.honorarios_sobre_danos_morais
    assert fee_installments(output.parcelas,Decimal("10"))==output.parcelas


def test_conflicting_fee_type_does_not_generate_installments():
    """Conflito documental não é resolvido por padrão operacional silencioso."""
    rows=[Installment(data="2025-01-01",valor_singelo="1000",verba_tipo="dano_moral")]
    output=OperationalPolicy().apply(result([("parametros.honorarios","10"),("parametros.honorarios_tipo","fixo"),("parametros.honorarios_tipo","percentual")],rows))
    assert not any(row.origem=="honorarios_dano_moral" for row in output.parcelas)
    assert "parametros.honorarios_tipo" not in adjustments(output)

def test_fees_are_not_invented_without_percentage():
    output=OperationalPolicy().apply(result(rows=[Installment(data="2025-01-01",valor_singelo="1000",verba_tipo="dano_moral")]))
    assert len(output.parcelas)==1 and not output.honorarios_sobre_danos_morais


def test_fee_preparation_and_real_engine_do_not_charge_twice(client,payload):
    rows=[{"data":"2025-01-01","valor_singelo":"1000.00","verba_tipo":"dano_moral"}]
    prepared=client.post("/api/calculos/honorarios/preparar",json={"parcelas":rows,"percentual":"10"})
    assert prepared.status_code==200
    payload["parcelas"]=prepared.json()
    payload["parametros"].update(honorarios="10",honorarios_tipo="percentual")
    payload["honorarios_sobre_danos_morais"]=True
    response=client.post("/api/calculos",json=payload)
    assert response.status_code==200,response.text
    summary={row["campo"]:row["valor"] for row in response.json()["resumo"]}
    assert Decimal(summary["honorarios"])==0
    assert len(response.json()["memoria"]["linhas"])==2
    payload["parcelas"][0]["valor_singelo"]="2000.00"
    rejected=client.post("/api/calculos",json=payload)
    assert rejected.status_code==422 and "Atualizar honorários" in rejected.text


def test_current_competence_endpoint_and_stale_automatic_request(client,payload):
    current=client.get("/api/calculos/padroes")
    assert current.status_code==200 and 1900<current.json()["ano"]<2200
    payload["competencia_automatica"]=True
    payload["parametros"]["ano_atualizacao"]=1900
    assert client.post("/api/calculos",json=payload).status_code==409


def test_current_competence_endpoint_limits_ipca15_to_available_series(client):
    coverage=local_index_coverage("ipca_15_ibge")
    current=client.get("/api/calculos/padroes",params={"indice":"ipca_15_ibge"})
    assert current.status_code==200
    body=current.json()
    assert body["competencia_recomendada"] <= coverage.maximum_update_competence
    if body["ajustada_por_disponibilidade"]:
        assert body["competencia_recomendada"] == coverage.maximum_update_competence


def test_request_defaults_depend_on_origin(payload):
    """O contrato diferencia o modo manual de teste de um processo real sem alterar valores explícitos."""
    from backend.models import CalculationRequest

    manual = dict(payload)
    manual["origem_calculo"] = "manual"
    manual["numero_processo"] = None
    manual["parametros"] = dict(payload["parametros"])
    manual["parametros"].pop("juros_moratorios_tipo", None)
    manual["parametros"].pop("juros_compensatorios_tipo", None)
    manual["parametros"].pop("art_523", None)
    validated_manual = CalculationRequest.model_validate(manual)
    assert validated_manual.parametros.juros_moratorios_tipo == "sem_juros"
    assert validated_manual.parametros.juros_compensatorios_tipo == "sem_juros"
    assert validated_manual.parametros.art_523 == "nao_aplicar"

    real = dict(payload)
    real["origem_calculo"] = "processo"
    real["numero_processo"] = "1001"
    real["parametros"] = dict(payload["parametros"])
    real["parametros"].pop("juros_moratorios_tipo", None)
    real["parametros"].pop("juros_compensatorios_tipo", None)
    real["parametros"].pop("art_523", None)
    validated_real = CalculationRequest.model_validate(real)
    assert validated_real.parametros.juros_moratorios_tipo == "taxa_legal_12_aa_6_aa"
    assert validated_real.parametros.juros_compensatorios_tipo == "taxa_legal_12_aa_6_aa"
    assert validated_real.parametros.art_523 == "nao_aplicar"


def test_explicitly_cleared_parameter_does_not_receive_operational_default():
    """Um comando decisório de afastamento não é confundido com simples omissão documental."""
    source = result([("parametros.juros_moratorios_tipo", "taxa_legal_12_aa_6_aa")])
    source.decisoes_cronologicas = [
        ChronologyDecision(
            campo="parametros.juros_moratorios_tipo",
            valor=None,
            documento="1001_9.pdf",
            pagina=4,
            sequencia=9,
            natureza="comando_decisorio",
            efeito="afasta",
            motivo="Critério afastado no documento sintético.",
        )
    ]
    output = OperationalPolicy().apply(source)
    assert "parametros.juros_moratorios_tipo" not in adjustments(output)

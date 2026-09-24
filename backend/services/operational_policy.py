"""Aplica critérios operacionais rastreáveis antes da revisão humana do cálculo."""
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from pydantic import TypeAdapter
from backend.errors import ServiceError
from backend.config import OperationalSettings
from backend.models import CalculationDefaults, CalculationRequest, ExtractionResult, Installment, OperationalAdjustment, Rate
from judicial_calc.data_sources.local_excel import local_index_coverage
from judicial_calc.indices.registry import create_default_index_registry

MONTHS = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")


def current_competence(today: date | None = None, index_key: str | None = None) -> CalculationDefaults:
    """Retorna a competência recomendada, respeitando a cobertura do índice.

    O relógio da aplicação define o teto desejado. Quando uma série local não
    alcança esse mês, a recomendação é reduzida para a maior competência que o
    motor consegue calcular sem estimar dados ausentes.
    """
    today = today or datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    desired = f"{today.year:04d}-{today.month:02d}"
    recommended = desired
    adjusted = False
    message = None
    if index_key and index_key != "sem_correcao":
        try:
            coverage = local_index_coverage(index_key)
        except (ValueError, FileNotFoundError):
            coverage = None
        if coverage is not None and coverage.maximum_update_competence < recommended:
            recommended = coverage.maximum_update_competence
            adjusted = True
            message = (
                f"Competência limitada pela última série disponível de {coverage.label}; "
                "nenhum índice ausente foi estimado."
            )
    year = int(recommended[:4])
    month = int(recommended[5:7])
    return CalculationDefaults(
        mes=MONTHS[month - 1],
        ano=year,
        competencia_recomendada=recommended,
        ajustada_por_disponibilidade=adjusted,
        mensagem=message,
    )


def fee_installments(rows: list[Installment], percentage: Decimal) -> list[Installment]:
    """Compõe parcelas nominais de honorários; não calcula juros ou correção."""
    percentage = TypeAdapter(Rate).validate_python(percentage)
    base = [row for row in rows if row.origem != "honorarios_dano_moral"]
    if any(row.verba_tipo == "honorarios" for row in base):
        raise ServiceError("Existem honorários informados manualmente. Revise-os antes de gerar honorários sobre danos morais.")
    result = list(base)
    for row in base:
        if row.verba_tipo == "dano_moral" and percentage > 0:
            amount = (row.valor_singelo * percentage / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            result.append(Installment(data=row.data, valor_singelo=amount, verba_tipo="honorarios", origem="honorarios_dano_moral", descricao=f"Honorários {percentage}% sobre dano moral original; data da parcela-base"))
    return result


def validate_prepared_request(payload: CalculationRequest) -> None:
    """Não permite duplicar encargos nem calcular sobre uma composição desatualizada."""
    generated = [row for row in payload.parcelas if row.origem == "honorarios_dano_moral"]
    if generated and not payload.honorarios_sobre_danos_morais:
        raise ServiceError("Parcelas de honorários geradas exigem o modo honorários sobre danos morais.")
    if payload.honorarios_sobre_danos_morais:
        if not any(row.verba_tipo == "dano_moral" for row in payload.parcelas):
            raise ServiceError("Honorários sobre danos morais exigem ao menos uma parcela de dano moral.")
        if payload.parametros.honorarios is None or payload.parametros.honorarios_tipo != "percentual":
            raise ServiceError("Honorários sobre danos morais exigem percentual informado.")
        expected = fee_installments(payload.parcelas, payload.parametros.honorarios)
        expected_rows = [(row.data, row.valor_singelo, row.verba_tipo) for row in expected if row.origem == "honorarios_dano_moral"]
        if [(row.data, row.valor_singelo, row.verba_tipo) for row in generated] != expected_rows:
            raise ServiceError("A base ou o percentual mudou. Clique em Atualizar honorários e confirme novamente a revisão.")
    if payload.competencia_automatica:
        current = current_competence(index_key=payload.parametros.indice)
        if (payload.parametros.mes_atualizacao, payload.parametros.ano_atualizacao) != (current.mes, current.ano):
            raise ServiceError("A competência automática mudou. Desmarque e confirme novamente a revisão para atualizar mês e ano.", 409)


class OperationalPolicy:
    """Aplica os padrões após conferir evidências, separando-os dos fatos extraídos."""
    def __init__(self, configuration: OperationalSettings | None = None):
        """Configuração central permite alterar seleção sem editar o motor."""
        self.configuration = configuration or OperationalSettings()

    def apply(self, extracted: ExtractionResult, today: date | None = None) -> ExtractionResult:
        """Aplica padrões somente quando a evidência do caso concreto não informa o campo.

        A função trabalha sobre uma cópia da extração. Evidências permanecem intactas
        em ``campos`` e cada padrão é incluído em ``ajustes_operacionais`` com motivo
        textual. Dessa forma, a interface consegue distinguir o que veio do documento
        do que foi definido pela política operacional.
        """
        result = extracted.model_copy(deep=True)

        def values(path: str) -> set[str]:
            """Coleta o estado cronológico efetivo antes de recorrer às evidências brutas."""
            if path.startswith("parametros."):
                key = path.split(".", 1)[1]
                if key in result.parametros_consolidados and result.parametros_consolidados[key] is not None:
                    return {str(result.parametros_consolidados[key])}
                decision = next((item for item in reversed(result.decisoes_cronologicas) if item.campo == path), None)
                if decision is not None:
                    return {str(decision.valor)} if decision.valor is not None else set()
            return {str(field.valor) for field in result.campos if field.campo == path and field.valor is not None and field.escopo == "caso_concreto"}

        def unique(path: str) -> str | None:
            """Retorna o único valor documental quando não existe conflito no campo."""
            found = values(path)
            return next(iter(found)) if len(found) == 1 else None

        def explicitly_cleared(path: str) -> bool:
            """Indica que decisão posterior afastou o campo sem fornecer substituto."""
            return any(
                decision.campo == path and decision.efeito == "afasta" and decision.valor is None
                for decision in result.decisoes_cronologicas
            )

        def assign(field: str, value: object, reason: str) -> None:
            """Registra um padrão operacional sem convertê-lo em evidência documental."""
            result.ajustes_operacionais.append(OperationalAdjustment(campo="parametros." + field, valor=value, motivo=reason))

        index = unique("parametros.indice")
        effective_index = index
        registry = create_default_index_registry()
        if (not values("parametros.indice") and not explicitly_cleared("parametros.indice")) or (index and registry.get(index) is None and ("tjsp" in index.lower() or "tabela prática" in index.lower())):
            key = self.configuration.default_index
            if registry.get(key) is None:
                raise ServiceError("O índice TJSP configurado não existe no catálogo instalado.", 503)
            assign("indice", key, "Padrão autorizado: TJSP (INPC/IPCA-15 - Lei 14905), na ausência de chave informada.")
            effective_index = key
        if not values("parametros.juros_moratorios_tipo") and not explicitly_cleared("parametros.juros_moratorios_tipo"):
            assign(
                "juros_moratorios_tipo",
                self.configuration.default_moratory_type,
                "Documento sem tipo de juros moratórios: aplicada a Taxa Legal - 12% a.a. / 6% a.a. como critério operacional padrão.",
            )
        if not values("parametros.juros_compensatorios_tipo") and not explicitly_cleared("parametros.juros_compensatorios_tipo"):
            assign(
                "juros_compensatorios_tipo",
                self.configuration.default_compensatory_type,
                "Documento sem tipo de juros compensatórios: aplicada a Taxa Legal - 12% a.a. / 6% a.a. como critério operacional padrão.",
            )
        if not values("parametros.art_523") and not explicitly_cleared("parametros.art_523"):
            assign(
                "art_523",
                self.configuration.default_art_523,
                "Documento sem comando explícito sobre o art. 523 do CPC: definido como não aplicar.",
            )
        if not values("parametros.juros_moratorios_data_inicio") and not explicitly_cleared("parametros.juros_moratorios_data_inicio"):
            citation = unique("processo.data_citacao")
            petition = unique("processo.data_peticao_inicial")
            source = (citation or petition) if len(values("processo.data_citacao")) <= 1 else None
            if source:
                try:
                    source = date.fromisoformat(source).isoformat()
                except ValueError:
                    result.alertas.append("Data processual inválida: informe manualmente o início dos juros.")
                else:
                    assign("juros_moratorios_data_inicio", source, "Data da citação documentada." if citation else "Citação sem data disponível: utilizada a data documentada da petição inicial, conforme regra autorizada.")
            else:
                result.alertas.append("Sem data verificável da citação ou da petição inicial: início dos juros exige preenchimento manual.")
        current = current_competence(today, effective_index)
        missing_month = not values("parametros.mes_atualizacao") and not explicitly_cleared("parametros.mes_atualizacao")
        missing_year = not values("parametros.ano_atualizacao") and not explicitly_cleared("parametros.ano_atualizacao")
        if missing_month:
            reason = "Competência automática limitada à disponibilidade real do índice selecionado." if current.ajustada_por_disponibilidade else "Mês atual no horário de Brasília, conforme regra autorizada."
            assign("mes_atualizacao", current.mes, reason)
        if missing_year:
            reason = "Competência automática limitada à disponibilidade real do índice selecionado." if current.ajustada_por_disponibilidade else "Ano atual no horário de Brasília, conforme regra autorizada."
            assign("ano_atualizacao", current.ano, reason)
        result.competencia_automatica = missing_month and missing_year
        fee_types = values("parametros.honorarios_tipo")
        if len(fee_types) > 1:
            result.alertas.append("Conflito no tipo de honorários: nenhuma parcela automática foi gerada; revise o critério documental.")
        percentage = unique("parametros.honorarios") if unique("parametros.honorarios_tipo") == "percentual" else None
        if percentage is not None and any(row.verba_tipo == "dano_moral" for row in result.parcelas) and not any(row.verba_tipo == "honorarios" for row in result.parcelas):
            try:
                rate = TypeAdapter(Rate).validate_python(percentage)
                result.parcelas = fee_installments(result.parcelas, rate)
                result.honorarios_sobre_danos_morais = True
                result.ajustes_operacionais.append(OperationalAdjustment(campo="parcelas.honorarios", valor=str(rate), motivo="Percentual documental aplicado ao valor nominal de cada dano moral, com arredondamento de centavos e mesma data da parcela-base. Encargo global desativado para evitar dupla cobrança."))
            except (ValueError, ArithmeticError):
                result.alertas.append("Percentual de honorários inválido: revise o valor antes de gerar as parcelas.")
        return result

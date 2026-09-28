"""Única fachada do cálculo: adapta tipos sem reproduzir fórmulas."""
from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
from filelock import FileLock

from judicial_calc import calcular_debitos, salvar_resultado_pdf
from judicial_calc.core.types import ResultadoCalculo
from backend.config import ROOT, Settings
from backend.models import CalculationRequest, DataTable, Scalar
from backend.services.operational_policy import validate_prepared_request


def file_hashes(directory: Path, pattern: str) -> dict[str, str]:
    """Hash de conteúdo identifica código e séries sem incluir dados nos logs."""
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.rglob(pattern))}


def digest(values: dict[str, str]) -> str:
    """Ordenação torna o identificador independente da ordem do filesystem."""
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def scalar(value: object) -> Scalar:
    """Decimais viram texto para evitar arredondamento binário na serialização."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def dataframe_table(frame: pd.DataFrame) -> DataTable:
    """O formato tabular admite colunas adicionais produzidas pelo próprio motor."""
    return DataTable(colunas=[str(column) for column in frame.columns], linhas=[[scalar(value) for value in row] for row in frame.itertuples(index=False, name=None)])


class EngineFacade:
    """Isola o motor de cálculo dos contratos HTTP e das estruturas da interface."""
    def __init__(self, settings: Settings):
        """Recebe dependências explicitamente para manter configuração e testes isolados."""
        self.lock = FileLock(settings.data_dir / "indices.lock", timeout=120)
        self.engine_hash = digest(file_hashes(ROOT / "src", "*.py"))

    def calculate(self, payload: CalculationRequest) -> ResultadoCalculo:
        """Converte a requisição validada para o formato esperado pelo motor e executa o cálculo."""
        params = payload.parametros.model_dump(mode="json", exclude_none=True)
        if payload.parametros_por_dano is not None:
            params["parametros_por_dano"] = payload.parametros_por_dano.model_dump(mode="json", exclude_none=True)
        validate_prepared_request(payload)
        if payload.honorarios_sobre_danos_morais:
            params["honorarios"] = "0"
        # Atualização de arquivos tem endpoint próprio e usa a mesma exclusão mútua.
        params["auto_atualizar_planilhas_indices"] = False
        installments = [dict(item=index, **row.model_dump(mode="json", exclude={"origem"})) for index, row in enumerate(payload.parcelas, 1)]
        result = calcular_debitos(installments, **params)
        # A identidade do cadastro não participa das fórmulas, mas melhora a
        # rastreabilidade da memória PDF. Ela é anexada somente depois do motor.
        result.parametros["numero_processo"] = payload.numero_processo
        result.parametros["identificador_calculo"] = payload.identificador_calculo
        return result

    def pdf(
        self,
        result: ResultadoCalculo,
        *,
        identificador_calculo: str | None = None,
        versao_calculo: int | None = None,
    ) -> bytes:
        """Gera a única memória PDF com identidade de negócio e versão quando conhecidas."""
        with tempfile.TemporaryDirectory(prefix="judicial_export_") as directory:
            path = Path(directory) / "memoria.pdf"
            salvar_resultado_pdf(
                result,
                path,
                identificador_calculo=identificador_calculo,
                versao_calculo=versao_calculo,
            )
            return path.read_bytes()

    def index_hash(self) -> str:
        """A versão das séries é capturada enquanto o cálculo detém o lock."""
        return digest(file_hashes(ROOT / "src/judicial_calc/data", "*.xlsx"))

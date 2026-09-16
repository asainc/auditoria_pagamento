"""Importadores rejeitam linhas inválidas em vez de alterar o lote silenciosamente."""
from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from backend.errors import ServiceError
from backend.models import BatchImport, CalculationDraft, Installment


def read_table(content: bytes, filename: str) -> list[dict[str, str]]:
    """Somente formatos documentados; CSV exige UTF-8 e preserva identificadores."""
    suffix = Path(filename).suffix.lower()
    try:
        if suffix in {".xlsx", ".xls"}:
            frame = pd.read_excel(io.BytesIO(content), dtype=str).fillna("")
            if len(frame) > 10000:
                raise ServiceError("Planilha excede 10.000 linhas.")
            return frame.to_dict("records")
        if suffix == ".csv":
            text = content.decode("utf-8-sig")
            delimiter = ";" if ";" in text.splitlines()[0] else ","
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)
            if len(rows) > 10000:
                raise ServiceError("CSV excede 10.000 linhas.")
            return rows
    except (ValueError, UnicodeError, OSError, IndexError) as exc:
        raise ServiceError("Não foi possível ler a planilha. Use Excel válido ou CSV UTF-8.") from exc
    raise ServiceError("Formato não suportado. Use XLSX, XLS ou CSV.")


def normalize_date(value: object) -> str:
    """Datas ISO têm prioridade; o formato brasileiro é aceito explicitamente."""
    text = str(value).strip().split(" ")[0]
    for pattern in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    raise ServiceError("Data inválida. Use AAAA-MM-DD ou DD/MM/AAAA.")


def normalize_money(value: object) -> str:
    """A vírgula identifica formato brasileiro; decimal canônico usa ponto."""
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        result = Decimal(text)
        if not result.is_finite():
            raise InvalidOperation
        return str(result)
    except InvalidOperation as exc:
        raise ServiceError("Valor monetário inválido.") from exc


def installment_from_row(row: dict[str, str], damage_type: str) -> Installment:
    """Normalização de arquivo fica centralizada e usa o mesmo contrato da API."""
    return Installment.model_validate({"data": normalize_date(row.get("data", "")), "valor_singelo": normalize_money(row.get("valor_singelo", row.get("valor", ""))), "descricao": row.get("descricao", ""), "verba_tipo": row.get("verba_tipo") or damage_type})


class ImportService:
    """A prévia nunca calcula nem confirma revisão humana."""
    def installments(self, content: bytes, filename: str, damage_type: str) -> list[Installment]:
        """Importa todas as linhas ou informa erro, sem omitir valores inválidos."""
        rows = read_table(content, filename)
        if not rows:
            raise ServiceError("A planilha não contém parcelas.")
        result = []
        for index, row in enumerate(rows, 2):
            try:
                result.append(installment_from_row(row, damage_type))
            except (ValidationError, ServiceError) as exc:
                raise ServiceError(f"Linha {index} inválida. Confira data, valor e tipo de verba; nenhuma parcela foi importada.") from exc
        return result

    def batch(self, content: bytes, filename: str) -> BatchImport:
        """JSON carrega o contrato completo; planilhas agrupam parcelas por processo."""
        try:
            if Path(filename).suffix.lower() == ".json":
                raw = json.loads(content.decode("utf-8-sig"))
                rows = raw["processos"]
                if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
                    raise ServiceError("Informe entre 1 e 100 processos.")
                drafts = [CalculationDraft.model_validate({**row, "origem_calculo": row.get("origem_calculo", "processo")}) for row in rows]
            else:
                grouped = {}
                for row in read_table(content, filename):
                    process = row.get("numero_processo", "")
                    params = {key.removeprefix("parametros."): value for key, value in row.items() if key.startswith("parametros.") and value != ""}
                    current = grouped.setdefault(process, {"origem_calculo": "processo", "numero_processo": process, "parcelas": [], "parametros": params})
                    if current["parametros"] != params:
                        raise ServiceError("Há parâmetros diferentes para o mesmo processo na planilha.")
                    current["parcelas"].append(installment_from_row(row, "dano_material"))
                drafts = [CalculationDraft.model_validate(value) for value in grouped.values()]
            if not 1 <= len(drafts) <= 100 or len({draft.numero_processo for draft in drafts}) != len(drafts):
                raise ServiceError("Informe de 1 a 100 processos distintos.")
            for draft in drafts:
                draft.revisao_humana_confirmada = False
            return BatchImport(processos=drafts, erros=[])
        except (ValueError, KeyError, TypeError, UnicodeError) as exc:
            raise ServiceError("Lote inválido. Confira o modelo de importação e os campos obrigatórios; nenhum processo foi executado.") from exc

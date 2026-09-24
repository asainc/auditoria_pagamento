"""Tipos e contrato-base compartilhados entre os domínios da API."""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

ProcessId = Annotated[str, Field(pattern=r"^[0-9][0-9.\-]{0,39}$")]
CalculationIdentifier = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._/\-]{0,79}$")]
Money = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2, allow_inf_nan=False)]
Rate = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=8, allow_inf_nan=False)]
FlexibleAmount = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=8, allow_inf_nan=False)]
DamageType = Literal["dano_material", "dano_moral", "honorarios", "custas"]
EvidenceNature = Literal["pedido", "fato", "comando_decisorio", "fundamentacao", "classificacao_documental", "indeterminado"]
EvidenceEffect = Literal["informa", "mantem", "altera", "afasta", "majora", "reduz", "substitui", "nao_se_aplica"]
InterestType = Literal["sem_juros", "capitalizacao_simples", "capitalizacao_composta", "juros_moratorios_stj1368_lei_14905", "taxa_legal_12_aa_6_aa", "taxa_legal_diaria_selic_ipcae", "taxa_legal", "juros_moratorios_ctn_lei_14905"]
Periodicity = Literal["diaria", "mensal", "anual"]
Month = Literal["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
Scalar = str | int | float | bool | None


class Contract(BaseModel):
    """Base fechada para impedir campos desconhecidos e coerções silenciosas."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_default=True)

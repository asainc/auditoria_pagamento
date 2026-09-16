"""Interface de linha de comando do projeto."""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from judicial_calc.io.excel import salvar_resultado_excel
from judicial_calc.io.pdf import salvar_resultado_pdf
from judicial_calc.services.calculation_service import calcular_debitos


def _decimal_para_texto(obj: Any) -> Any:
    """Serializa ``Decimal`` para JSON.

    Entrada:
        ``obj``: objeto recebido por ``json.dumps``.

    Saída:
        ``str`` quando ``obj`` é ``Decimal``; caso contrário lança ``TypeError``.

    Exemplo:
        ``Decimal("10.00")`` vira ``"10.00"`` no JSON da CLI.
    """
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(type(obj).__name__)


def main() -> None:
    """Executa o cálculo a partir de um arquivo JSON.

    Entrada:
        Argumento ``--entrada-json`` com JSON contendo ``parcelas`` e ``params``;
        argumentos opcionais ``--saida-xlsx`` e ``--saida-pdf`` para exportação.

    Saída:
        Imprime JSON com ``memoria`` e ``resumo`` no terminal e, se informado,
        grava os arquivos solicitados em ``.xlsx`` e/ou ``.pdf``.

    Exemplo:
        ``judicial-calc --entrada-json entrada.json --saida-pdf memoria.pdf``.
    """
    parser = argparse.ArgumentParser(description="Calcula débitos judiciais com índices de correção e juros.")
    parser.add_argument("--entrada-json", required=True, help="Arquivo JSON com chaves parcelas e params.")
    parser.add_argument("--saida-xlsx", help="Opcional: caminho do Excel de saída.")
    parser.add_argument("--saida-pdf", help="Opcional: caminho do PDF da memória de cálculo.")
    args = parser.parse_args()

    payload = json.loads(Path(args.entrada_json).read_text(encoding="utf-8"))
    resultado = calcular_debitos(payload["parcelas"], **payload["params"])
    if args.saida_xlsx:
        salvar_resultado_excel(resultado, args.saida_xlsx)
    if args.saida_pdf:
        salvar_resultado_pdf(resultado, args.saida_pdf)
    print(json.dumps({
        "memoria": resultado.memoria.to_dict("records"),
        "resumo": resultado.resumo.to_dict("records"),
    }, ensure_ascii=False, indent=2, default=_decimal_para_texto))


if __name__ == "__main__":
    main()

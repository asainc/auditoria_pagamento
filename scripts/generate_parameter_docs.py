"""Gera a documentação do catálogo de parâmetros a partir da política central."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config" / "calculation_policy.json"
TARGET = ROOT / "docs" / "PARAMETROS.md"


def _display(value: object) -> str:
    """Converte valores da política para texto curto e estável em Markdown."""
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return "`true`" if value else "`false`"
    return f"`{value}`"


def main() -> None:
    """Grava padrões, obrigatoriedade, opções e grupos sem duplicação manual."""
    data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    manual = data["origins"]["manual"]["defaults"]
    process = data["origins"]["processo"]["defaults"]
    required = set(data["required_parameter_keys"])
    groups: dict[str, list[dict]] = defaultdict(list)
    for field in data["fields"]:
        groups[field["section"]].append(field)

    lines = [
        "# Catálogo de parâmetros",
        "",
        "> Arquivo gerado por `python scripts/generate_parameter_docs.py` a partir de `config/calculation_policy.json`. Não edite a tabela manualmente.",
        "",
        "## Fonte de verdade",
        "",
        "`config/calculation_policy.json` define chaves, rótulos, seções visuais, opções, campos obrigatórios e padrões por origem. O backend lê esse arquivo diretamente e o Angular consome um artefato TypeScript gerado pelo mesmo catálogo.",
        "",
        "## Padrões por origem",
        "",
        "| Campo | Cálculo manual | Processo real |",
        "| --- | --- | --- |",
    ]
    for key in sorted(set(manual) | set(process)):
        lines.append(f"| `{key}` | {_display(manual.get(key)) if key in manual else 'sem padrão'} | {_display(process.get(key)) if key in process else 'sem padrão'} |")
    lines.extend([
        "",
        "Os padrões completam somente campos ausentes. Um valor explicitamente informado pelo operador ou consolidado a partir dos documentos não é sobrescrito. Para processo real, a `OperationalPolicy` registra o uso de padrão em `ajustes_operacionais`, mantendo separado o que veio de documento e o que veio de política.",
        "",
        "## Dependências importantes",
        "",
        "- `capitalizacao_simples` e `capitalizacao_composta` exigem taxa e periodicidade do mesmo grupo de juros.",
        "- Prescrição habilitada exige anos e tipo de data de referência; quando o tipo não é `data_ultima_parcela`, a data de referência também é obrigatória.",
        "- Compensação habilitada exige tipo e valor.",
        "- Duplo índice habilitado exige índice, data inicial e data final para as duas faixas.",
        "- Valores monetários e taxas atravessam a API como texto decimal e são validados com `Decimal` no Python.",
        "",
    ])

    for section, fields in groups.items():
        lines.extend([
            f"## {section}",
            "",
            "| Chave | Rótulo | Tipo visual | Obrigatório base | Opções/observações |",
            "| --- | --- | --- | --- | --- |",
        ])
        for field in fields:
            options = field.get("options") or []
            option_text = ", ".join(str(option["value"]) for option in options if option.get("value") not in (None, ""))
            notes = field.get("help") or option_text or "—"
            lines.append(
                f"| `{field['key']}` | {field['label']} | `{field['type']}` | "
                f"{'sim' if field['key'] in required else 'não'} | {notes} |"
            )
        lines.append("")

    lines.extend([
        "## Manutenção do catálogo",
        "",
        "`config/calculation_policy.json` é o único ponto editável para metadados e defaults. Após qualquer edição autorizada, os artefatos derivados são regenerados por `generate_parameter_catalog.py` e `generate_parameter_docs.py` e validados pelas suítes Python e Angular.",
        "",
        "Critérios jurídicos ou regulatórios exigem validação do time jurídico/compliance/DPO quando aplicável; o catálogo técnico não substitui essa validação.",
    ])
    TARGET.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Catálogo documentado em {TARGET.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()

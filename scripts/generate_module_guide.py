"""Gera um guia simples com a responsabilidade de cada módulo do projeto.

O arquivo resultante é voltado a quem precisa localizar onde fazer uma mudança
sem conhecer toda a base de código. A descrição principal vem do comentário de
módulo quando ele existe; quando não existe, o gerador usa a responsabilidade da
pasta para não inventar uma regra de negócio.

Entrada:
    arquivos Python, TypeScript, configuração e prompts existentes no projeto.

Saída:
    ``docs/GUIA_MODULOS.md``.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "GUIA_MODULOS.md"


FOLDER_ROLES: tuple[tuple[str, str, str], ...] = (
    ("backend/contracts/", "Contrato da API", "JSON/Python já recebido pela API", "objeto tipado e validado"),
    ("backend/routers/", "Rota HTTP", "requisição HTTP validada", "chamada de serviço e resposta HTTP"),
    ("backend/services/", "Serviço de aplicação", "contratos e dependências injetadas", "resultado do caso de uso"),
    ("backend/repositories/", "Acesso a dados", "objetos do domínio e filtros", "registros persistidos ou consultados"),
    ("backend/persistence/", "Infraestrutura do SQLite", "configuração/transação", "conexão e estrutura de banco"),
    ("backend/domain/", "Modelo interno do backend", "valores validados", "estrutura de domínio"),
    ("backend/", "Núcleo do backend", "configuração/contratos", "serviços e API preparados"),
    ("src/judicial_calc/services/", "Regra do motor", "parcelas e parâmetros", "memória/resumo ou transformação financeira"),
    ("src/judicial_calc/indices/", "Correção monetária", "datas, índice e séries", "fator de correção"),
    ("src/judicial_calc/interest/", "Juros moratórios", "base, datas, taxa e série", "juros/fator"),
    ("src/judicial_calc/data_sources/drcalc/", "Atualização de índices", "fonte DrCalc e arquivos locais", "séries validadas/planilhas"),
    ("src/judicial_calc/data_sources/", "Fonte de dados do motor", "identificador/período", "tabela ou série"),
    ("src/judicial_calc/extraction/", "Leitura de séries externas", "série e período", "tabela normalizada"),
    ("src/judicial_calc/io/", "Entrada/saída do motor", "resultado/tabela", "arquivo ou estrutura exportada"),
    ("src/judicial_calc/core/", "Tipos e utilidades centrais", "valores básicos", "valor normalizado/tipo comum"),
    ("src/judicial_calc/", "Pacote do motor", "parcelas/parâmetros", "resultado determinístico"),
    ("scripts/", "Ferramenta de desenvolvimento", "arquivos/configuração do projeto", "validação, inicialização ou documento gerado"),
    ("frontend/src/app/core/", "Integração/estado do Angular", "estado da tela ou resposta HTTP", "estado atualizado/requisição"),
    ("frontend/src/app/", "Componente Angular", "estado e interação do usuário", "tela/eventos"),
)


def _clean(text: str | None) -> str:
    """Transforma um comentário longo em uma descrição curta de uma linha."""
    if not text:
        return "Responsabilidade definida pela pasta e pelo nome do módulo."
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first.replace("|", "\\|") or "Responsabilidade definida pela pasta e pelo nome do módulo."


def _python_description(path: Path) -> str:
    """Lê apenas a árvore sintática; o módulo não é importado nem executado."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return "Módulo Python; consulte a referência de código para detalhes."
    return _clean(ast.get_docstring(tree))


def _typescript_description(path: Path) -> str:
    """Extrai o primeiro comentário de documentação do arquivo TypeScript."""
    source = path.read_text(encoding="utf-8")
    match = re.search(r"/\*\*\s*(.*?)\s*\*/", source, flags=re.S)
    if not match:
        return "Módulo da interface Angular responsável pelo recurso indicado no nome do arquivo."
    return _clean(re.sub(r"\s+", " ", match.group(1)))


def _role(relative: str) -> tuple[str, str, str]:
    """Retorna papel, entrada típica e saída típica de acordo com a pasta."""
    for prefix, role, input_value, output_value in FOLDER_ROLES:
        if relative.startswith(prefix):
            return role, input_value, output_value
    return "Módulo de apoio", "dados do projeto", "resultado específico do módulo"


def _rows(paths: list[Path], description_reader) -> list[str]:
    """Monta linhas de tabela para uma lista ordenada de arquivos."""
    rows: list[str] = []
    for path in sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix()):
        relative = path.relative_to(ROOT).as_posix()
        role, input_value, output_value = _role(relative)
        description = description_reader(path)
        rows.append(f"| `{relative}` | {role} | {description} | {input_value} | {output_value} |")
    return rows


def generate() -> str:
    """Produz o Markdown completo de forma determinística."""
    python_paths = [
        path
        for base in (ROOT / "backend", ROOT / "src", ROOT / "scripts")
        for path in base.rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    ts_paths = list((ROOT / "frontend" / "src" / "app").rglob("*.ts"))

    lines = [
        "# Guia de módulos",
        "",
        "> Gerado por `scripts/generate_module_guide.py`. O objetivo é responder rapidamente: \"em qual arquivo devo mexer?\".",
        "",
        "As colunas **Entrada típica** e **Saída típica** descrevem a função da camada, não substituem as assinaturas exatas. Para tipos exatos de classes e funções, use `docs/REFERENCIA_CODIGO.md`.",
        "",
        "## Backend, motor e scripts Python",
        "",
        "| Módulo | Papel | Objetivo/escopo | Entrada típica | Saída típica |",
        "|---|---|---|---|---|",
    ]
    lines.extend(_rows(python_paths, _python_description))
    lines += [
        "",
        "## Frontend Angular",
        "",
        "| Módulo | Papel | Objetivo/escopo | Entrada típica | Saída típica |",
        "|---|---|---|---|---|",
    ]
    lines.extend(_rows(ts_paths, _typescript_description))

    lines += [
        "",
        "## Arquivos de configuração",
        "",
        "| Arquivo | Objetivo |",
        "|---|---|",
        "| `config/runtime.json` | Host, portas, workers e regras de recarga automática dos servidores locais. |",
        "| `config/app.settings.json` | Limites e valores operacionais não secretos do backend. |",
        "| `config/calculation_policy.json` | Catálogo central de parâmetros, opções, seções e padrões operacionais do cálculo. |",
        "| `config/extraction_tasks.json` | Limites de saída de cada tarefa de extração documental. |",
        "| `.env` | Valores específicos do ambiente e segredos; arquivo local que não deve ser versionado. |",
        "| `frontend/public/app-config.json` | Configuração pública lida pelo navegador; nunca deve conter segredos. |",
        "",
        "## Prompts",
        "",
        "| Arquivo | Escopo |",
        "|---|---|",
        "| `prompts/_base.md` | Regras comuns para todas as tarefas e contrato de evidência. |",
        "| `prompts/00_classificacao.md` | Classificação dos documentos e marcos relevantes. |",
        "| `prompts/01_parcelas.md` | Parcelas, danos e verbas monetárias. |",
        "| `prompts/02_correcao.md` | Critérios de atualização monetária. |",
        "| `prompts/03_moratorios.md` | Critérios de juros moratórios. |",
        "| `prompts/05_encargos.md` | Encargos, multas e honorários. |",
        "| `prompts/06_prescricao.md` | Informações documentais relacionadas à prescrição. |",
        "| `prompts/07_compensacao.md` | Critérios documentais de compensação. |",
        "| `prompts/08_duplo_indice.md` | Faixas e índices quando há dois critérios de atualização. |",
        "| `prompts/09_valor_dobrado.md` | Evidências de aplicação de valor em dobro. |",
        "",
        "## Regra para escolher o módulo correto",
        "",
        "Se a mudança altera **como calcular**, comece em `src/judicial_calc`. Se altera **como coordenar ou persistir**, comece em `backend`. Se altera **como mostrar ou coletar**, comece em `frontend`. Se altera **um valor ajustável sem mudar algoritmo**, procure `config`. Se altera **como a IA lê um assunto do documento**, procure o prompt correspondente.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    """Grava o guia na pasta de documentação e informa o caminho criado."""
    OUTPUT.write_text(generate(), encoding="utf-8")
    print(f"Guia de módulos gerado: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

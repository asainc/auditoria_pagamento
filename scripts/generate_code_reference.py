"""Gera a referência técnica do código a partir do próprio source tree.

A documentação de referência é derivada de assinaturas e docstrings para evitar
que uma lista manual de funções fique desatualizada em relação ao source. O gerador
não executa os módulos da aplicação e, portanto, não acessa rede, banco ou segredos.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "REFERENCIA_CODIGO.md"
PYTHON_ROOTS = (ROOT / "backend", ROOT / "src", ROOT / "scripts")
TYPESCRIPT_ROOT = ROOT / "frontend" / "src" / "app"


def _one_line(text: str | None) -> str:
    """Normaliza a primeira linha útil de uma docstring para o índice."""
    if not text:
        return "Sem descrição específica no código."
    return next((line.strip() for line in text.splitlines() if line.strip()), "Sem descrição específica no código.")


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Reconstrói uma assinatura legível sem importar o módulo analisado."""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    args = ast.unparse(node.args)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{prefix} {node.name}({args}){returns}"


def _parameter_summary(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Lista parâmetros e anotações sem executar o módulo analisado."""
    positional = [*node.args.posonlyargs, *node.args.args]
    values: list[str] = []
    for argument in positional:
        if argument.arg in {"self", "cls"}:
            continue
        annotation = ast.unparse(argument.annotation) if argument.annotation else "tipo não declarado"
        values.append(f"`{argument.arg}: {annotation}`")
    if node.args.vararg:
        annotation = ast.unparse(node.args.vararg.annotation) if node.args.vararg.annotation else "tipo não declarado"
        values.append(f"`*{node.args.vararg.arg}: {annotation}`")
    for argument in node.args.kwonlyargs:
        annotation = ast.unparse(argument.annotation) if argument.annotation else "tipo não declarado"
        values.append(f"`{argument.arg}: {annotation}`")
    if node.args.kwarg:
        annotation = ast.unparse(node.args.kwarg.annotation) if node.args.kwarg.annotation else "tipo não declarado"
        values.append(f"`**{node.args.kwarg.arg}: {annotation}`")
    return ", ".join(values) if values else "nenhuma entrada explícita"


def _return_summary(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Retorna a anotação de saída declarada ou informa quando ela não existe."""
    return f"`{ast.unparse(node.returns)}`" if node.returns else "tipo de saída não declarado"


def _class_attributes(node: ast.ClassDef) -> list[str]:
    """Extrai atributos declarados diretamente na classe para facilitar leitura do estado."""
    attributes: list[str] = []
    for child in node.body:
        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            annotation = ast.unparse(child.annotation)
            attributes.append(f"`{child.target.id}: {annotation}`")
        elif isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    attributes.append(f"`{target.id}: tipo inferido em execução`")
    return attributes


def _python_section(path: Path) -> list[str]:
    """Gera seção de um arquivo Python usando AST e docstrings reais."""
    relative = path.relative_to(ROOT).as_posix()
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = [f"## `{relative}`", "", _one_line(ast.get_docstring(tree)), ""]
    public_nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
    if not public_nodes:
        lines += ["Este módulo não expõe classes ou funções de nível superior.", ""]
        return lines
    for node in public_nodes:
        if isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(base) for base in node.bases)
            suffix = f"({bases})" if bases else ""
            lines += [f"### `class {node.name}{suffix}`", "", _one_line(ast.get_docstring(node)), ""]
            attributes = _class_attributes(node)
            if attributes:
                lines += ["**Atributos declarados:** " + ", ".join(attributes) + ".", ""]
            methods = [child for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if methods:
                lines += ["**Métodos:**", ""]
                for child in methods:
                    lines += [
                        f"- `{_signature(child)}` — {_one_line(ast.get_docstring(child))}",
                        f"  - Entrada: {_parameter_summary(child)}.",
                        f"  - Saída: {_return_summary(child)}.",
                    ]
            lines.append("")
        else:
            lines += [
                f"### `{_signature(node)}`",
                "",
                _one_line(ast.get_docstring(node)),
                "",
                f"**Entrada:** {_parameter_summary(node)}.",
                "",
                f"**Saída:** {_return_summary(node)}.",
                "",
            ]
    return lines


def _typescript_section(path: Path) -> list[str]:
    """Cria índice didático dos principais símbolos TypeScript sem compilar o frontend."""
    relative = path.relative_to(ROOT).as_posix()
    source = path.read_text(encoding="utf-8")
    header = re.search(r"/\*\*\s*(.*?)\s*\*/", source, flags=re.S)
    description = re.sub(r"\s+", " ", header.group(1)).strip() if header else "Módulo TypeScript da interface Angular."
    symbols = re.findall(r"export\s+(?:default\s+)?(?:class|interface|type|const|function)\s+([A-Za-z_$][\w$]*)", source)
    lines = [f"## `{relative}`", "", description, ""]
    if symbols:
        lines.append("Símbolos exportados: " + ", ".join(f"`{symbol}`" for symbol in dict.fromkeys(symbols)) + ".")
    else:
        lines.append("O arquivo não possui símbolo exportado detectável pelo índice estático.")
    lines.append("")
    return lines


def generate() -> str:
    """Monta a referência completa na mesma ordem em todas as execuções."""
    lines = [
        "# Referência do código",
        "",
        "> Arquivo gerado automaticamente por `scripts/generate_code_reference.py`.",
        "> As descrições vêm das docstrings/comentários do source; não edite este arquivo manualmente.",
        "",
        "## Como ler esta referência",
        "",
        "Use esta referência para localizar responsabilidades. Para entender a sequência de execução, consulte `FLUXO_CALCULO.md`; para contratos e valores padrão, consulte `PARAMETROS.md`.",
        "",
        "# Python",
        "",
    ]
    python_files: list[Path] = []
    for directory in PYTHON_ROOTS:
        python_files.extend(
            path for path in directory.rglob("*.py")
            if "__pycache__" not in path.parts and path.name != "generate_code_reference.py"
        )
    for path in sorted(set(python_files), key=lambda item: item.relative_to(ROOT).as_posix()):
        lines.extend(_python_section(path))
    lines += ["# Angular / TypeScript", ""]
    for path in sorted(TYPESCRIPT_ROOT.rglob("*.ts"), key=lambda item: item.relative_to(ROOT).as_posix()):
        lines.extend(_typescript_section(path))
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    """Escreve o artefato gerado em `docs/REFERENCIA_CODIGO.md`."""
    OUTPUT.write_text(generate(), encoding="utf-8")
    print(f"Referência gerada: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Inicialização mínima do pacote backend para execução corporativa sem virtualenv.

A aplicação usa layout ``src/`` para o motor financeiro. Em estações em que o
projeto não pode ser instalado em modo editável, o Python poderia resolver uma
cópia antiga de ``judicial_calc`` presente no perfil do usuário. A raiz ``src``
do próprio projeto é inserida na frente do caminho de importação antes de os
serviços do backend serem carregados.

Esta rotina não instala dependências, não altera variáveis globais do Windows e
não contém regra de negócio. Ela apenas torna determinística a origem do pacote
local durante esta execução.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_SRC = (_PROJECT_ROOT / "src").resolve()

if _PROJECT_SRC.is_dir():
    src_text = str(_PROJECT_SRC)
    # Remove uma ocorrência posterior para garantir precedência determinística.
    sys.path[:] = [item for item in sys.path if Path(item or ".").resolve() != _PROJECT_SRC]
    sys.path.insert(0, src_text)

"""Fixtures inteiramente sintéticas; rede e índices distribuídos não são alterados."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen.canvas import Canvas

from backend.config import Settings
from backend.principal import create_app


@pytest.fixture
def payload():
    """Este arquivo é gerado pelo mapper Angular em npm test."""
    return json.loads((Path(__file__).parent / "fixtures/angular_request.json").read_text())


@pytest.fixture
def client(tmp_path):
    """Cada teste ganha um SQLite e um diretório documental independentes."""
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        yield client


@pytest.fixture
def pdf_bytes():
    """PDF legível com valores fictícios permite testar hash, citação e exportação."""
    output = io.BytesIO()
    canvas = Canvas(output)
    canvas.drawString(50, 760, "DOCUMENTO SINTETICO - SEM DADOS REAIS")
    canvas.drawString(50, 735, "Parcela: 100.00. Data: 2025-01-01. Tipo: dano_material.")
    canvas.drawString(50, 710, "Correcao: sem_correcao. Multa: 2%.")
    canvas.save()
    return output.getvalue()

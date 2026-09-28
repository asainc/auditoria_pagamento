"""A aplicação distribui somente uma memória de cálculo em PDF."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_runtime_exposes_single_pdf_memory_generator():
    """A aplicação mantém somente a memória de cálculo como artefato PDF."""
    pdf_source = (ROOT / "src/judicial_calc/io/pdf.py").read_text(encoding="utf-8")
    public_api = (ROOT / "src/judicial_calc/__init__.py").read_text(encoding="utf-8")
    assert "salvar_resultado_pdf" in pdf_source + public_api

def test_new_execution_persists_only_standard_memory(client, payload):
    result = client.post("/api/calculos", json=payload)
    assert result.status_code == 200, result.text
    calculation_id = result.json()["registro"]["calculo_id"]
    execution_id = result.json()["execucao"]["execucao_id"]
    database = client.app.state.services.database.path
    import sqlite3
    with sqlite3.connect(database) as connection:
        kinds = [row[0] for row in connection.execute(
            "SELECT kind FROM calculation_artifacts WHERE execution_id=? ORDER BY kind",
            (execution_id,),
        ).fetchall()]
    assert kinds == ["memoria"]
    normal = client.get(f"/api/calculos/{calculation_id}/execucoes/{execution_id}/memoria-pdf")
    assert normal.status_code == 200
    assert normal.content.startswith(b"%PDF-")

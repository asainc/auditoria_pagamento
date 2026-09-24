"""A aplicação distribui somente uma memória de cálculo em PDF."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_no_auditable_pdf_generator_in_runtime_code():
    targets = [
        ROOT / "src/judicial_calc/io/pdf.py",
        ROOT / "src/judicial_calc/__init__.py",
        ROOT / "backend/services/engine.py",
        ROOT / "backend/services/calculation.py",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in targets)
    assert "salvar_resultado_pdf_auditavel" not in text
    assert "MEMÓRIA DE CÁLCULO AUDITÁVEL" not in text

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

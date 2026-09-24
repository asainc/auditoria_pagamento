"""Upload validado, persistente e organizado exclusivamente no backend."""
from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from backend.calculation_identity import display_process_number
from backend.config import Settings
from backend.errors import ServiceError
from backend.contracts.document import DocumentMetadata
from backend.repositories.audit_repository import AuditRepository
from backend.repositories.document_repository import DocumentRepository


class DocumentService:
    """Identifica o processo pelo nome exigido; conteúdo não altera a associação."""
    def __init__(self, settings: Settings, repository: DocumentRepository, audit_repository: AuditRepository):
        """Recebe dependências explicitamente para manter configuração e testes isolados."""
        self.settings = settings
        self.repository = repository
        self.audit_repository = audit_repository
        self.directory = settings.data_dir / "documents"
        self.directory.mkdir(parents=True, exist_ok=True)

    async def receive(self, files: list[UploadFile]) -> list[DocumentMetadata]:
        """Valida o lote completo antes de persistir; leitura limitada evita alocações ilimitadas."""
        if not 1 <= len(files) <= self.settings.max_upload_files:
            raise ServiceError("Quantidade de arquivos fora do limite configurado.")
        validated: list[tuple[DocumentMetadata, bytes]] = []
        for file in files:
            name = file.filename or ""
            match = re.fullmatch(r"([0-9][0-9.\-]{0,39})_([0-9]+)(?:_[^/\\]+)?\.pdf", name, re.IGNORECASE)
            if not match or Path(name).name != name or len(name) > 200:
                raise ServiceError("Nome inválido. Use numeroProcesso_sequencia.pdf; somente números, pontos e hífens no processo.")
            if file.content_type not in {"application/pdf", "application/octet-stream"}:
                raise ServiceError("Envie arquivos do tipo PDF.")
            content = await file.read(self.settings.max_upload_bytes + 1)
            if len(content) > self.settings.max_upload_bytes:
                raise ServiceError("PDF excede o tamanho máximo configurado.", 413)
            if not content.startswith(b"%PDF-"):
                raise ServiceError("O conteúdo do arquivo não é um PDF válido.")
            try:
                reader = PdfReader(io.BytesIO(content), strict=True)
                if reader.is_encrypted:
                    raise ServiceError("Remova a senha do PDF antes do envio.")
                pages = len(reader.pages)
                if not 1 <= pages <= 2000:
                    raise ServiceError("PDF deve conter entre 1 e 2.000 páginas.")
            except (PdfReadError, ValueError, OSError) as exc:
                raise ServiceError("PDF corrompido ou estrutura não suportada.") from exc
            document = DocumentMetadata(identificador=uuid4().hex, numero_processo=display_process_number(match.group(1)), nome=name, sha256=hashlib.sha256(content).hexdigest(), tamanho_bytes=len(content), paginas=pages, classificacao="a_classificar")
            validated.append((document, content))
        documents: list[DocumentMetadata] = []
        names: dict[tuple[str, str], str] = {}
        for document, _ in validated:
            for existing in self.repository.list_for_process(document.numero_processo):
                names[(existing.numero_processo, existing.nome)] = existing.sha256
        for document, _ in validated:
            key = (document.numero_processo, document.nome)
            if key in names and names[key] != document.sha256:
                raise ServiceError("Já existe documento com esse nome e conteúdo diferente. Use outro número de sequência para preservar as evidências.", 409)
            names[key] = document.sha256
        for document, content in validated:
            # O hash gerado internamente define o caminho; nomes enviados nunca viram caminhos.
            path = self.directory / (document.sha256 + ".pdf")
            if not path.exists():
                temporary = path.with_suffix("." + uuid4().hex + ".tmp")
                temporary.write_bytes(content)
                temporary.replace(path)
            documents.append(self.repository.add(document))
        self.audit_repository.append("upload_completed", {"files": len(documents), "bytes": sum(row.tamanho_bytes for row in documents)})
        return documents

    def path(self, identifier: str) -> tuple[Path, DocumentMetadata]:
        """Somente documento registrado pode ser obtido pelo identificador opaco."""
        document = self.repository.get(identifier)
        if document is None:
            raise ServiceError("Documento não encontrado.", 404)
        path = self.directory / (document.sha256 + ".pdf")
        if not path.is_file():
            raise ServiceError("Arquivo indisponível. Reenvie o documento.", 404)
        return path, document

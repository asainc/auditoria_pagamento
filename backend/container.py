"""Monta os objetos compartilhados pela API e controla o ciclo de vida deles.

A API não cria serviços dentro de cada rota. Este módulo constrói uma única
composição por instância FastAPI, conecta repositórios aos serviços adequados e
fecha recursos com threads quando a aplicação é encerrada.
"""
from __future__ import annotations

from fastapi import Request

from backend.config import Settings
from backend.persistence.schema import migrate
from backend.persistence.sqlite import SQLiteDatabase
from backend.repositories.ai_operations_repository import AiOperationsRepository
from backend.repositories.audit_repository import AuditRepository
from backend.repositories.calculation_repository import CalculationRepository
from backend.repositories.document_repository import DocumentRepository
from backend.repositories.extraction_repository import ExtractionRepository
from backend.repositories.index_repository import IndexRepository
from backend.repositories.quality_repository import QualityRepository
from backend.services.batches import BatchService
from backend.services.calculation import CalculationService
from backend.services.documents import DocumentService
from backend.services.engine import EngineFacade
from backend.services.extraction import ExtractionProvider, ExtractionService
from backend.services.imports import ImportService
from backend.services.indices import IndexService
from backend.services.quality_learning import QualityLearningService
from backend.services.revision_audit import RevisionAuditService


class Services:
    """Agrupa serviços e repositórios que pertencem à mesma execução da API.

    Entrada:
        ``settings``: configuração validada da aplicação.
        ``provider``: provedor opcional de extração usado principalmente em testes.
        Quando omitido, a integração corporativa configurada no projeto é usada.

    Saída:
        A instância expõe atributos como ``documents``, ``calculations``,
        ``extractions`` e ``indices``. As rotas recebem esse mesmo objeto por
        injeção, sem recriar conexões ou filas a cada requisição.
    """

    def __init__(self, settings: Settings, provider: ExtractionProvider | None = None) -> None:
        """Cria banco, repositórios e serviços em uma ordem explícita.

        A ordem é importante: primeiro o esquema do banco é validado; depois os
        repositórios são criados; por fim os serviços recebem somente os
        repositórios de que realmente precisam.
        """
        self.settings = settings

        # Uma única fábrica de conexões aponta para o diretório configurado. Cada
        # operação de repositório abre sua própria conexão curta e controlada.
        self.database = SQLiteDatabase(settings.data_dir)
        migrate(self.database)

        # Repositórios: cada objeto cuida de um conjunto específico de tabelas.
        self.document_repository = DocumentRepository(self.database)
        self.extraction_repository = ExtractionRepository(self.database, self.document_repository)
        self.audit_repository = AuditRepository(self.database)
        self.calculation_repository = CalculationRepository(self.database)
        self.index_repository = IndexRepository(self.database)
        self.ai_operations_repository = AiOperationsRepository(self.database)
        self.quality_repository = QualityRepository(self.database)

        # Trabalhos de extração marcados como em execução podem ter sido
        # interrompidos por desligamento da aplicação. A recuperação acontece
        # antes de aceitar novas requisições.
        self.extraction_repository.recover_jobs()

        # Serviços: esta camada contém a coordenação das regras e não conhece HTTP.
        self.documents = DocumentService(settings, self.document_repository, self.audit_repository)
        self.engine = EngineFacade(settings)
        self.calculations = CalculationService(
            self.calculation_repository,
            self.audit_repository,
            self.engine,
        )
        self.batches = BatchService(self.calculations)

        default_provider = ExtractionProvider(
            settings,
            ai_repository=self.ai_operations_repository,
            quality_repository=self.quality_repository,
        )
        self.extractions = ExtractionService(
            settings,
            self.extraction_repository,
            self.document_repository,
            self.audit_repository,
            self.documents,
            provider or default_provider,
        )
        self.indices = IndexService(
            settings,
            self.index_repository,
            self.audit_repository,
            self.engine,
        )
        self.imports = ImportService()
        self.revision_audit = RevisionAuditService(
            self.audit_repository,
            self.extraction_repository,
        )
        self.quality = QualityLearningService(
            settings,
            self.quality_repository,
            self.extraction_repository,
            self.document_repository,
        )

    def close(self) -> None:
        """Encerra recursos que mantêm threads abertas.

        Entrada:
            Nenhuma.

        Saída:
            Nenhuma. Depois desta chamada, a instância não deve receber novas
            requisições. O banco usa conexões curtas e não exige fechamento global.
        """
        self.extractions.close()
        self.indices.close()


def services(request: Request) -> Services:
    """Obtém a composição de serviços pertencente à aplicação FastAPI atual.

    Entrada:
        ``request``: requisição HTTP entregue pelo FastAPI.

    Saída:
        ``Services`` criado durante a inicialização da aplicação. As rotas usam
        esta função como dependência para receber serviços testáveis e reutilizáveis.
    """
    return request.app.state.services

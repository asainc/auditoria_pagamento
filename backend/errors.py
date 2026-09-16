"""Falhas de domínio chegam às rotas sem expor arquivos ou dados internos."""


class ServiceError(Exception):
    """Erro esperado, com mensagem operacional segura e código HTTP explícito."""
    def __init__(self, message: str, status_code: int = 422):
        """Recebe dependências explicitamente para manter configuração e testes isolados."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code

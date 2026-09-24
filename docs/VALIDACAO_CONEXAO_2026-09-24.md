# Validação da correção de conexão — 24/09/2026

Comando executado:
`python -m pytest --noconftest tests/test_bradesco_bridge.py tests/test_settings.py tests/test_text_connection.py -q`

Resultado: 13 testes aprovados. Transporte HTTP interceptado; nenhuma chamada
corporativa real. O conftest global foi desativado porque carrega componentes
não usados nestes testes. A suíte completa e o frontend não foram executados.
Não se afirma resolução do incidente sem reprodução no ambiente corporativo.

Versões do ambiente de teste (o lock original do projeto foi preservado):
- pytest: 9.1.1
- pydantic: 2.13.5
- requests: 2.34.2
- starlette: 1.7.0

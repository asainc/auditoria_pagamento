# Validação final — 24/09/2026

Esta entrega consolida a refatoração estrutural solicitada sem alterar deliberadamente as fórmulas financeiras estabilizadas do motor.

## Verificações executadas

- `pytest -q`: **161 testes aprovados**.
- `python scripts/validate_architecture.py`: **arquitetura aprovada**; Angular, FastAPI e motor determinístico permanecem separados.
- `npm test` em `frontend/`: **43 testes aprovados e 4 ignorados**. O comando executou `tsc -p tsconfig.tests.json` antes dos testes Node.
- `npm run build` de produção **não foi executado**, pois `frontend/node_modules` não está presente no pacote de trabalho. A compilação completa deve ser repetida após instalar as dependências homologadas no Nexus corporativo.
- artefatos OpenAPI/TypeScript, catálogo/parâmetros, referência de código e manifesto SHA-256 do motor foram regenerados após a refatoração.

## Escopo validado

- repositórios separados e composição explícita dos serviços;
- migração de bases SQLite legadas;
- armazenamento normalizado em versão, execução e artefato;
- constraints e imutabilidade física de versões/execuções/artefatos;
- criação de nova versão somente para novo estado funcional e criação de execução para retry idêntico;
- concorrência otimista por `versao_base`;
- API canônica `/api/v2`, aliases legados ocultos do OpenAPI e `X-API-Version: 2.0.0`;
- envelope de erros estruturados com `code`, `fields`, `retryable` e `request_id`;
- parâmetros internos normalizados, incluindo distinção entre percentual e valor fixo;
- separação dos contratos de cálculo por domínio;
- DrCalc dividido em modelos, parsing, cliente, workbook, lifecycle e serviço;
- tela de Histórico decomposta em componentes;
- paginação/lazy loading de execuções e versões;
- comparação/diff completo de versões;
- normalização de identidade processual e filtros avançados.

## Limites da validação

A suíte não comprova conectividade real com infraestrutura corporativa nem atualidade da fonte externa de índices. O build Angular de produção não foi executado sem dependências corporativas instaladas. Testes de carga e concorrência distribuída devem preceder produção. Regras jurídicas, retenção de documentos/snapshots e políticas de acesso continuam sujeitas à validação das áreas responsáveis. Nenhuma credencial real, dado de produção ou PDF real foi usado.

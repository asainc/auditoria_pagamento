# Guia de módulos

> Gerado por `scripts/generate_module_guide.py`. O objetivo é responder rapidamente: "em qual arquivo devo mexer?".

As colunas **Entrada típica** e **Saída típica** descrevem a função da camada, não substituem as assinaturas exatas. Para tipos exatos de classes e funções, use `docs/REFERENCIA_CODIGO.md`.

## Backend, motor e scripts Python

| Módulo | Papel | Objetivo/escopo | Entrada típica | Saída típica |
|---|---|---|---|---|
| `backend/__init__.py` | Núcleo do backend | Inicialização mínima do pacote backend para execução corporativa sem virtualenv. | configuração/contratos | serviços e API preparados |
| `backend/access.py` | Núcleo do backend | Publicação protegida por gateway autenticado; local usa apenas loopback. | configuração/contratos | serviços e API preparados |
| `backend/calculation_identity.py` | Núcleo do backend | Normalização determinística das identidades usadas no histórico de cálculos. | configuração/contratos | serviços e API preparados |
| `backend/calculation_policy.py` | Núcleo do backend | Catálogo e padrões centrais do cálculo. | configuração/contratos | serviços e API preparados |
| `backend/config.py` | Núcleo do backend | Configuração validada; erros não são substituídos silenciosamente por padrões. | configuração/contratos | serviços e API preparados |
| `backend/container.py` | Núcleo do backend | Monta os objetos compartilhados pela API e controla o ciclo de vida deles. | configuração/contratos | serviços e API preparados |
| `backend/contracts/__init__.py` | Contrato da API | Exportações explícitas dos contratos por domínio. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/contracts/audit.py` | Contrato da API | Contratos da trilha de revisão humana. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/contracts/base.py` | Contrato da API | Tipos e contrato-base compartilhados entre os domínios da API. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/contracts/batch.py` | Contrato da API | Contratos de execução e importação em lote. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/contracts/calculation.py` | Contrato da API | Exportações centrais dos contratos relacionados ao domínio de cálculo. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/contracts/calculation_history.py` | Contrato da API | Contratos de versionamento, execução, artefatos e histórico. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/contracts/calculation_input.py` | Contrato da API | Contratos de entrada de cálculo e preparação de parcelas. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/contracts/calculation_output.py` | Contrato da API | Contratos de saída do motor e recomendações operacionais. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/contracts/calculation_parameters.py` | Contrato da API | Contratos dos parâmetros de cálculo, separados do transporte HTTP. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/contracts/document.py` | Contrato da API | Contratos do domínio documental. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/contracts/extraction.py` | Contrato da API | Contratos de extração, evidência e política de parâmetros. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/contracts/index.py` | Contrato da API | Contratos do catálogo e atualização de índices. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/contracts/quality.py` | Contrato da API | Contratos de aprendizado supervisionado e qualidade da extração. | JSON/Python já recebido pela API | objeto tipado e validado |
| `backend/domain/__init__.py` | Modelo interno do backend | Modelos de domínio independentes dos contratos HTTP. | valores validados | estrutura de domínio |
| `backend/domain/calculation_parameters.py` | Modelo interno do backend | Modelo de domínio dos parâmetros jurídico-financeiros. | valores validados | estrutura de domínio |
| `backend/errors.py` | Núcleo do backend | Erros públicos estruturados, estáveis e sem conteúdo sensível. | configuração/contratos | serviços e API preparados |
| `backend/models.py` | Núcleo do backend | Ponto central de importação dos contratos usados pelo backend e pelos testes. | configuração/contratos | serviços e API preparados |
| `backend/persistence/__init__.py` | Infraestrutura do SQLite | Infraestrutura de banco local: conexão SQLite e criação/migração do esquema. | configuração/transação | conexão e estrutura de banco |
| `backend/persistence/schema.py` | Infraestrutura do SQLite | Schema e migrações idempotentes do banco de negócio. | configuração/transação | conexão e estrutura de banco |
| `backend/persistence/sqlite.py` | Infraestrutura do SQLite | Infraestrutura SQLite compartilhada pelos repositórios especializados. | configuração/transação | conexão e estrutura de banco |
| `backend/principal.py` | Núcleo do backend | Única inicialização FastAPI; não hospeda o frontend da aplicação. | configuração/contratos | serviços e API preparados |
| `backend/repositories/__init__.py` | Acesso a dados | Repositórios que leem e gravam cada grupo de dados persistidos pela aplicação. | objetos do domínio e filtros | registros persistidos ou consultados |
| `backend/repositories/ai_operations_repository.py` | Acesso a dados | Persistência de telemetria FinOps e cache determinístico de respostas estruturadas. | objetos do domínio e filtros | registros persistidos ou consultados |
| `backend/repositories/audit_repository.py` | Acesso a dados | Persistência de auditoria técnica e revisão humana. | objetos do domínio e filtros | registros persistidos ou consultados |
| `backend/repositories/calculation_repository.py` | Acesso a dados | Persistência do agregado Cálculo → Versão → Execução → Artefato. | objetos do domínio e filtros | registros persistidos ou consultados |
| `backend/repositories/document_repository.py` | Acesso a dados | Persistência exclusiva de documentos e processos. | objetos do domínio e filtros | registros persistidos ou consultados |
| `backend/repositories/extraction_repository.py` | Acesso a dados | Persistência exclusiva do fluxo e fila de extração. | objetos do domínio e filtros | registros persistidos ou consultados |
| `backend/repositories/index_repository.py` | Acesso a dados | Persistência mínima do estado do atualizador de índices. | objetos do domínio e filtros | registros persistidos ou consultados |
| `backend/repositories/quality_repository.py` | Acesso a dados | Persistência da supervisão humana, curadoria e datasets versionados. | objetos do domínio e filtros | registros persistidos ou consultados |
| `backend/routers/__init__.py` | Rota HTTP | Rotas apenas recebem, validam e delegam aos serviços. | requisição HTTP validada | chamada de serviço e resposta HTTP |
| `backend/routers/audit.py` | Rota HTTP | Endpoints de auditoria da revisão humana de parâmetros. | requisição HTTP validada | chamada de serviço e resposta HTTP |
| `backend/routers/batches.py` | Rota HTTP | Lotes reutilizam o mesmo serviço de cálculo e a confirmação humana. | requisição HTTP validada | chamada de serviço e resposta HTTP |
| `backend/routers/calculations.py` | Rota HTTP | Cálculo, histórico versionado, execuções e exportações compartilham contratos validados. | requisição HTTP validada | chamada de serviço e resposta HTTP |
| `backend/routers/documents.py` | Rota HTTP | Documentos chegam por multipart e são obtidos por identificador opaco. | requisição HTTP validada | chamada de serviço e resposta HTTP |
| `backend/routers/extractions.py` | Rota HTTP | Consulta e repetição da extração não dependem de estado do navegador. | requisição HTTP validada | chamada de serviço e resposta HTTP |
| `backend/routers/indices.py` | Rota HTTP | Catálogo e atualização de índices passam exclusivamente pela API. | requisição HTTP validada | chamada de serviço e resposta HTTP |
| `backend/routers/quality.py` | Rota HTTP | Endpoints de qualidade supervisionada e FinOps da extração. | requisição HTTP validada | chamada de serviço e resposta HTTP |
| `backend/services/__init__.py` | Serviço de aplicação | Serviços de aplicação independentes dos componentes Angular. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/ai_usage.py` | Serviço de aplicação | Telemetria FinOps: separa métricas reais, estimativas locais e custo configurado. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/batches.py` | Serviço de aplicação | Orquestração de lotes reaproveita o cálculo unitário, sem duplicar o motor. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/bradesco_bridge.py` | Serviço de aplicação | Integração mínima com ``gpt_bradesco.py`` para geração de texto. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/calculation.py` | Serviço de aplicação | Orquestra cálculo, versionamento, exportação e auditoria fora das rotas HTTP. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/chronology.py` | Serviço de aplicação | Consolidação determinística da evolução documental de um processo. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/documents.py` | Serviço de aplicação | Upload validado, persistente e organizado exclusivamente no backend. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/engine.py` | Serviço de aplicação | Única fachada do cálculo: adapta tipos sem reproduzir fórmulas. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/engine_guidance.py` | Serviço de aplicação | Transforma erros estruturados do motor em orientação operacional segura. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/evidence_validator.py` | Serviço de aplicação | Validação de evidências contra o texto local e consolidação cronológica. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/extraction.py` | Serviço de aplicação | Orquestração de extração documental com leitura local, seleção de páginas e fila durável. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/extraction_jobs.py` | Serviço de aplicação | Fila durável de extração baseada no repositório de negócio. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/extraction_types.py` | Serviço de aplicação | Tipos internos da extração; separados da orquestração para evitar acoplamento. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/extraction_wire.py` | Serviço de aplicação | Contrato externo tolerante a omissões seguras; limites permanecem no contrato interno. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/imports.py` | Serviço de aplicação | Importadores rejeitam linhas inválidas em vez de alterar o lote silenciosamente. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/indices.py` | Serviço de aplicação | Gestão das séries delega ao atualizador existente, com exclusão mútua. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/operational_policy.py` | Serviço de aplicação | Aplica critérios operacionais rastreáveis antes da revisão humana do cálculo. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/pdf_text_extractor.py` | Serviço de aplicação | Leitura local de PDFs com score explícito de qualidade da camada textual. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/prompt_context.py` | Serviço de aplicação | Monta contexto enxuto e específico por tarefa para reduzir tokens repetidos. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/prompt_executor.py` | Serviço de aplicação | Execução de prompts corporativos com roteamento, cache, aprendizado e FinOps. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/prompt_router.py` | Serviço de aplicação | Seleção determinística de páginas para reduzir payload sem usar outro modelo. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/quality_learning.py` | Serviço de aplicação | Transforma revisão humana em supervisão estruturada, curada e versionável. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/revision_audit.py` | Serviço de aplicação | Persistência e enriquecimento da trilha de revisão humana dos parâmetros. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/services/structured_output.py` | Serviço de aplicação | Normalização determinística da saída do text_generator antes de qualquer reparo por IA. | contratos e dependências injetadas | resultado do caso de uso |
| `backend/version.py` | Núcleo do backend | Versões oficiais da aplicação e do contrato HTTP. | configuração/contratos | serviços e API preparados |
| `scripts/check-python-environment.py` | Ferramenta de desenvolvimento | Valida o runtime Python antes de iniciar a API. | arquivos/configuração do projeto | validação, inicialização ou documento gerado |
| `scripts/evaluate_extraction.py` | Ferramenta de desenvolvimento | Compara predições de extração com um conjunto de referência revisado. | arquivos/configuração do projeto | validação, inicialização ou documento gerado |
| `scripts/generate_code_reference.py` | Ferramenta de desenvolvimento | Gera a referência técnica do código a partir do próprio source tree. | arquivos/configuração do projeto | validação, inicialização ou documento gerado |
| `scripts/generate_contracts.py` | Ferramenta de desenvolvimento | Gera interfaces TypeScript do OpenAPI; a API é a fonte única dos contratos. | arquivos/configuração do projeto | validação, inicialização ou documento gerado |
| `scripts/generate_engine_manifest.py` | Ferramenta de desenvolvimento | Gera o manifesto SHA-256 dos arquivos Python do motor determinístico. | arquivos/configuração do projeto | validação, inicialização ou documento gerado |
| `scripts/generate_module_guide.py` | Ferramenta de desenvolvimento | Gera um guia simples com a responsabilidade de cada módulo do projeto. | arquivos/configuração do projeto | validação, inicialização ou documento gerado |
| `scripts/generate_parameter_catalog.py` | Ferramenta de desenvolvimento | Gera o catálogo TypeScript a partir da política central. | arquivos/configuração do projeto | validação, inicialização ou documento gerado |
| `scripts/generate_parameter_docs.py` | Ferramenta de desenvolvimento | Gera a documentação do catálogo de parâmetros a partir da política central. | arquivos/configuração do projeto | validação, inicialização ou documento gerado |
| `scripts/run_backend.py` | Ferramenta de desenvolvimento | Inicializa o backend usando uma única configuração de execução. | arquivos/configuração do projeto | validação, inicialização ou documento gerado |
| `scripts/test_text_generator_connection.py` | Ferramenta de desenvolvimento | Diagnóstico seguro da conexão com o gerador corporativo. | arquivos/configuração do projeto | validação, inicialização ou documento gerado |
| `scripts/validate_architecture.py` | Ferramenta de desenvolvimento | Valida fronteiras arquiteturais, dependências proibidas e versões fixadas do frontend. | arquivos/configuração do projeto | validação, inicialização ou documento gerado |
| `src/judicial_calc/__init__.py` | Pacote do motor | Interface pública do motor de cálculo judicial. | parcelas/parâmetros | resultado determinístico |
| `src/judicial_calc/cli.py` | Pacote do motor | Interface de linha de comando do projeto. | parcelas/parâmetros | resultado determinístico |
| `src/judicial_calc/core/__init__.py` | Tipos e utilidades centrais | Tipos, validações e utilidades básicas usadas por todas as regras do motor. | valores básicos | valor normalizado/tipo comum |
| `src/judicial_calc/core/constants.py` | Tipos e utilidades centrais | Constantes compartilhadas por regras de datas e consulta de séries oficiais. | valores básicos | valor normalizado/tipo comum |
| `src/judicial_calc/core/dates.py` | Tipos e utilidades centrais | Funções utilitárias para datas e competências mensais. | valores básicos | valor normalizado/tipo comum |
| `src/judicial_calc/core/errors.py` | Tipos e utilidades centrais | Exceções estruturadas usadas na fronteira do motor de cálculo. | valores básicos | valor normalizado/tipo comum |
| `src/judicial_calc/core/models.py` | Tipos e utilidades centrais | Modelos Pydantic versionados para entrada/auditoria do cálculo judicial. | valores básicos | valor normalizado/tipo comum |
| `src/judicial_calc/core/numbers.py` | Tipos e utilidades centrais | Funções utilitárias para conversão e arredondamento numérico. | valores básicos | valor normalizado/tipo comum |
| `src/judicial_calc/core/tables.py` | Tipos e utilidades centrais | Normalização de tabelas de índices. | valores básicos | valor normalizado/tipo comum |
| `src/judicial_calc/core/types.py` | Tipos e utilidades centrais | Tipos públicos retornados pela biblioteca. | valores básicos | valor normalizado/tipo comum |
| `src/judicial_calc/data/__init__.py` | Pacote do motor | Pacote de recursos contendo as planilhas de índices distribuídas com o motor. | parcelas/parâmetros | resultado determinístico |
| `src/judicial_calc/data_sources/__init__.py` | Fonte de dados do motor | Acesso controlado às fontes de índices e às planilhas locais do motor. | identificador/período | tabela ou série |
| `src/judicial_calc/data_sources/drcalc/__init__.py` | Atualização de índices | Interface pública do atualizador de índices obtidos do DrCalc. | fonte DrCalc e arquivos locais | séries validadas/planilhas |
| `src/judicial_calc/data_sources/drcalc/client.py` | Atualização de índices | Cliente HTTP e parser de formulários/tabelas históricas do DrCalc. | fonte DrCalc e arquivos locais | séries validadas/planilhas |
| `src/judicial_calc/data_sources/drcalc/lifecycle.py` | Atualização de índices | Estado local, backup, restauração, cache e exclusão mútua do atualizador. | fonte DrCalc e arquivos locais | séries validadas/planilhas |
| `src/judicial_calc/data_sources/drcalc/models.py` | Atualização de índices | Tipos e constantes compartilhados pela integração DrCalc. | fonte DrCalc e arquivos locais | séries validadas/planilhas |
| `src/judicial_calc/data_sources/drcalc/parsing.py` | Atualização de índices | Normalização de texto, números, períodos e URLs da fonte DrCalc. | fonte DrCalc e arquivos locais | séries validadas/planilhas |
| `src/judicial_calc/data_sources/drcalc/service.py` | Atualização de índices | Orquestra download, staging, validação, promoção e fallback dos índices. | fonte DrCalc e arquivos locais | séries validadas/planilhas |
| `src/judicial_calc/data_sources/drcalc/workbook.py` | Atualização de índices | Seleção, mesclagem e validação das planilhas de índices. | fonte DrCalc e arquivos locais | séries validadas/planilhas |
| `src/judicial_calc/data_sources/http_client.py` | Fonte de dados do motor | Sessão HTTP compartilhada pelas consultas públicas do motor. | identificador/período | tabela ou série |
| `src/judicial_calc/data_sources/local_excel.py` | Fonte de dados do motor | Leitura das planilhas locais usadas nos cálculos judiciais. | identificador/período | tabela ou série |
| `src/judicial_calc/extraction/__init__.py` | Leitura de séries externas | Contratos e extratores usados para obter séries externas em formato tabular. | série e período | tabela normalizada |
| `src/judicial_calc/extraction/base.py` | Leitura de séries externas | Contratos simples para extratores de tabelas mensais. | série e período | tabela normalizada |
| `src/judicial_calc/extraction/sgs.py` | Leitura de séries externas | Download de séries mensais e diárias do SGS/Bacen. | série e período | tabela normalizada |
| `src/judicial_calc/indices/__init__.py` | Correção monetária | Estratégias de correção monetária e resolução das séries de índices. | datas, índice e séries | fator de correção |
| `src/judicial_calc/indices/base.py` | Correção monetária | Estratégias base para correção monetária. | datas, índice e séries | fator de correção |
| `src/judicial_calc/indices/local_excel.py` | Correção monetária | Estratégias de correção monetária baseadas na planilha mensal local. | datas, índice e séries | fator de correção |
| `src/judicial_calc/indices/registry.py` | Correção monetária | Registro central das estratégias de correção monetária. | datas, índice e séries | fator de correção |
| `src/judicial_calc/indices/sgs_percentage.py` | Correção monetária | Índices de correção obtidos de séries percentuais mensais SGS/Bacen. | datas, índice e séries | fator de correção |
| `src/judicial_calc/interest/__init__.py` | Juros moratórios | Regras de juros moratórios, separadas por forma de cálculo e fonte de taxa. | base, datas, taxa e série | juros/fator |
| `src/judicial_calc/interest/daily_rates.py` | Juros moratórios | Juros moratórios por tabelas diárias locais. | base, datas, taxa e série | juros/fator |
| `src/judicial_calc/interest/fixed.py` | Juros moratórios | Cálculo de juros fixos simples ou compostos. | base, datas, taxa e série | juros/fator |
| `src/judicial_calc/interest/service.py` | Juros moratórios | Seleciona a forma de calcular juros moratórios a partir do tipo configurado. | base, datas, taxa e série | juros/fator |
| `src/judicial_calc/interest/taxa_legal.py` | Juros moratórios | Juros legais especiais usados para replicar opções do critério de referência. | base, datas, taxa e série | juros/fator |
| `src/judicial_calc/io/__init__.py` | Entrada/saída do motor | Entradas e saídas do motor, como geração de Excel e memória PDF. | resultado/tabela | arquivo ou estrutura exportada |
| `src/judicial_calc/io/excel.py` | Entrada/saída do motor | Exportação do resultado do cálculo para planilha Excel auditável. | resultado/tabela | arquivo ou estrutura exportada |
| `src/judicial_calc/io/pdf.py` | Entrada/saída do motor | Geração da memória de cálculo em PDF. | resultado/tabela | arquivo ou estrutura exportada |
| `src/judicial_calc/services/__init__.py` | Regra do motor | Serviços que coordenam etapas do motor financeiro sem expor detalhes internos. | parcelas e parâmetros | memória/resumo ou transformação financeira |
| `src/judicial_calc/services/calculation_adjustments.py` | Regra do motor | Compensação aplicada ao resultado final do cálculo. | parcelas e parâmetros | memória/resumo ou transformação financeira |
| `src/judicial_calc/services/calculation_parameters.py` | Regra do motor | Normalização e validação dos parâmetros públicos do motor de cálculo. | parcelas e parâmetros | memória/resumo ou transformação financeira |
| `src/judicial_calc/services/calculation_penalties.py` | Regra do motor | Multas, rateios monetários e art. 523 do CPC usados pelo motor. | parcelas e parâmetros | memória/resumo ou transformação financeira |
| `src/judicial_calc/services/calculation_prescription.py` | Regra do motor | Filtro de parcelas alcançadas pela configuração de prescrição. | parcelas e parâmetros | memória/resumo ou transformação financeira |
| `src/judicial_calc/services/calculation_service.py` | Regra do motor | Orquestração do cálculo de atualização de débitos judiciais. | parcelas e parâmetros | memória/resumo ou transformação financeira |
| `src/judicial_calc/services/calculation_summary.py` | Regra do motor | Composição do resumo final e dos honorários do cálculo. | parcelas e parâmetros | memória/resumo ou transformação financeira |

## Frontend Angular

| Módulo | Papel | Objetivo/escopo | Entrada típica | Saída típica |
|---|---|---|---|---|
| `frontend/src/app/app.component.ts` | Componente Angular | Shell Angular único com navegação entre aplicações e módulos operacionais. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/app.routes.ts` | Componente Angular | Cada aplicação fica agrupada para permitir expansão futura do sistema. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/batches/batch-page.component.ts` | Componente Angular | Lotes mostram a prévia completa antes de solicitar confirmação e executar. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/calculation/calculation-page.component.ts` | Componente Angular | Página compõe componentes coesos e concentra apenas a organização visual. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/calculation/evidence-info.component.ts` | Componente Angular | Exibe a origem documental e as considerações de extração sem ocupar uma aba própria. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/calculation/extraction-log.component.ts` | Componente Angular | Log visual reúne a origem automática e a trilha imutável de revisão humana. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/calculation/installment-batch.component.ts` | Componente Angular | Criação de linhas recorrentes organiza datas; não implementa cálculo jurídico. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/calculation/installment-dates.ts` | Componente Angular | Meses/anos mantêm o dia original, limitado ao último dia válido de cada mês. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/calculation/installment-editor.component.ts` | Componente Angular | Edição direta de parcelas com rolagem própria, sem apagar outros tipos de verba. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/calculation/parameter-fields.ts` | Componente Angular | Gerado de config/calculation_policy.json. Não editar manualmente. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/calculation/parameter-panel.component.ts` | Componente Angular | Organiza os critérios por tipo de dano e mantém parcelas no primeiro bloco. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/calculation/pdf-viewer.component.ts` | Componente Angular | O visualizador consome somente Blob da API, com cancelamento e descarte de URLs. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/calculation/process-selector.component.ts` | Componente Angular | A seleção é vazia no início e mantém a busca sob controle do usuário. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/calculation/result-calculation-summary.component.ts` | Componente Angular | Resumo operacional do cálculo exibido somente na guia Resultado. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/calculation/result-panel.component.ts` | Componente Angular | Resultado e memória exibem apenas valores calculados pelo backend. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/core/api-errors.ts` | Integração/estado do Angular | Mensagens comuns distinguem o servidor da aplicação do provedor de extração. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/batch-api.service.ts` | Integração/estado do Angular | Importação e execução são ações distintas e explicitamente tipadas. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/calculation-api.service.ts` | Integração/estado do Angular | A interface envia parâmetros; nenhuma matemática jurídica é executada aqui. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/calculation-mapper.ts` | Integração/estado do Angular | Único adaptador de formulário camelCase para os contratos snake_case. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/config.ts` | Integração/estado do Angular | Configuração lida antes de iniciar Angular, sem recompilar por ambiente. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/connection-api.service.ts` | Integração/estado do Angular | Disponibilidade é consultada antes do upload, sem enviar a chave ao navegador. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/contracts.ts` | Integração/estado do Angular | Gerado de docs/openapi.json. Atualize por scripts/generate_contracts.py. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/document-api.service.ts` | Integração/estado do Angular | Serviço HTTP do domínio documental. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/extraction-api.service.ts` | Integração/estado do Angular | Extrações continuam no servidor mesmo quando o usuário troca de processo. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/index-api.service.ts` | Integração/estado do Angular | Catálogo único é consultado na API. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/notifications.ts` | Integração/estado do Angular | Notificações podem ser fechadas e não carregam HTML do backend. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/quality-api.service.ts` | Integração/estado do Angular | Feedback supervisionado, dataset e FinOps da extração. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/result-presentation.ts` | Integração/estado do Angular | Rótulos de apresentação: os valores são sempre os retornados pelo motor. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/revision-audit-api.service.ts` | Integração/estado do Angular | Trilha de revisão humana; nenhum cálculo é executado neste serviço. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/workspace-audit.store.ts` | Integração/estado do Angular | Trilha de revisão humana isolada do restante da área de trabalho. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/workspace-calculation.store.ts` | Integração/estado do Angular | Revisão, cálculo e exportação ficam separados da navegação e extração. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/workspace-extraction.store.ts` | Integração/estado do Angular | Upload, polling e aplicação de extração vivem isolados do restante da UI. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/workspace-state.store.ts` | Integração/estado do Angular | Estado puro da área de trabalho; não executa HTTP nem regras de negócio remotas. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/core/workspace.store.ts` | Integração/estado do Angular | Fachada fina da área de trabalho; estado, extração, cálculo e auditoria vivem em stores específicos. | estado da tela ou resposta HTTP | estado atualizado/requisição |
| `frontend/src/app/history/calculation-history-page.component.ts` | Componente Angular | Página orquestradora do histórico; filtros, diff, comparação e execuções são componentes independentes. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/history/history-diff.component.ts` | Componente Angular | Exibe diferenças entre versões sem conhecer carregamento, paginação ou estado da página. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/history/history-executions.component.ts` | Componente Angular | Execuções técnicas paginadas e carregadas apenas quando a versão é expandida. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/history/history-filters.component.ts` | Componente Angular | Filtros do histórico isolados da paginação e da consulta HTTP. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/history/history-version-comparator.component.ts` | Componente Angular | Comparador isolado: carrega somente quando o usuário solicita a comparação. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/indices/indices-page.component.ts` | Componente Angular | Estado de atualização é consultado no servidor; não há sucesso presumido. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/quality/quality-page.component.ts` | Componente Angular | Painel operacional de qualidade supervisionada e FinOps, sem expor documento bruto. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/shared/notifications.component.ts` | Componente Angular | Região acessível de avisos com fechamento individual. | estado e interação do usuário | tela/eventos |
| `frontend/src/app/templates/application-template-page.component.ts` | Componente Angular | Página template reutilizável para aplicações futuras do sistema. | estado e interação do usuário | tela/eventos |

## Arquivos de configuração

| Arquivo | Objetivo |
|---|---|
| `config/runtime.json` | Host, portas, workers e regras de recarga automática dos servidores locais. |
| `config/app.settings.json` | Limites e valores operacionais não secretos do backend. |
| `config/calculation_policy.json` | Catálogo central de parâmetros, opções, seções e padrões operacionais do cálculo. |
| `config/extraction_tasks.json` | Limites de saída de cada tarefa de extração documental. |
| `.env` | Valores específicos do ambiente e segredos; arquivo local que não deve ser versionado. |
| `frontend/public/app-config.json` | Configuração pública lida pelo navegador; nunca deve conter segredos. |

## Prompts

| Arquivo | Escopo |
|---|---|
| `prompts/_base.md` | Regras comuns para todas as tarefas e contrato de evidência. |
| `prompts/00_classificacao.md` | Classificação dos documentos e marcos relevantes. |
| `prompts/01_parcelas.md` | Parcelas, danos e verbas monetárias. |
| `prompts/02_correcao.md` | Critérios de atualização monetária. |
| `prompts/03_moratorios.md` | Critérios de juros moratórios. |
| `prompts/05_encargos.md` | Encargos, multas e honorários. |
| `prompts/06_prescricao.md` | Informações documentais relacionadas à prescrição. |
| `prompts/07_compensacao.md` | Critérios documentais de compensação. |
| `prompts/08_duplo_indice.md` | Faixas e índices quando há dois critérios de atualização. |
| `prompts/09_valor_dobrado.md` | Evidências de aplicação de valor em dobro. |

## Regra para escolher o módulo correto

Se a mudança altera **como calcular**, comece em `src/judicial_calc`. Se altera **como coordenar ou persistir**, comece em `backend`. Se altera **como mostrar ou coletar**, comece em `frontend`. Se altera **um valor ajustável sem mudar algoritmo**, procure `config`. Se altera **como a IA lê um assunto do documento**, procure o prompt correspondente.

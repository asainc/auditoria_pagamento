## 2026-09-24 — Correção dos warnings Angular NG8107

- Removido o optional chaining redundante de `diff.campos` e `diff.parcelas` em `history-diff.component.ts`; `diff` é um `@Input` obrigatório e não admite `null`/`undefined` nesse ponto do template.
- Mantido `?? []` apenas nos arrays opcionais `campos` e `parcelas`, preservando compatibilidade com o contrato atual.
- Incluído teste de regressão para impedir a reintrodução de `diff?.campos` e `diff?.parcelas`.
- Nenhuma regra de cálculo, persistência, versionamento ou comportamento da tela Histórico foi alterada.


## 2026-09-24 — Histórico sem PDF auditável e edição de qualquer versão

- Removido o botão **PDF auditável** dos cards de versão e das execuções técnicas na tela Histórico; a interface oferece somente a Memória PDF.
- Qualquer versão de um cálculo `ativo` pode ser aberta como base de edição, e não apenas a versão atual.
- A versão histórica selecionada permanece registrada em `versao_base`; se a edição produzir um novo estado funcional, a nova versão é criada no topo da sequência e preserva a origem histórica no relacionamento de versão.
- O controle de concorrência passou a separar `versao_base` de `versao_atual_esperada`: editar V1 quando o cálculo está em V4 é permitido, mas a gravação falha se outra pessoa criar V5 enquanto a edição estiver aberta.
- O detalhe de versão informa `versao_atual`, permitindo que o Angular carregue o token de concorrência no momento da abertura do snapshot histórico.
- Validação desta revisão: **164 testes Python aprovados**, arquitetura aprovada e **46 testes frontend aprovados + 4 ignorados** após compilação TypeScript da suíte.

## 2026-09-24 — Resultado simplificado e PDF único
- Removida a geração do PDF auditável; novas execuções persistem somente a Memória PDF.
- A guia Resultado agora exibe Memória PDF, Histórico e o card compacto da versão do cálculo.
- O antigo banner de versão na guia Resultado foi substituído por um resumo de Dano Material/Dano Moral com indexador, períodos de correção/juros e regra de juros.
- A tela Histórico não teve sua estrutura visual alterada nesta entrega; artefatos auditáveis antigos permanecem legíveis por compatibilidade.
# Changelog

## 2026-09-24 — Refatoração estrutural: persistência, contratos, API e histórico

- `backend/repository.py` tornou-se somente uma fachada retrocompatível; SQL e responsabilidades foram separados em `DocumentRepository`, `ExtractionRepository`, `AuditRepository`, `CalculationRepository` e `IndexRepository`, com composição explícita em `backend/container.py`.
- Persistência de cálculo foi normalizada em `calculation_versions` (estado funcional imutável), `calculation_executions` (resultado técnico de cada execução) e `calculation_artifacts` (memórias PDF com SHA-256, tamanho e MIME).
- O schema passou a aplicar constraints/índices/triggers para identidade única do cálculo, hash de negócio único por cálculo, estados/origens válidos, hashes SHA-256 e imutabilidade de versões, execuções e artefatos. A migração de bases antigas move snapshots embutidos para a estrutura normalizada sem recalcular o passado.
- A API canônica passou a ser `/api/v2`; `/api` e `/api/v1` permanecem como aliases de compatibilidade ocultos do OpenAPI. `X-API-Version`, health check e OpenAPI usam o contrato `2.0.0`; a aplicação está na versão `2.1.0`.
- Erros públicos agora possuem estrutura estável (`code`, `message`, `fields`, `retryable`, `request_id`), mantendo aliases antigos apenas durante compatibilidade.
- Contratos de cálculo foram divididos em parâmetros, entrada, saída e histórico. `backend/models.py` e `backend/contracts/calculation.py` permanecem como fachadas de compatibilidade.
- Parâmetros foram agrupados por responsabilidade no contrato e convertidos para um modelo de domínio aninhado; regras de valor diferenciam explicitamente percentual de valor monetário fixo sem mudar o payload legado do motor.
- O antigo `drcalc_updater.py` monolítico virou fachada; implementação foi dividida em `drcalc/models.py`, `parsing.py`, `client.py`, `workbook.py`, `lifecycle.py` e `service.py`.
- A tela de Histórico foi decomposta em filtros, diff, comparador e execuções. Execuções são carregadas sob demanda e paginadas no backend/frontend.
- Validação desta revisão: **161 testes Python aprovados**; arquitetura aprovada; frontend com **43 testes aprovados e 4 ignorados**, após compilação da suíte TypeScript de testes. O build Angular de produção não foi executado porque `frontend/node_modules` não está presente nesta entrega.

## 2026-09-24 — Multa fixa e ajustes de navegação/typografia

- Multa comum passa a aceitar `percentual` ou `fixo`, com campo canônico `multa_valor` e seletor `multa_tipo`, em paridade com a experiência de honorários.
- Requisições e snapshots legados com `multa_percentual` continuam aceitos e são normalizados para `multa_valor`.
- Multa fixa é aplicada uma única vez no cálculo e rateada apenas para fins de memória auditável, preservando exatamente o total informado e evitando multiplicação pelo número de parcelas.
- Extração especializada de encargos passa a distinguir multa percentual de multa em valor fixo sem converter uma modalidade na outra.
- `Execução em lote` e `Índices` foram removidos somente do menu superior; as rotas permanecem disponíveis para acesso técnico direto.
- A fonte de `Conferência do cálculo` foi alterada para a mesma família usada em `Auditoria de Pagamentos`, sem mudar tamanho, peso, espaçamento ou demais estilos do título.
- Validação desta revisão: **156 testes Python aprovados** e **43 testes frontend aprovados, 4 ignorados** após compilação da suíte TypeScript isolada. O build Angular completo requer `node_modules` corporativo instalado.

## 2026-09-24 — Histórico avançado, concorrência e separação versão/execução

- Número do processo passa a ser normalizado para uma identidade somente com dígitos; a máscara CNJ é reaplicada para exibição quando houver 20 dígitos.
- Implementado hash canônico do estado de negócio (parâmetros, parcelas e `honorarios_sobre_danos_morais`) para impedir versões duplicadas.
- Controle de concorrência combina transação SQLite `BEGIN IMMEDIATE` e `versao_base` como trava otimista; uma edição baseada em versão desatualizada retorna conflito em vez de criar ramificação silenciosa.
- Versões de negócio e execuções técnicas foram separadas. Recalcular sem mudança funcional reutiliza a versão e cria uma nova execução auditável.
- Cada versão persiste diff estruturado completo dos parâmetros e parcelas em relação à base.
- Incluído comparador entre quaisquer duas versões do mesmo cálculo, com diferença do total e diff completo.
- Histórico principal passou a ser paginado no backend e não transporta mais todas as versões.
- Versões e execuções são carregadas por lazy loading na interface.
- Adicionados estados `ativo`, `arquivado` e `cancelado`; arquivar/cancelar preserva dados e bloqueia novas execuções até reativação.
- Filtros avançados: busca, origem, estado, índice, criador, intervalo de atualização, ordenação e tamanho de página.
- Migração SQLite adiciona identidade normalizada, estado, hash de negócio, diff e tabela de execuções sem descartar versões anteriores; versões legadas recebem uma execução técnica sintética correspondente ao snapshot original.
- A interface permite consultar as execuções de cada versão e baixar a memória específica da execução.
- Validação automatizada desta revisão: **154 testes Python aprovados**. Testes frontend independentes de build: **40 aprovados e 4 ignorados**; o build Angular de produção exige as dependências corporativas instaladas.

## 2026-09-24 — Salvamento automático e versionamento por alteração de conteúdo

- Todo cálculo concluído, inclusive manual, passa a ser salvo automaticamente no histórico.
- Cálculo manual agora exige `identificador_calculo`, informado pelo usuário na interface antes da execução.
- O mesmo número de processo ou identificador manual reutiliza o mesmo `calculo_id`.
- Nova versão é criada somente quando parâmetros de cálculo ou parcelas mudam; retries sem alteração reutilizam a versão existente.
- `honorarios_sobre_danos_morais` é tratado como parâmetro versionável por alterar o comportamento do motor.
- Ao reutilizar uma versão sem alterações, a API devolve o snapshot histórico canônico para manter resultado, metadados e PDFs coerentes com a versão apresentada.
- A tela Histórico passou a exibir processos e cálculos manuais; processos permanecem ordenados pelo número e manuais pelo identificador.
- A migração SQLite adiciona `origin` e `identifier` a `calculation_records` sem descartar cadastros existentes.
- Validação automatizada desta revisão: 147 testes Python aprovados e 34 testes frontend aprovados, com 4 testes frontend ignorados por dependerem de artefatos corporativos locais.


## 2026-09-24 — Cadastro e versionamento de cálculos por processo

- Todo cálculo concluído de um processo passa a ser cadastrado automaticamente em `calculation_records`.
- O mesmo processo reutiliza o mesmo `calculo_id`; alterações futuras criam versões sequenciais e imutáveis.
- Cada versão preserva request, resultado, memória normal/auditável em PDF, hashes técnicos, versão base e campos alterados.
- Requisições tecnicamente idênticas à versão de referência não criam duplicatas.
- Incluídos endpoints para listar histórico, reabrir uma versão e baixar os PDFs congelados sem recalcular o passado.
- Criada tela Angular **Histórico**, ordenada pelo número do processo, com expansão das versões e ação **Abrir e editar**.
- Ao reabrir uma versão, o usuário precisa confirmar novamente a revisão; o próximo cálculo fica vinculado ao mesmo cadastro.
- O resultado atual exibe a versão cadastrada e oferece acesso direto ao histórico.
- Validação automatizada desta entrega: 143 testes Python aprovados e 33 testes frontend aprovados, com 4 testes frontend ignorados por dependerem de artefatos corporativos locais.


## 2026-09-24 — Cobertura real dos índices e competência automática segura

- Removidos os intervalos de disponibilidade escritos manualmente no backend; o catálogo agora lê a primeira e a última competência não vazia de cada coluna de `taxas_mensais.xlsx`.
- O contrato de `/api/indices` passou a informar `competencia_inicial`, `competencia_final`, `competencia_maxima_atualizacao`, modo de acumulação e disponibilidade da série.
- Índices conhecidos sem série instalada permanecem identificáveis, porém são apresentados como indisponíveis e ficam desabilitados no seletor do Angular.
- Para índices de variação mensal, a competência de atualização M exige a taxa de M-1; para números-índice, M precisa existir na própria série.
- A competência automática agora é limitada ao maior mês suportado pelo índice selecionado, sem estimar competências ausentes.
- Erros de cobertura passaram a informar índice, competência necessária, última competência disponível e maior competência de atualização suportada.
- O atualizador do DrCalc diferencia consulta bem-sucedida com nova competência de consulta sem avanço de cobertura. O estado `sem_novidade` evita informar atualização quando nenhuma série avançou.
- Em falha durante a substituição dos três arquivos de índices, o backend tenta restaurar integralmente o backup criado antes da troca, evitando versões parciais misturadas.
- O Angular exibe a cobertura real e a competência máxima de atualização do índice selecionado.


## 2026-09-24 — TLS corporativo via repositório nativo do SO

- Corrigido o cliente HTTPS para usar a cadeia de confiança nativa do sistema operacional quando `BRADESCO_CA_BUNDLE` estiver vazio.
- No Windows, a integração passa a aproveitar as CAs corporativas instaladas no Windows Certificate Store, sem desabilitar verificação TLS.
- Mantido suporte a bundle PEM explícito para ambientes que exigem CA dedicada.
- Adicionado diagnóstico `tls_origem_confianca` ao script `scripts/test_text_generator_connection.py`.
- Mensagens de falha TLS agora distinguem store do sistema de bundle corporativo inválido/incompleto.
- O motor de cálculo e os prompts de extração não foram alterados.


## 2026-09-24 — Diagnóstico da geração de texto corporativa

- Corrigida a classificação de falhas do `text_generator` que antes podiam aparecer apenas como `bradesco_indisponivel`.
- Credencial ausente agora informa de forma explícita a necessidade de `BRADESCO_AUTHORIZATION_TOKEN` ou `BRADESCO_IDENTIFICADOR` + `BRADESCO_SENHA`.
- Respostas incompatíveis do gateway (`JSON` inválido ou ausência de `response.output_text`) agora possuem código operacional próprio.
- Adicionado `scripts/test_text_generator_connection.py`, que envia somente texto sintético e não lê PDFs.
- Atualizado `.env.example` para documentar corretamente a autenticação exigida pelo `gpt_bradesco.py` distribuído.
- Validação local: 129 testes aprovados; nenhuma chamada real ao ambiente corporativo foi executada.

## 2.0.0 — 2026-09-24

### Corrigido

- migração automática de bases SQLite legadas para o contrato atual da trilha de revisão, sem descartar a tabela original;
- cálculo manual voltou a reproduzir a ordem real da interface: auditoria de parâmetro → confirmação → `/api/calculos`;
- execução corporativa sem virtualenv passa a priorizar o `judicial_calc` da própria pasta `src`;
- falhas de importação do motor e persistência da trilha de revisão retornam erro operacional sanitizado em vez de HTTP 500 genérico.

### Alterado

- restituição em dobro passou a aceitar multiplicador explícito por parcela de dano material, com a flag global somente como fallback;
- extração foi decomposta em leitura PyMuPDF, roteamento de páginas, execução de prompts, normalização estrutural e validação de evidências;
- chamadas ao `text_generator` recebem contexto selecionado deterministicamente por tarefa;
- PDFs sem camada textual utilizável são bloqueados antes da chamada ao serviço corporativo;
- reparo por IA só ocorre após normalização estrutural determinística local;
- jobs de extração passaram a usar fila persistente com lease, retentativas e recuperação após reinício;
- observabilidade técnica passou a registrar métricas estruturais sem persistir conteúdo documental;
- estado Angular foi separado em stores de estado, extração, cálculo e auditoria;
- revisão humana navega para página e trecho de evidência;
- configurações mortas do gerador de texto foram removidas.

### Não incluído

- benchmark real da extração, excluído deste marco a pedido do solicitante.

### Governança

O responsável técnico e a aprovação institucional devem ser registrados pelo processo corporativo de merge/release. Regras jurídicas e de retenção continuam sujeitas à validação das áreas responsáveis.

## 2026-09-24 — Conexão text_generator

- Corrigida propagação de ambiente, CA, timeout e URLs configuradas no .env.
- Preservado contrato mínimo para módulos corporativos legados.
- Diferenciados erros de TLS, timeout e rede com mensagens sanitizadas.
- Incluídos testes de transporte simulado e instruções de diagnóstico no README.

## 2026-09-24 — Índices ausentes no seletor

- Corrigida a verificação do frontend que rejeitava o backend 2.0.0.
- Isolados os resultados do carregamento de processos e índices.
- Incluídos estado de carregamento e tentativa manual no painel de parâmetros.
- Validação: quatro testes de serviços TypeScript isolados e 30 testes Python
  de catálogo/conexão e integração de cálculo aprovados. Sem teste em navegador
  ou build Angular completo nesta revisão.

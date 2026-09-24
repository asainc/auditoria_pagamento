# Decisões arquiteturais vigentes

| Decisão | Justificativa |
| --- | --- |
| Angular → REST → FastAPI → motor Python | Mantém apresentação, aplicação e fórmulas desacopladas. |
| `origem_calculo` explícita (`manual`/`processo`) | Evita valor sentinela escondido em `numero_processo` e torna o contrato autoexplicativo. |
| `numero_processo=null` no modo manual | Separa teste sintético de processo documental real. |
| `config/calculation_policy.json` como fonte única de parâmetros/defaults | Evita divergência entre backend, frontend e documentação. |
| Catálogo Angular e documentação de parâmetros gerados | Reduz duplicação manual e risco de drift. |
| Evidência documental separada de ajuste operacional | Permite identificar se um valor veio de documento ou de política. |
| Prompt base + prompts especializados | Centraliza regras universais sem perder precisão por domínio. |
| LLM classifica `natureza` e `efeito`; Python consolida | Mantém decisão de composição cronológica em código testável e auditável. |
| Recência documental não resolve conflito sozinha | Um documento posterior pode apenas citar ou manter decisão anterior. |
| Conflitos não representáveis permanecem para revisão humana | Evita inferência silenciosa em cenário ambíguo. |
| Processo real sem tipos de juros usa `taxa_legal_12_aa_6_aa` | Política operacional determinística quando a documentação é omissa; exige validação jurídica para mudança. |
| Manual sem tipos de juros usa `sem_juros` | Evita encargo implícito em cenário de teste. |
| Art. 523 ausente usa `nao_aplicar` | Encargo não é incluído por silêncio documental. |
| `honorarios_tipo` não possui default | Não inventa natureza percentual/fixa sem evidência. |
| Alterações humanas são eventos imutáveis | Permite trilha completa, não apenas comparação do estado final. |
| Identidade técnica é pseudonimizada fora do ambiente local | Reduz exposição em trilha operacional; política de retenção depende da implantação. |
| `CalculationValidationError` carrega código + campos | Remove regex sobre texto de exceção e orienta campo sem ecoar valor. |
| Motor dividido por responsabilidades coesas | Parâmetros, prescrição, encargos, ajustes e resumo ficam em módulos separados; `calculation_service.py` apenas orquestra sem alterar fórmulas. |
| Golden master verifica estabilidade numérica do motor | Os cenários de referência tornam qualquer divergência de resultado explícita nos testes. |
| Extração de IA não fica dentro de `judicial_calc` | O pacote do motor permanece determinístico e independente do provedor de LLM. |
| `Decimal` no Python e texto decimal no transporte | Evita arredondamento binário indesejado. |
| Pydantic com campos extras proibidos | Erros de integração falham explicitamente. |
| Revisão humana obrigatória antes do cálculo | A IA produz sugestão, não decisão final. |
| Logs HTTP não armazenam payload | Reduz exposição de conteúdo processual e dados pessoais. |
| Hashes de entrada, política, motor e índices acompanham o resultado | Permite relacionar a saída à entrada aceita, à política vigente e aos artefatos de cálculo. |

| Schema de parâmetros reduzido por tarefa de extração | Evita repetir o contrato inteiro em dez chamadas e reduz tokens sem remover os campos relevantes da especialidade. |
| Limites de saída por tarefa em `config/extraction_tasks.json` | Evita reservar saída excessiva e deixa o tuning auditável sem alterar código. |
| Telemetria da integração corporativa registra chamadas e duração | O contrato atual do gerador corporativo não expõe contagem de tokens nem faturamento; esses campos permanecem indisponíveis em vez de serem estimados. |
| PyMuPDF precede qualquer prompt de extração | PDFs textuais são lidos localmente por página e somente o texto extraído, com documento e página, entra nos prompts especializados. PDFs sem camada textual são sinalizados para revisão em vez de gerar conteúdo por inferência. |
| `text_generator` é o único executor de prompts | Centraliza parâmetros, autenticação, tratamento de erro e auditoria da geração de texto. |
| Seções de parâmetros usam cartões independentes e cabeçalho destacado quando abertas | Mantém o bloco ativo identificável durante a rolagem sem alterar a identidade visual da aplicação. |
| Categorias do DrCalc são descobertas pela navegação da fonte, com IDs apenas como fallback | Evita quebrar a atualização quando o site altera identificadores de categoria. |
| Séries do DrCalc são obtidas pela submissão do formulário histórico real | O valor do seletor de indexador não é tratado como URL por suposição; período, categoria, defaults e método GET/POST são reproduzidos conforme a página publicada. |
| Variação percentual e número-índice são tratados como métricas distintas | Evita gravar um percentual mensal em coluna acumulada ou um número-índice como taxa decimal. Quando a unidade não pode ser inferida com segurança, a coluna acumulada é preservada. |
| Parser histórico aceita formatos longos e matrizes por ano/mês | Aumenta a resiliência a tabelas ASP antigas sem depender de um único layout HTML. |
| Estado da atualização usa `DrCalcUpdateResult.success` como fonte de verdade | Evita falso negativo causado por inferência baseada em texto de mensagem ou no campo `executed`. |
| Eventos financeiros deixam de integrar o contrato de cálculo | O fluxo específico de depósitos/pagamentos/levantamentos foi removido da aplicação e do motor para reduzir ambiguidade e manter apenas os ajustes explicitamente suportados. |
| Valor em dobro é resolvido por parcela de dano material | `multiplicador=1|2` explícito na parcela prevalece; `valor_dobrado_flag` permanece como fallback/atalho global. Dano moral, honorários e custas permanecem em 1x. |
| Tabelas de log têm viewport mínimo com rolagem nos dois eixos | Mantém pelo menos cinco linhas visíveis e permite inspecionar colunas largas sem comprimir o conteúdo. |

Regras que expressem interpretação jurídica, sucessão de decisões, política de encargos ou retenção de dados devem ser validadas pelas áreas responsáveis antes de uso institucional.


## Dependências npm — 16/09/2026

- **Decisão:** utilizar somente distribuições oficiais e versões confirmadas no repositório corporativo, sem forks ou pacotes fictícios.
- **Dependências do frontend/Nexus:** baseline Node.js `22.12.0`, npm `10.9.0` e Angular `21.2.19`; versões transitivas explicitamente compatibilizadas com a disponibilidade informada no Nexus (`rollup 4.60.1`, `readdirp 4.1.2`, `postcss 8.5.25`) e binding oficial Windows do Rollup na mesma versão.
- **Instalação corporativa:** os `.tgz` obtidos pelo fluxo autorizado podem ser validados e carregados no cache local sem transformar o projeto em uma distribuição baseada em `file:`.
- **Limite:** disponibilidade técnica no Nexus não equivale a homologação de licença, vulnerabilidade ou política interna.



## 2026-09-24 — consolidação técnica da extração e do cálculo

- **Motivo:** reduzir acoplamento, chamadas desnecessárias ao `text_generator`, perda de trabalho em reinícios e ambiguidade da restituição em dobro.
- **Decisões:** o valor em dobro aceita `multiplicador` por parcela; a flag global permanece somente como fallback/atalho; jobs de extração são persistidos com lease/retry; contexto de IA é selecionado deterministicamente por tarefa; saídas estruturais são normalizadas localmente antes de eventual reparo por IA; a revisão humana navega para a página/trecho de evidência.
- **Validação técnica:** suíte automatizada, golden masters do motor, contratos gerados e validação arquitetural.
- **Benchmark:** benchmark real da extração foi explicitamente excluído deste marco a pedido do solicitante.
- **Responsável técnico:** deve ser preenchido no repositório corporativo pelo responsável pela aprovação/merge desta versão; o artefato gerado não presume identidade ou aprovação institucional.

## 2026-09-24 — Compatibilidade de execução manual sem virtualenv e migração SQLite

- O pacote `backend` prioriza explicitamente `<raiz>/src` no `sys.path` para que estações corporativas sem instalação editável carreguem o `judicial_calc` pertencente ao próprio projeto, e não uma cópia antiga do perfil do usuário.
- `Repository` migra automaticamente versões antigas de `parameter_changes`; a tabela original é preservada como `parameter_changes_legacy_vN` antes da criação do contrato atual.
- Falhas de persistência da trilha de revisão são retornadas como erro operacional 503 sanitizado, em vez de HTTP 500 genérico.
- O fluxo de regressão cobre a mesma ordem da UI: registrar alteração manual, confirmar revisão e executar `/api/v2/calculos` sem número de processo.

## 2026-09-24 — Confiança TLS nativa do sistema operacional

Responsável pela alteração: assistente de engenharia; validação corporativa pendente.

- Quando `BRADESCO_CA_BUNDLE` estiver vazio, usar `ssl.create_default_context()` e
  um `HTTPAdapter` próprio para preservar o repositório de certificados confiáveis
  do sistema operacional em vez de forçar apenas o bundle do `certifi`.
- No Windows corporativo, isso permite que a cadeia TLS utilize as CAs instaladas nos
  stores confiáveis `ROOT/CA`, inclusive CAs de proxy/inspeção HTTPS autorizadas.
- Quando `BRADESCO_CA_BUNDLE` estiver preenchido, usar exclusivamente o bundle PEM
  informado, permitindo uma configuração explícita e auditável.
- Manter `CERT_REQUIRED` e verificação de hostname sempre ativos. A solução não usa
  `verify=False` e não reduz a segurança do canal.
- A sessão HTTP é mantida por thread e reconstruída quando o caminho/conteúdo do
  bundle muda; alterações no store do SO exigem reinício do backend.

## 2026-09-24 — Correção de configuração do text_generator

Responsável pela alteração: assistente de engenharia; validação corporativa pendente.

- Aplicar configure_iagen mesmo sem credenciais em Settings: ambiente e CA são
  necessários também quando a autenticação vem de variáveis do processo.
- Encaminhar timeout e URLs de identidade/texto do .env ao módulo distribuído,
  mediante CONNECTION_CONFIG_VERSION=1. Preservar os seis parâmetros da chamada
  de geração para compatibilidade com módulos legados.
- Aceitar BRADESCO_AMBIENTE e BRADESCO_TIMEOUT como aliases. Na mesma camada,
  BRADESCO_IAGEN_AMBIENTE e BRADESCO_TIMEOUT_SECONDS têm precedência;
  variáveis do processo continuam prevalecendo sobre .env.
- Classificar causas encadeadas de TLS, timeout e rede sem propagar mensagens
  externas. Manter validação TLS ativa e não alterar rotas ou payloads sem
  documentação corporativa confirmada.

## 2026-09-24 — Recuperação do catálogo de índices

Responsável pela alteração: assistente de engenharia.

- Alinhar o health check Angular ao backend 2.0.0, mantendo rejeição de versões
  incompatíveis. A divergência anterior impedia a chamada ao catálogo.
- Usar Promise.allSettled para não perder índices recebidos quando processos
  falharem. Uma inicialização parcial continua permitindo nova tentativa.
- Mostrar carregamento/indisponibilidade junto aos parâmetros e desabilitar
  seletores dinâmicos vazios. Nenhum índice ou taxa é inventado no frontend.
- Preservar o header X-API-Version e a rota legada /api/v1 existentes; corrigir
  apenas a comparação com versao_api do health check.
- Testes: `node --test tests/index-loading.test.cjs` (na pasta frontend, com
  TypeScript instalado): 4 aprovados. `python -m pytest
  tests/test_index_catalog_connection.py tests/test_calculation_integration.py -q`:
  30 aprovados. Não executados build Angular completo nem validação no navegador.

## 2026-09-24 — Diagnóstico explícito de autenticação do text_generator

Responsável pela alteração: assistente de engenharia; validação corporativa real pendente.

- O erro público deixa de agrupar credencial ausente e envelope inválido como indisponibilidade genérica.
- A exceção corporativa transporta somente um código técnico sanitizado; conteúdo da resposta, prompt, PDFs e segredos permanecem fora dos logs e da UI.
- O teste de conectividade usa mensagem sintética e existe separadamente do fluxo de documentos para reduzir risco operacional durante suporte.
- A suíte automatizada valida o contrato local, mas a disponibilidade real do deployment, credenciais e rede precisa ser confirmada no ambiente corporativo.

## 2026-09-24 — Cadastro automático e versionamento por conteúdo revisável

- **Decisão:** todo cálculo concluído é cadastrado automaticamente. Processo real usa o número do processo como identificador canônico; cálculo manual exige um identificador informado pelo usuário.
- **Motivo:** garantir rastreabilidade também para cálculos manuais e evitar que o usuário tenha de acionar uma etapa separada de “salvar”.
- **Critério de nova versão:** nova versão é criada somente quando parâmetros de cálculo ou parcelas mudam em relação à versão de referência. `honorarios_sobre_danos_morais` é considerado parâmetro porque altera a execução do motor.
- **Idempotência:** repetir o cálculo sem modificar parâmetros nem parcelas reutiliza a versão existente. Mudanças de metadados técnicos, política, motor ou snapshot de índices, isoladamente, não geram nova versão.
- **Coerência do snapshot (decisão posteriormente evoluída):** a primeira implementação devolvia o snapshot persistido quando a versão era reutilizada. A decisão posterior de separar versão de negócio e execução técnica substitui esse comportamento: a versão continua imutável, enquanto o resultado/PDF da reexecução recebe um `execucao_id` próprio.
- **Imutabilidade:** request, resultado e memória PDF permanecem congelados por execução. Downloads históricos não recalculam o passado.
- **Relação entre versões:** `versao_base` registra qual snapshot foi reaberto; `campos_alterados` registra objetivamente as diferenças de parâmetros e/ou parcelas.
- **Ordenação:** cálculos de processo aparecem primeiro, ordenados pelo número do processo; cálculos manuais aparecem em seguida, ordenados pelo identificador. Versões aparecem da mais recente para a mais antiga.
- **Revisão humana:** reabrir uma versão invalida a confirmação anterior. Um novo cálculo exige nova confirmação humana.
- **Retenção:** prazo de retenção, descarte e acesso aos snapshots deve ser validado por Jurídico/Compliance/DPO antes do uso institucional.

## 2026-09-24 — Histórico avançado: identidade, concorrência, versões e execuções

Responsável pela alteração: assistente de engenharia; validação operacional multiusuário pendente em ambiente corporativo.

- **Identidade processual:** o número do processo é persistido com uma chave normalizada contendo somente dígitos. Máscaras diferentes do mesmo número não criam outro cálculo. A formatação CNJ é apenas de apresentação; esta regra não valida juridicamente o dígito verificador.
- **Identidade de versão:** um `business_hash` SHA-256 é calculado somente sobre parâmetros, parcelas e `honorarios_sobre_danos_morais`. O mesmo estado funcional reutiliza a versão já cadastrada.
- **Execução técnica:** toda execução concluída recebe `execucao_id`, mesmo quando não nasce uma versão. Hashes do motor, política, índices, entrada, duração e PDFs ficam ligados à execução para não transformar variação técnica em versão funcional.
- **Concorrência:** `BEGIN IMMEDIATE` serializa a decisão de persistência no SQLite e `versao_base` implementa optimistic locking. Quando um novo estado parte de versão que deixou de ser atual, o backend retorna conflito e não cria versão parcial.
- **Histórico linear:** a interface permite edição da versão atual. Versões antigas permanecem consultáveis/comparáveis, evitando ramificações silenciosas do histórico. Uma estratégia de branching só deverá ser introduzida se houver requisito jurídico/operacional explícito.
- **Diff:** cada versão nova persiste diferenças escalares e diferenças completas das parcelas em relação à versão base. O comparador também calcula o diff diretamente entre duas versões escolhidas, sem alterar snapshots persistidos.
- **Ciclo de vida:** cálculos podem estar `ativo`, `arquivado` ou `cancelado`. Arquivamento/cancelamento não remove versões ou execuções e impede novas execuções até reativação.
- **Escalabilidade da consulta:** o histórico é paginado no backend. Versões e execuções são consultadas sob demanda, evitando transportar todo o histórico em uma única resposta.
- **Filtros:** busca por processo/identificador, origem, estado, índice, criador, intervalo de atualização e ordenação são executados no backend.
- **Migração:** bases antigas recebem colunas e tabelas novas de forma aditiva. Uma versão legada sem execução materializada recebe uma execução técnica correspondente ao snapshot histórico já existente; nenhum cálculo é reexecutado durante migração.
## 2026-09-24 — Multa comum percentual ou fixa

Responsável pela alteração: assistente de engenharia; validação jurídica do critério concreto permanece responsabilidade da revisão humana.

- **Contrato:** `multa_valor` é o campo canônico e `multa_tipo` admite `percentual` ou `fixo`. `multa_percentual` é aceito somente como alias legado de entrada.
- **Percentual:** mantém o comportamento anterior e calcula a multa sobre a base configurada pelas opções de incidência.
- **Fixo:** representa um único valor monetário para todo o cálculo. O motor não replica o valor por parcela; ele o rateia entre parcelas elegíveis apenas para manter memória, subtotal e art. 523 consistentes linha a linha.
- **Compatibilidade:** snapshots, fixtures e chamadas antigas continuam calculáveis por fallback explícito. Novas extrações e a interface usam apenas os campos canônicos.
- **Interface:** a retirada de `Execução em lote` e `Índices` é somente de navegação principal, sem excluir endpoints/rotas. A alteração do título `Conferência do cálculo` restringe-se à família tipográfica.


## 2026-09-24 — Refatoração estrutural da persistência e contratos

Responsável pela alteração: assistente de engenharia; aprovação institucional permanece a cargo do processo corporativo de release.

- **Repositórios por domínio:** código novo injeta repositórios especializados. `Repository` existe somente para compatibilidade e não contém SQL. Motivo: evitar que documentos, extrações, auditoria, índices e cálculos evoluam no mesmo objeto monolítico.
- **Versão × execução × artefato:** versão representa estado funcional imutável; execução representa uma materialização técnica daquele estado; artefato representa arquivo produzido por uma execução. Motivo: reexecutar o mesmo estado com outra versão de índice/motor não cria versão de negócio falsa nem duplica PDFs na tabela de versões.
- **Constraints como última barreira:** regras críticas de identidade, unicidade do hash e imutabilidade são aplicadas também pelo SQLite. Motivo: não depender exclusivamente da disciplina da camada Python.
- **API canônica:** novos clientes usam `/api/v2`; aliases `/api` e `/api/v1` são transitórios e ocultos do OpenAPI. O contrato público usa `2.0.0`; a versão da aplicação é independente (`2.1.0`).
- **Parâmetros:** a API plana permanece compatível, mas o backend converte os campos para grupos internos coesos e diferencia valor percentual de montante fixo. Motivo: reduzir estados semanticamente inválidos sem quebrar o motor estabilizado.
- **DrCalc:** scraping, parsing, workbook, ciclo de vida e orquestração ficam em módulos distintos. O arquivo antigo permanece como fachada para imports existentes.
- **Histórico Angular:** filtros, diff, comparação e execuções foram extraídos da página orquestradora. Execuções usam lazy loading e paginação independente.
- **Erros públicos:** decisões de frontend devem usar `code`, não texto. `request_id` correlaciona suporte; valores recebidos não são ecoados.

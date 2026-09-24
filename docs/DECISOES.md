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
- O fluxo de regressão cobre a mesma ordem da UI: registrar alteração manual, confirmar revisão e executar `/api/calculos` sem número de processo.

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

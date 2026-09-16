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
| Telemetria baseada no `usage` real do provedor | Tokens e cache são medidos, não estimados a partir do texto local. |
| Preços fora do código em `config/model_pricing.json` | Tarifas mudam; modelo desconhecido produz custo nulo em vez de preço inventado. |
| Conteúdo documental não entra na telemetria de custo | Mantém observabilidade sem ampliar exposição de dados do processo. |
| Seções de parâmetros usam cartões independentes e cabeçalho destacado quando abertas | Mantém o bloco ativo identificável durante a rolagem sem alterar a identidade visual da aplicação. |
| Categorias do DrCalc são descobertas pela navegação da fonte, com IDs apenas como fallback | Evita quebrar a atualização quando o site altera identificadores de categoria. |
| Séries do DrCalc são obtidas pela submissão do formulário histórico real | O valor do seletor de indexador não é tratado como URL por suposição; período, categoria, defaults e método GET/POST são reproduzidos conforme a página publicada. |
| Variação percentual e número-índice são tratados como métricas distintas | Evita gravar um percentual mensal em coluna acumulada ou um número-índice como taxa decimal. Quando a unidade não pode ser inferida com segurança, a coluna acumulada é preservada. |
| Parser histórico aceita formatos longos e matrizes por ano/mês | Aumenta a resiliência a tabelas ASP antigas sem depender de um único layout HTML. |
| Estado da atualização usa `DrCalcUpdateResult.success` como fonte de verdade | Evita falso negativo causado por inferência baseada em texto de mensagem ou no campo `executed`. |

Regras que expressem interpretação jurídica, sucessão de decisões, política de encargos ou retenção de dados devem ser validadas pelas áreas responsáveis antes de uso institucional.


## Dependências npm — 16/09/2026

- **Decisão:** utilizar exclusivamente pacotes oficiais publicados no npm, sem fork local, tarball de biblioteca ou substituto fictício.
- **Browserslist:** restaurado para a distribuição oficial `4.28.9`. Como a distribuição oficial depende de `update-browserslist-db`, foi fixada a versão oficial `1.3.3` para não resolver a `1.3.2` que recebeu HTTP 403.
- **Content-Type:** `negotiator` foi fixado na versão oficial `1.0.0`, aceita pelos consumidores `^1.0.0` e sem dependência de `content-type`; `body-parser` e `type-is` usam `content-type@2.0.0`, dentro das respectivas faixas `^2.0.0`.
- **Motivo:** manter a árvore dentro dos contratos semânticos publicados pelos mantenedores e reduzir o risco de manutenção/homologação de forks.
- **Trade-off:** `update-browserslist-db` volta a existir porque faz parte da distribuição oficial do Browserslist compatível com a linha usada pelo Angular. Se a versão `1.3.3` também for recusada pelo Nexus, a resolução deve ser feita com a governança corporativa, não por modificação local da biblioteca.
- **Validação:** `npm run verify:lock`, testes de regressão e validação arquitetural passaram. A instalação offline completa não pôde ser executada porque o cache da sessão não possui todos os tarballs; o download real e o build dependem das permissões do Nexus.
- **Responsável pela aprovação de dependências:** equipe proprietária do Nexus/segurança corporativa (a confirmar).

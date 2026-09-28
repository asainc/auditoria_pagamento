# Telemetria, FinOps e otimização da IA corporativa

## Objetivo

Reduzir chamadas e contexto sem sacrificar auditabilidade. A aplicação diferencia três categorias: métricas fornecidas pelo gateway, estimativas locais para planejamento e custo estimado usando tarifas corporativas configuradas explicitamente.

Nenhuma tarifa é embutida no código. Sem tarifa verificada, a aplicação mostra custo como indisponível em vez de inventar um valor.

## Telemetria registrada

Por chamada são registrados apenas metadados operacionais:

- etapa e modelo;
- hash SHA-256 da requisição;
- job de extração;
- sucesso/falha;
- uso de cache;
- caracteres de entrada/saída;
- tokens reais quando o gateway os expõe;
- estimativa local de tokens quando necessário;
- custo estimado somente quando as tarifas verificadas foram configuradas;
- duração;
- quantidade de páginas de contexto;
- indicação de correção estrutural.

Não são registrados prompt integral, PDF integral, credenciais ou token de autenticação na tabela FinOps.

## Tokens reais versus estimativa

Quando a resposta corporativa expõe `usage`, a integração captura contadores de entrada, cache e saída. Quando não expõe, o sistema usa uma aproximação local baseada em caracteres (`ceil(caracteres/4)`) exclusivamente para capacidade/FinOps. Essa aproximação não deve ser tratada como faturamento.

O resumo só exibe um total de `tokens_reais` quando todas as chamadas do recorte possuem telemetria real. Em cenários mistos, a origem é marcada como `mista` e o total real agregado não é apresentado como se estivesse completo.

## Custo

Configure apenas tarifas oficiais da API corporativa:

- `AI_FINOPS_INPUT_USD_PER_MILLION_TOKENS`;
- `AI_FINOPS_OUTPUT_USD_PER_MILLION_TOKENS`;
- `AI_FINOPS_CACHED_INPUT_USD_PER_MILLION_TOKENS`.

O custo apresentado é uma estimativa técnica a partir da tarifa configurada, não uma fatura. Se alguma chamada do período não puder ser precificada, o total é mantido como indisponível para evitar subestimar custo.

## Controles para reduzir consumo

### 1. Roteamento de páginas antes da IA

`PromptPageRouter` escolhe somente páginas candidatas por tarefa e usa fallback limitado. O PDF inteiro não é enviado automaticamente a cada prompt.

Configurações:

- `EXTRACTION_MAX_PAGES_PER_TASK`;
- `EXTRACTION_FALLBACK_PAGES_PER_DOCUMENT`;
- `BRADESCO_PROMPT_MAX_CHARS`.

### 2. Cache exato

A resposta estruturada normalizada é reutilizada quando modelo, temperatura, limite de saída e requisição completa são exatamente iguais. O cache é local, baseado em SHA-256 e não faz similaridade aproximada.

- `AI_FINOPS_CACHE_ENABLED=true|false`;
- `AI_FINOPS_CACHE_TTL_DAYS=30`.

A expiração limita retenção. Desabilite o cache se a política de dados do ambiente exigir. Essa decisão precisa ser validada com Segurança/Compliance/DPO conforme a classificação dos dados processados.

### 3. Correção estrutural local primeiro

Aliases, wrappers e defaults conservadores são normalizados localmente. Uma segunda chamada é feita somente se o contrato continuar inválido.

### 4. Few-shot curado e limitado

Somente exemplos aprovados são usados. O retrieval é local, não consome uma chamada adicional, e o bloco é limitado por:

- `LEARNING_MAX_EXAMPLES_PER_TASK`;
- `LEARNING_MAX_CHARS_PER_TASK`.

### 5. Limites rígidos por job

Antes de cada chamada real:

- `AI_FINOPS_MAX_CALLS_PER_JOB` limita quantidade de chamadas;
- `AI_FINOPS_MAX_INPUT_CHARS_PER_JOB` limita volume total de contexto enviado.

Cache hit não consome cota de chamadas de API.

### 6. Orçamento mensal opcional

- `AI_FINOPS_MONTHLY_BUDGET_USD` define orçamento;
- `AI_FINOPS_BUDGET_WARNING_RATIO` define a faixa de alerta;
- `AI_FINOPS_ENFORCE_MONTHLY_BUDGET=true` bloqueia novas chamadas quando o orçamento calculável foi atingido.

O bloqueio deve ser habilitado somente depois de confirmar tarifas e cobertura da telemetria. Se custo não puder ser calculado com integridade, o sistema não presume consumo zero nem bloqueia por um número incompleto.

## Painel FinOps

A tela `Qualidade IA` apresenta:

- chamadas reais à API;
- falhas de API;
- cache hits e taxa de cache;
- caracteres enviados;
- tokens reais quando completos;
- tokens estimados;
- custo estimado quando completo;
- orçamento mensal e status, quando configurado;
- detalhamento por etapa/prompt.

Use o detalhamento por etapa para localizar prompts com maior contexto, baixa taxa de cache ou muitas falhas/reparos.

## Guardrails de operação

Uma política FinOps robusta deve combinar:

1. orçamento e alertas por ambiente;
2. limite por job;
3. dashboards por etapa;
4. revisão periódica de prompts e páginas roteadas;
5. benchmark de qualidade antes de qualquer redução agressiva de contexto;
6. rastreabilidade de modelo/prompt/pipeline;
7. validação financeira das tarifas configuradas;
8. não usar redução de custo para justificar perda não mensurada de qualidade.

# Telemetria e otimização da IA corporativa

## Métricas disponíveis

O contrato utilizado por `text_generator` devolve o texto final, mas não fornece no retorno consumido pela calculadora contadores de tokens ou cobrança. Portanto a aplicação registra apenas:

- etapa;
- modelo/serviço;
- quantidade de chamadas;
- duração de cada chamada;
- duração acumulada.

Tokens e custo permanecem nulos. Não há estimativa por caracteres, tokenizer aproximado ou tabela de preços presumida.

## Otimização de payload

O projeto reduz redundância em três pontos:

1. prompts especializados recebem somente os campos do seu domínio;
2. OCR é executado uma vez por PDF a cada job de extração;
3. textos extensos são divididos por documento/página, sem truncamento silencioso.

`config/extraction_tasks.json` controla somente o limite máximo de saída de cada tarefa. `BRADESCO_TEXT_MAX_TOKENS` funciona como teto global.

## Trade-off

A aplicação prioriza cobertura documental e rastreabilidade. Não seleciona automaticamente apenas alguns PDFs para economizar chamadas, porque parâmetros podem estar distribuídos entre petições, sentenças, acórdãos, extratos e anexos.

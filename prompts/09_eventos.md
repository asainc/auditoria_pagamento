# Extraindo eventos financeiros

## Objetivo
Extraia somente eventos efetivamente ocorridos e comprovados no caso: `deposito_judicial`, `pagamento_parcial`, `compensacao` ou `levantamento`.

## Fontes
Priorize comprovantes, guias, extratos, decisões de levantamento e planilhas de cumprimento com data e valor verificáveis. Use `natureza=evento_comprovado` para o fato do evento; eventual comando judicial sobre seu efeito pode usar `comando_decisorio`.

## Campos
Para cada evento:
- `tipo`;
- `data` em `AAAA-MM-DD` quando calculável;
- `valor` decimal textual;
- `criterio`: `abater_na_data_do_pagamento`, `descontar_no_final` ou `informativo`;
- `indice_atualizacao` somente se houver índice específico expresso;
- `aplicar_juros_apos_evento` somente com comando inequívoco.

## Critério
Não presuma que todo depósito reduz a dívida na data do depósito. Se o documento apenas prova a ocorrência, use `informativo` e gere alerta para revisão. Critérios de abatimento exigem suporte no caso/política expressa.

## Deduplicação
Não duplique evento porque foi citado novamente em peça posterior. Um levantamento pode se referir a depósito anterior sem criar novo abatimento. Evite representar a mesma quantia simultaneamente como evento e compensação parametrizada.

## Saída
Use índices consistentes: `eventos_financeiros.<índice>.tipo`, `.data`, `.valor`, `.criterio` e campos opcionais. Retorne `parcelas=[]` e não crie parâmetros fora deste assunto.

## Cobertura adicional
Procure depósito judicial, guia, pagamento, transferência, quitação parcial, levantamento, alvará, estorno, compensação efetivada e crédito em conta. Em extratos, diferencie data de lançamento, data de processamento e data de valor; use apenas a data cuja natureza estiver clara. Não deduza o efeito econômico do evento quando o documento apenas comprovar sua ocorrência.

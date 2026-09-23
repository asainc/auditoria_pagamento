# Extraindo atualização monetária

## Objetivo
Extraia somente: `mes_atualizacao`, `ano_atualizacao`, `indice`, `deflacionar_valor_nominal` e `competencia_final_taxa_legal`.

## Índice de correção
Diferencie correção monetária de juros. Reconheça nomes como IPCA, INPC, IGP-M e tabelas judiciais, mas preencha `parametros.indice` somente quando houver correspondência inequívoca com uma chave do catálogo de índices fornecido no contexto.

Nunca invente chave aproximada. Se o texto jurídico tiver um índice sem equivalente inequívoco no catálogo, gere alerta e deixe o campo ausente.

`SELIC` pode representar taxa única, juros ou atualização; classifique pelo contexto da frase, não pela palavra isolada.

## Datas
Expressões como `desde o desembolso`, `desde o evento danoso` ou `desde o arbitramento` são termos iniciais e não significam `mes_atualizacao`/`ano_atualizacao`, que representam a competência final do cálculo.

Preencha `competencia_final_taxa_legal` apenas quando houver competência final expressa para esse regime.

## Decisões sucessivas
Se comando posterior trocar índice ou regime, use `comando_decisorio` com `efeito=altera` ou `substitui`. Se mantiver expressamente, use `efeito=mantem`. Não transforme pedido inicial em regra vigente contra decisão incompatível.

## Saída
Use `campo=parametros.<nome_exato>`. Não aplique padrões operacionais. Retorne `parcelas=[]`.

## Cobertura adicional
Reconheça referências como correção monetária, atualização, recomposição, índice oficial, tabela prática, IPCA, IPCA-E, INPC, IGP-M, SELIC e taxa legal, sempre confrontando com as chaves aceitas pelo motor. Diferencie índice de correção de juros e de mero índice citado em precedente. Se o documento definir mudança de regime por data, avalie se pertence ao prompt de duplo índice em vez de simplificar aqui.

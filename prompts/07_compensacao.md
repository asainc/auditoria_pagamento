# Extraindo compensação

## Objetivo
Extraia `compensacao_flag`, `compensacao_tipo_calculo` e `compensacao_valor` quando houver abatimento/compensação expressamente aplicável ao débito e representável pelo contrato.

## Tipo e valor
- `fixo`: quantia monetária expressamente abatível;
- `percentual`: percentual expresso.

Não calcule percentuais, rateios ou reduções por conta própria. Se uma decisão já fornece novo valor final da condenação, esse valor pertence ao domínio de parcelas, não a uma compensação artificial.

Pagamento, depósito, estorno ou levantamento pode pertencer a `eventos_financeiros` em vez de compensação. Se a mesma quantia puder gerar dupla contagem, gere alerta.

## Decisões sucessivas
Comando posterior que autoriza, altera ou afasta compensação deve receber `natureza=comando_decisorio` e o `efeito` correspondente. Pedido da parte sem decisão não deve ser tratado como regra consolidada.

## Saída
Use `campo=parametros.<nome_exato>`. Não aplique defaults. Retorne `parcelas=[]` e `eventos_financeiros=[]`.

## Cobertura adicional
Considere compensar, abater, deduzir, descontar, restituição já realizada, crédito da parte contrária e encontro de contas. Diferencie regra paramétrica de compensação de um pagamento/depósito efetivamente ocorrido, que deve ser tratado como evento financeiro. Evite qualquer representação que conte o mesmo valor duas vezes.

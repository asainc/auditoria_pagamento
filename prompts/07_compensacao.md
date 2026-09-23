# Extraindo compensação

## Objetivo
Extraia `compensacao_flag`, `compensacao_tipo_calculo` e `compensacao_valor` quando houver abatimento/compensação expressamente aplicável ao débito e representável pelo contrato.

## Tipo e valor
- `fixo`: quantia monetária expressamente abatível;
- `percentual`: percentual expresso.

Não calcule percentuais, rateios ou reduções por conta própria. Se uma decisão já fornece novo valor final da condenação, esse valor pertence ao domínio de parcelas, não a uma compensação artificial.

Pagamento, depósito, estorno ou levantamento não deve ser transformado automaticamente em compensação. Se houver risco de dupla contagem, gere alerta.

## Decisões sucessivas
Comando posterior que autoriza, altera ou afasta compensação deve receber `natureza=comando_decisorio` e o `efeito` correspondente. Pedido da parte sem decisão não deve ser tratado como regra consolidada.

## Saída
Use `campo=parametros.<nome_exato>`. Não aplique defaults. Retorne `parcelas=[]`.

## Cobertura adicional
Considere compensar, abater, deduzir, descontar, restituição já realizada, crédito da parte contrária e encontro de contas. Diferencie regra paramétrica de compensação de simples menção a pagamento/depósito. Evite qualquer representação que conte o mesmo valor duas vezes.
